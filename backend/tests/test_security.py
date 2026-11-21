from app.core.security import hash_password, verify_password, create_access_token, generate_secure_token
import jwt
from app.core.config import settings

def test_argon2_password_hashing():
    pw = "SuperSecurePassword123!"
    h = hash_password(pw)
    assert h.startswith("$argon2")
    assert verify_password(pw, h) is True
    assert verify_password("WrongPassword!", h) is False

def test_jwt_access_token_creation_and_payload():
    token = create_access_token("42")
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    assert payload["sub"] == "42"
    assert "exp" in payload
    assert "iat" in payload

def test_secure_token_randomness():
    t1 = generate_secure_token()
    t2 = generate_secure_token()
    assert len(t1) >= 32
    assert t1 != t2
