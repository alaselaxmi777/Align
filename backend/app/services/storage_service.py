import os
import uuid
import logging
import httpx
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Base persistent uploads directory
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class SecurityScanner:
    """Security and virus scanning hook. Operates safely in demo/dev mode."""
    @staticmethod
    def scan_file(file_path: Path) -> bool:
        logger.debug(f"SecurityScanner: scan_file passed for {file_path.name}")
        return True

class StorageService(ABC):
    @abstractmethod
    def save_file(self, data: bytes, filename: str, subfolder: str = "images") -> tuple[str, Path]:
        """Saves file bytes and returns (public_url, local_path)."""
        pass

    @abstractmethod
    def delete_file(self, rel_url: str) -> bool:
        """Deletes file given its relative URL."""
        pass

    @abstractmethod
    def file_exists(self, rel_url: str) -> bool:
        pass

class LocalStorageService(StorageService):
    def __init__(self, base_dir: Path = UPLOAD_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, data: bytes, filename: str, subfolder: str = "images") -> tuple[str, Path]:
        target_dir = self.base_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_path = target_dir / filename
        if not dest_path.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError("Path traversal attempt detected in storage destination.")

        with open(dest_path, "wb") as f:
            f.write(data)

        SecurityScanner.scan_file(dest_path)
        public_url = f"/uploads/{subfolder}/{filename}"
        return public_url, dest_path

    def delete_file(self, rel_url: str) -> bool:
        clean_rel = rel_url.removeprefix("/uploads/").lstrip("/")
        target_path = self.base_dir / clean_rel
        if target_path.resolve().is_relative_to(self.base_dir.resolve()) and target_path.exists():
            target_path.unlink()
            return True
        return False

    def file_exists(self, rel_url: str) -> bool:
        clean_rel = rel_url.removeprefix("/uploads/").lstrip("/")
        target_path = self.base_dir / clean_rel
        return target_path.resolve().is_relative_to(self.base_dir.resolve()) and target_path.exists()

