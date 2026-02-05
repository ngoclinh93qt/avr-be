"""
Authentication middleware and dependencies for FastAPI.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase_client import supabase_service

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user model."""

    def __init__(self, user_data: dict):
        self.id: str = user_data.get("id", "")
        self.email: str = user_data.get("email", "")
        self.role: str = user_data.get("role", "authenticated")
        self.raw: dict = user_data


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthUser:
    """
    Dependency to get current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        user = await supabase_service.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AuthUser(user.__dict__ if hasattr(user, "__dict__") else dict(user))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthUser]:
    """
    Dependency for optional authentication.
    Returns None if no token provided, user if valid.

    Usage:
        @app.get("/public-or-private")
        async def route(user: Optional[AuthUser] = Depends(get_optional_user)):
            if user:
                return {"authenticated": True, "user_id": user.id}
            return {"authenticated": False}
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_auth(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Alias for get_current_user for clearer intent."""
    return user
