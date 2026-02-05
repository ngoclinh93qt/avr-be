"""
Research history API endpoints.
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.core.auth import AuthUser, get_current_user
from app.core.supabase_client import supabase_service

router = APIRouter(prefix="/history", tags=["Research History"])


# ════════════════════════════════════════════════════════════════════════════
# Response Models
# ════════════════════════════════════════════════════════════════════════════


class ResearchPaperResponse(BaseModel):
    id: str
    pmid: Optional[str]
    title: str
    authors: list[str]
    abstract: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    similarity: float
    source: str


class ResearchSessionSummary(BaseModel):
    id: str
    abstract: str
    status: str
    total_papers_found: int
    total_papers_ranked: int
    avg_similarity: float
    created_at: str


class ResearchSessionDetail(BaseModel):
    id: str
    abstract: str
    language: str
    status: str
    keywords: Optional[list[str]]
    assessment: Optional[dict]
    analysis_result: Optional[dict]
    total_papers_found: int
    total_papers_ranked: int
    avg_similarity: float
    processing_time_seconds: float
    created_at: str
    updated_at: str
    papers: list[ResearchPaperResponse]


class SessionListResponse(BaseModel):
    sessions: list[ResearchSessionSummary]
    total: int
    limit: int
    offset: int


# ════════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════════


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
):
    """
    Get user's research session history.
    """
    try:
        sessions = await supabase_service.get_user_sessions(
            user_id=user.id,
            limit=limit,
            offset=offset,
        )

        return SessionListResponse(
            sessions=[
                ResearchSessionSummary(
                    id=s["id"],
                    abstract=s["abstract"][:200] + "..."
                    if len(s.get("abstract", "")) > 200
                    else s.get("abstract", ""),
                    status=s.get("status", "unknown"),
                    total_papers_found=s.get("total_papers_found", 0),
                    total_papers_ranked=s.get("total_papers_ranked", 0),
                    avg_similarity=s.get("avg_similarity", 0.0),
                    created_at=s.get("created_at", ""),
                )
                for s in sessions
            ],
            total=len(sessions),  # TODO: Get actual count
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=ResearchSessionDetail)
async def get_session(
    session_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Get a specific research session with all papers.
    """
    try:
        session = await supabase_service.get_research_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Check ownership
        if session.get("user_id") != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get papers
        papers = await supabase_service.get_session_papers(session_id)

        return ResearchSessionDetail(
            id=session["id"],
            abstract=session.get("abstract", ""),
            language=session.get("language", "auto"),
            status=session.get("status", "unknown"),
            keywords=session.get("keywords"),
            assessment=session.get("assessment"),
            analysis_result=session.get("analysis_result"),
            total_papers_found=session.get("total_papers_found", 0),
            total_papers_ranked=session.get("total_papers_ranked", 0),
            avg_similarity=session.get("avg_similarity", 0.0),
            processing_time_seconds=session.get("processing_time_seconds", 0.0),
            created_at=session.get("created_at", ""),
            updated_at=session.get("updated_at", ""),
            papers=[
                ResearchPaperResponse(
                    id=p["id"],
                    pmid=p.get("pmid"),
                    title=p.get("title", ""),
                    authors=p.get("authors", []),
                    abstract=p.get("abstract"),
                    year=p.get("year"),
                    journal=p.get("journal"),
                    doi=p.get("doi"),
                    similarity=p.get("similarity", 0.0),
                    source=p.get("source", "pubmed"),
                )
                for p in papers
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch session: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Delete a research session and its papers.
    """
    try:
        session = await supabase_service.get_research_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Check ownership
        if session.get("user_id") != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Delete (cascade will delete papers)
        supabase_service.admin.table("research_sessions").delete().eq(
            "id", session_id
        ).execute()

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
