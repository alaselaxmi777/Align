import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings

ALGORITHM = "HS256"
_ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hashes password using Argon2id (OWASP recommended standard)."""
    return _ph.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies password against Argon2 or legacy bcrypt hash."""
    if not hashed_password or not password:
        return False
    if hashed_password.startswith("$argon2"):
        try:
            return _ph.verify(hashed_password, password)
        except VerifyMismatchError:
            return False
    elif hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False
    return False

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "type": "access", "exp": expires, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)

def hash_token(token_str: str) -> str:
    """Returns SHA-256 hash of a token string for safe storage and indexing."""
    return hashlib.sha256(token_str.encode("utf-8")).hexdigest()

def create_tracked_refresh_token(
    subject: str,
    family_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, str, datetime]:
    """
    Creates an authenticated refresh token with a unique JTI and family ID for rotation tracking.
    Returns: (token_jwt, token_hash, family_id, expires_at)
    """
    jti = str(uuid.uuid4())
    fam = family_id or str(uuid.uuid4())
    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + timedelta(days=7)

    payload = {
        "sub": str(subject),
        "type": "refresh",
        "jti": jti,
        "fam": fam,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    return token, hash_token(token), fam, expires

def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    token, _, _, _ = create_tracked_refresh_token(subject, expires_delta=expires_delta)
    return token

def decode_token(token_str: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token_str, settings.jwt_secret_key, algorithms=[ALGORITHM])
        # If token was generated before type claim was added, treat it as access
        token_type = payload.get("type", "access")
        if token_type != expected_type:
            raise ValueError(f"Invalid token type: expected {expected_type}, got {token_type}")
        return payload
    except Exception as exc:
        raise ValueError(f"Token decoding failed: {exc}") from exc

def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)

def verify_google_id_token(token_str: str) -> dict:
    """
    Validates a Google ID Token using the official google-auth library.
    Checks signature, expiration, issuer, and client ID audience.
    """
    if not settings.google_client_id:
        raise ValueError("Google OAuth is not configured on this server (GOOGLE_CLIENT_ID missing in .env).")
    try:
        request = google_requests.Request()
        id_info = id_token.verify_oauth2_token(
            token_str,
            request,
            audience=settings.google_client_id,
            clock_skew_in_seconds=10
        )
        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid Google token issuer")
        return id_info
    except Exception as e:
        raise ValueError(f"Google token verification failed: {str(e)}")
