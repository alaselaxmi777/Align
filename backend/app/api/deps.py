from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.core.security import ALGORITHM

JWT_ERRORS = (jwt.PyJWTError, ValueError)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False
)

def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            return None
        user_id = int(subject)
    except JWT_ERRORS:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user

def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    user = get_current_user_optional(token, db)
    if not user:
        raise unauthorized
    return user

def get_current_admin(
    user: User = Depends(get_current_user)
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    return user

def require_role(*allowed_roles: str):
    """
    Enforces Role-Based Access Control (RBAC).
    Allowed roles typically include: 'user', 'moderator', 'admin'.
    Admins are always authorized for moderator/user endpoints.
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {list(allowed_roles)}"
            )
        return user
    return role_checker

require_admin = get_current_admin

