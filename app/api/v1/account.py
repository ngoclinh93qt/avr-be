"""Account endpoint — token quota and profile info."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.supabase_client import supabase_service
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/account", tags=["Account"])


class TokenQuotaResponse(BaseModel):
    tokens_used_month: int
    token_limit_month: int
    token_reset_at: Optional[str]
    tier: str
    percent_used: float


@router.get("/quota", response_model=TokenQuotaResponse)
async def get_token_quota(user_id: str = Depends(get_current_user_id)):
    """Return current monthly token quota for the authenticated user."""
    quota = await supabase_service.get_token_quota(user_id)
    used = quota["tokens_used_month"]
    limit = quota["token_limit_month"]
    percent = round((used / limit) * 100, 1) if limit > 0 else 0.0
    return TokenQuotaResponse(
        tokens_used_month=used,
        token_limit_month=limit,
        token_reset_at=str(quota["token_reset_at"]) if quota.get("token_reset_at") else None,
        tier=quota["tier"],
        percent_used=percent,
    )
