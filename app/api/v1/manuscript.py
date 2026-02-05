from fastapi import APIRouter, HTTPException

from app.models.schemas import ManuscriptRequest, ManuscriptResponse
from app.services.manuscript_strategist import ManuscriptStrategistService

router = APIRouter()
service = ManuscriptStrategistService()


@router.post("/strategize", response_model=ManuscriptResponse)
async def strategize_manuscript(request: ManuscriptRequest):
    """Get manuscript writing strategy and Vietglish corrections"""
    try:
        result = await service.strategize(
            abstract=request.abstract,
            target_journal=request.target_journal,
            full_text=request.full_text,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
