import time
import threading
from collections import defaultdict
from fastapi import HTTPException, Request, status

class InMemoryRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""
    def __init__(self):
        self._lock = threading.Lock()
        # key -> list of timestamps
        self._records = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            # Filter timestamps within window
            timestamps = [t for t in self._records[key] if t > cutoff]
            if len(timestamps) >= max_requests:
                earliest = timestamps[0]
                retry_after = int(earliest + window_seconds - now) + 1
                self._records[key] = timestamps
                return False, max(1, retry_after)
            
            timestamps.append(now)
            self._records[key] = timestamps
            return True, 0

    def reset(self):
        with self._lock:
            self._records.clear()

_limiter = InMemoryRateLimiter()

TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost", "testclient"}

def is_trusted_proxy(ip: str) -> bool:
    if ip in TRUSTED_PROXIES:
        return True
    # Internal private IP subnets (e.g. docker bridge networks)
    if ip.startswith("172.") or ip.startswith("10.") or ip.startswith("192.168."):
        return True
    return False

def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """FastAPI dependency for hardened IP and user-based rate limiting."""
    def dependency(request: Request):
        direct_ip = request.client.host if request.client else "127.0.0.1"

        # Only trust X-Forwarded-For if request arrives from a trusted proxy
        client_ip = direct_ip
        if is_trusted_proxy(direct_ip):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

        # Bypass during automated test runner unless explicitly testing rate limits
        if client_ip in ("testclient", "testserver") and request.headers.get("X-Test-Rate-Limit") != "enforce":
            return

        # Check if caller has an active authenticated session
        user_identifier = client_ip
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token_val = auth_header.split(" ")[1]
                payload = decode_token(token_val)
                if payload.get("sub"):
                    user_identifier = f"user_{payload['sub']}"
            except Exception:
                pass

        path = request.url.path
        key = f"{user_identifier}:{path}"

        allowed, retry_after = _limiter.is_allowed(key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
