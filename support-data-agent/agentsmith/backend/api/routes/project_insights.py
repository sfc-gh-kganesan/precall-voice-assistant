"""API routes for on-demand insights generation."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.models import Project
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter()


class InsightRequest(BaseModel):
    """Request to generate insights."""

    date_from: str = None
    date_to: str = None


class Insight(BaseModel):
    """Generated insight."""

    title: str
    description: str
    priority: str  # high, medium, low
    category: str


class InsightsResponse(BaseModel):
    """Response with generated insights."""

    insights: List[Insight]
    total: int


@router.post("/{project_id}/insights", response_model=InsightsResponse)
async def generate_project_insights(
    project_id: int, request: InsightRequest, db: Session = Depends(get_db)
):
    """Generate insights from live Snowflake data (placeholder - to be implemented with AI)."""

    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"Generating insights for project {project_id}")

    # TODO: Implement actual insights generation using:
    # 1. Query Snowflake for conversations
    # 2. Analyze patterns, errors, trends
    # 3. Use LLM to generate actionable insights

    # For now, return placeholder
    return InsightsResponse(
        insights=[
            Insight(
                title="Insights generation coming soon",
                description="On-demand insights generation will analyze live conversations and provide recommendations",
                priority="medium",
                category="feature",
            )
        ],
        total=1,
    )