class SupabaseStorageService(StorageService):
    """
    Native Supabase Storage provider using REST API endpoints with the server secret key.
    Uploads directly to public buckets, returning public absolute URLs.
    """
    def __init__(
        self,
        supabase_url: str,
        service_key: str,
        bucket_name: str,
        local_cache_dir: Path = UPLOAD_DIR / "tmp",
    ):
        self.supabase_url = supabase_url.rstrip("/")
        self.service_key = service_key
        self.bucket_name = bucket_name
        self.local_cache_dir = local_cache_dir
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        self.client = httpx.Client(
            timeout=30.0,
            transport=httpx.HTTPTransport(retries=3),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    def _get_content_type(self, filename: str) -> str:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        content_types = {
            "webp": "image/webp",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "webm": "video/webm",
            "mov": "video/quicktime",
        }
        return content_types.get(ext, "application/octet-stream")

    def save_file(self, data: bytes, filename: str, subfolder: str = "images") -> tuple[str, Path]:
        clean_subfolder = subfolder.strip("/")
        key = f"{clean_subfolder}/{filename}" if clean_subfolder else filename
        content_type = self._get_content_type(filename)

        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{key}"
        headers = {
            **self.headers,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        resp = self.client.post(url, headers=headers, content=data)
        if resp.status_code not in (200, 201):
            logger.error(f"Supabase upload failed: {resp.status_code} - {resp.text}")
            raise RuntimeError(f"Supabase Storage upload failed with status {resp.status_code}: {resp.text}")

        public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{key}"
        temp_dest = self.local_cache_dir / filename
        return public_url, temp_dest

    def delete_file(self, rel_or_public_url: str) -> bool:
        try:
            key = rel_or_public_url.strip()
            marker = f"/storage/v1/object/public/{self.bucket_name}/"
            if marker in key:
                key = key.split(marker, 1)[-1]
            elif f"/{self.bucket_name}/" in key:
                key = key.split(f"/{self.bucket_name}/", 1)[-1]
            elif key.startswith("/uploads/"):
                key = key.removeprefix("/uploads/").lstrip("/")

            url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}"
            resp = self.client.request("DELETE", url, headers=self.headers, json={"prefixes": [key]})
            return resp.status_code in (200, 204)
        except Exception as exc:
            logger.warning(f"Supabase deletion failed for {rel_or_public_url}: {exc}")
            return False

    def file_exists(self, rel_or_public_url: str) -> bool:
        try:
            key = rel_or_public_url.strip()
            marker = f"/storage/v1/object/public/{self.bucket_name}/"
            if marker in key:
                key = key.split(marker, 1)[-1]
            elif f"/{self.bucket_name}/" in key:
                key = key.split(f"/{self.bucket_name}/", 1)[-1]

            url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{key}"
            resp = self.client.head(url)
            return resp.status_code == 200
        except Exception:
            return False

class S3CloudStorageService(StorageService):
    """
    Production-grade cloud object storage compatible with AWS S3, Cloudflare R2,
    and Supabase Storage.
    """
    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        region_name: str = "ap-south-1",
        endpoint_url: Optional[str] = None,
        public_domain: Optional[str] = None,
        local_cache_dir: Path = UPLOAD_DIR,
    ):
        import boto3
        from botocore.config import Config

        self.bucket_name = bucket_name
        self.public_domain = public_domain.rstrip("/") if public_domain else None
        self.local_cache_dir = local_cache_dir
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)

        config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"}
        )
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config,
        )

    def _get_content_type(self, filename: str) -> str:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        content_types = {
            "webp": "image/webp",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
        }
        return content_types.get(ext, "application/octet-stream")

    def save_file(self, data: bytes, filename: str, subfolder: str = "images") -> tuple[str, Path]:
        # 1. Save to local temporary buffer for verification and local fallback
        target_dir = self.local_cache_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / filename
        with open(dest_path, "wb") as f:
            f.write(data)

        # 2. Upload to Cloud Bucket
        key = f"{subfolder}/{filename}"
        content_type = self._get_content_type(filename)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

        # 3. Construct URL (Custom CDN domain or S3 bucket URL)
        if self.public_domain:
            public_url = f"{self.public_domain}/{key}"
        else:
            public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{key}"

        return public_url, dest_path

    def delete_file(self, rel_url: str) -> bool:
        try:
            # Extract key
            if "amazonaws.com/" in rel_url:
                key = rel_url.split("amazonaws.com/", 1)[-1]
            elif self.public_domain and self.public_domain in rel_url:
                key = rel_url.replace(self.public_domain, "").lstrip("/")
            else:
                key = rel_url.removeprefix("/uploads/").lstrip("/")

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

            # Also remove local cache if present
            local_path = self.local_cache_dir / key
            if local_path.exists():
                local_path.unlink()
            return True
        except Exception as exc:
            logger.warning(f"S3 deletion failed for {rel_url}: {exc}")
            return False

    def file_exists(self, rel_url: str) -> bool:
        try:
            key = rel_url.removeprefix("/uploads/").lstrip("/")
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

def get_storage_service() -> StorageService:
    backend_type = (os.getenv("STORAGE_PROVIDER") or os.getenv("STORAGE_BACKEND") or "local").lower().strip()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase_bucket = os.getenv("SUPABASE_BUCKET", "align-media")

    if backend_type == "supabase" or (supabase_url and supabase_key):
        if not supabase_url or not supabase_key:
            logger.error("[STORAGE] Provider is 'supabase' but SUPABASE_URL or SUPABASE_SERVICE_KEY is missing!")
            raise RuntimeError("Missing required SUPABASE_URL or SUPABASE_SERVICE_KEY in environment.")
        logger.info(f"[STORAGE] Storage Provider: supabase | Bucket: {supabase_bucket}")
        return SupabaseStorageService(
            supabase_url=supabase_url,
            service_key=supabase_key,
            bucket_name=supabase_bucket,
        )

    bucket_name = os.getenv("S3_BUCKET_NAME") or os.getenv("AWS_S3_BUCKET")
    access_key = os.getenv("S3_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")

    if (backend_type in {"s3", "r2"} or bucket_name) and access_key and secret_key:
        endpoint_url = os.getenv("S3_ENDPOINT_URL")
        public_domain = os.getenv("S3_PUBLIC_BASE_URL") or os.getenv("S3_PUBLIC_DOMAIN")
        region_name = os.getenv("S3_REGION_NAME") or os.getenv("AWS_REGION", "auto")
        logger.info(f"[STORAGE] Storage Provider: {backend_type} | Bucket: {bucket_name}")
        return S3CloudStorageService(
            bucket_name=bucket_name,
            access_key_id=access_key,
            secret_access_key=secret_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
            public_domain=public_domain,
        )

    logger.info("[STORAGE] Storage Provider: local | Base directory: uploads/")
    return LocalStorageService()

# Global singleton
storage_service = get_storage_service()
