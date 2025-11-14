"""API routes for AI-generated insights."""

import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.api.schemas import ImprovementSuggestionResponse
from backend.models.models import Simulation, SimulationStatus, ImprovementSuggestion
from backend.core.insights_judge import InsightsJudge
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{simulation_id}/ai-insights", response_model=List[ImprovementSuggestionResponse])
async def get_ai_insights(simulation_id: int, db: Session = Depends(get_db)):
    """Get AI-generated insights for a simulation.

    If insights haven't been generated yet, they will be generated on-demand.
    """
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=400, detail="Simulation must be completed before generating insights"
        )

    # Check if insights already exist
    existing_insights = (
        db.query(ImprovementSuggestion)
        .filter(ImprovementSuggestion.simulation_id == simulation_id)
        .all()
    )

    if existing_insights and simulation.llm_insights_generated:
        logger.info(f"Returning {len(existing_insights)} cached AI insights for simulation {simulation_id}")
        return existing_insights

    # Generate insights if they don't exist
    logger.info(f"Generating AI insights for simulation {simulation_id}")

    # Get Snowflake Cortex configuration from environment
    api_key = os.getenv("SNOWFLAKE_CORTEX_API_KEY")
    base_url = os.getenv("SNOWFLAKE_CORTEX_BASE_URL")
    model = os.getenv("SNOWFLAKE_CORTEX_MODEL", "snowflake-arctic")

    if not api_key or not base_url:
        raise HTTPException(
            status_code=500,
            detail="Snowflake Cortex configuration missing. Set SNOWFLAKE_CORTEX_API_KEY and SNOWFLAKE_CORTEX_BASE_URL environment variables.",
        )

    try:
        judge = InsightsJudge(api_key=api_key, base_url=base_url, model=model)
        insights = await judge.generate_insights(simulation_id, db)

        # Mark insights as generated
        simulation.llm_insights_generated = True
        simulation.llm_insights_generated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Successfully generated {len(insights)} AI insights for simulation {simulation_id}")
        return insights

    except Exception as e:
        logger.error(f"Failed to generate AI insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate AI insights: {str(e)}"
        )


@router.post("/{simulation_id}/ai-insights/regenerate", response_model=List[ImprovementSuggestionResponse])
async def regenerate_ai_insights(simulation_id: int, db: Session = Depends(get_db)):
    """Regenerate AI insights for a simulation (delete existing and create new ones)."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=400, detail="Simulation must be completed before generating insights"
        )

    logger.info(f"Regenerating AI insights for simulation {simulation_id}")

    # Delete existing insights
    db.query(ImprovementSuggestion).filter(
        ImprovementSuggestion.simulation_id == simulation_id
    ).delete()
    db.commit()

    # Get Snowflake Cortex configuration
    api_key = os.getenv("SNOWFLAKE_CORTEX_API_KEY")
    base_url = os.getenv("SNOWFLAKE_CORTEX_BASE_URL")
    model = os.getenv("SNOWFLAKE_CORTEX_MODEL", "snowflake-arctic")

    if not api_key or not base_url:
        raise HTTPException(
            status_code=500,
            detail="Snowflake Cortex configuration missing",
        )

    try:
        judge = InsightsJudge(api_key=api_key, base_url=base_url, model=model)
        insights = await judge.generate_insights(simulation_id, db)

        # Mark insights as generated
        simulation.llm_insights_generated = True
        simulation.llm_insights_generated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Successfully regenerated {len(insights)} AI insights for simulation {simulation_id}")
        return insights

    except Exception as e:
        logger.error(f"Failed to regenerate AI insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to regenerate AI insights: {str(e)}"
        )
