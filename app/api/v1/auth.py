"""
Authentication API endpoints.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.auth import AuthUser, get_current_user
from app.core.supabase_client import supabase_service
from app.config import get_settings

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


class SignUpResponse(BaseModel):
    requires_confirmation: bool = False
    message: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional[dict] = None


class UserResponse(BaseModel):
    id: str
    email: str
    role: str


class MessageResponse(BaseModel):
    message: str


class OAuthUrlResponse(BaseModel):
    url: str


# ════════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════════


@router.post("/signup", response_model=SignUpResponse)
async def sign_up(request: SignUpRequest):
    """
    Register a new user.

    If email confirmation is required, returns requires_confirmation=True.
    Otherwise returns tokens directly.
    """
    try:
        result = await supabase_service.sign_up(request.email, request.password)

        if not result.get("session"):
            # Email confirmation required
            return SignUpResponse(
                requires_confirmation=True,
                message="Please check your email to confirm your account",
            )

        session = result["session"]
        user = result["user"]

        return SignUpResponse(
            requires_confirmation=False,
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
        import traceback
        print(f"[signup error] {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign up failed: {str(e)}",
        )


@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """
    Sign in with email and password.
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

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.post("/signout", response_model=MessageResponse)
async def sign_out(user: AuthUser = Depends(get_current_user)):
    """
    Sign out current user.
    """
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

    except Exception:
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


@router.get("/google", response_model=OAuthUrlResponse)
async def google_oauth_url():
    """
    Get Google OAuth redirect URL.
    Frontend should redirect the user to this URL.
    After auth, Supabase redirects back to <frontend_url>/auth/callback
    with tokens in the URL hash.
    """
    try:
        settings = get_settings()
        redirect_to = f"{settings.frontend_url}/auth/callback"
        client = await supabase_service.get_client()
        response = await client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_to},
        })
        return OAuthUrlResponse(url=response.url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate OAuth URL: {str(e)}",
        )
