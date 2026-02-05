"""
Authentication API endpoints.
"""

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.auth import AuthUser, get_current_user
from app.core.supabase_client import supabase_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ════════════════════════════════════════════════════════════════════════════


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    role: str


class MessageResponse(BaseModel):
    message: str


# ════════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════════


@router.post("/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """
    Register a new user.

    Returns access token and refresh token on success.
    """
    try:
        result = await supabase_service.sign_up(request.email, request.password)

        if not result.get("session"):
            # Email confirmation required
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Please check your email to confirm your account",
            )

        session = result["session"]
        user = result["user"]

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign up failed: {str(e)}",
        )


@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """
    Sign in with email and password.

    Returns access token and refresh token on success.
    """
    try:
        result = await supabase_service.sign_in(request.email, request.password)

        session = result["session"]
        user = result["user"]

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid email or password",
        )


@router.post("/signout", response_model=MessageResponse)
async def sign_out(user: AuthUser = Depends(get_current_user)):
    """
    Sign out current user.
    """
    # Note: Supabase handles token invalidation on client side
    # Server-side signout is mainly for cleanup
    return MessageResponse(message="Signed out successfully")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    """
    try:
        result = await supabase_service.refresh_session(request.refresh_token)

        session = result["session"]
        user = result["user"]

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(user: AuthUser = Depends(get_current_user)):
    """
    Get current user info.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
    )
