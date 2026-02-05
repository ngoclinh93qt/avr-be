from fastapi import APIRouter, HTTPException

from app.models.schemas import JournalMatchRequest, JournalMatchResponse
from app.services.journal_matcher import JournalMatcherService

router = APIRouter()
service = JournalMatcherService()


@router.post("/match", response_model=JournalMatchResponse)
async def match_journals(request: JournalMatchRequest):
    """Find suitable journals for the research abstract"""
    try:
        result = await service.match(
            abstract=request.abstract,
            max_apc=request.max_apc,
            min_if=request.min_if,
            max_if=request.max_if,
            open_access_only=request.open_access_only,
            specialty=request.specialty,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
