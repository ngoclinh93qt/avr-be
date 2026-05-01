"""API dependencies for dependency injection."""

from typing import Optional
from fastapi import HTTPException, Header, Depends

from app.core.supabase_client import supabase_service

# Dev mode bypass - set to False in production
DEV_MODE = False
DEFAULT_USER_ID = "53262502-c85d-436f-98eb-66f518383813"  # admin@avr.com


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Extract and validate user ID from authorization header.

    Expects: Authorization: Bearer <token>
    """
    # Dev mode bypass
    if DEV_MODE:
        return DEFAULT_USER_ID

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )

    token = parts[1]

    # Validate token with Supabase
    user = await supabase_service.get_user(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    # Get user ID
    if hasattr(user, 'id'):
        return user.id
    elif isinstance(user, dict):
        return user.get('id')
    else:
        raise HTTPException(
            status_code=401,
            detail="Could not extract user ID"
        )


async def get_optional_user_id(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Extract user ID if authorization is provided, otherwise return None.
    Useful for endpoints that have different behavior for authenticated users.
    """
    if not authorization:
        return None

    try:
        return await get_current_user_id(authorization)
    except HTTPException:
        return None


async def require_paid_user(
    user_id: str = Depends(get_current_user_id),
) -> str:
    """
    Require that the user has a paid subscription.
    """
    tier, can_access = await supabase_service.check_user_tier(user_id)
    if not can_access:
        raise HTTPException(
            status_code=402,
            detail="This feature requires a paid subscription"
        )
    return user_id


async def check_token_quota(
    user_id: str = Depends(get_current_user_id),
) -> str:
    """Raise 429 if user has exceeded monthly token quota."""
    await supabase_service.check_token_quota(user_id)
    return user_id
