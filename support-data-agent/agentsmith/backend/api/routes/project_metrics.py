"""API routes for live project metrics from Snowflake."""

import logging
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.database import get_db, get_snowflake_db
from backend.models.models import Project
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ProjectMetrics(BaseModel):
    """Live metrics from Snowflake AGENT_TRACES."""

    total_conversations: int
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    avg_duration_ms: Optional[float]
    avg_turns: Optional[float]
    error_rate: Optional[float]
    voice_count: int
    text_count: int


@router.get("/{project_id}/metrics", response_model=ProjectMetrics)
async def get_project_metrics(
    project_id: int,
    sqlite_db: Session = Depends(get_db),
    snowflake_db: Session = Depends(get_snowflake_db),
):
    """Get live metrics for a project from Snowflake AGENT_TRACES table."""

    # Get project from SQLite
    project = sqlite_db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if Snowflake is configured
    if snowflake_db is None:
        logger.warning("Snowflake is not configured - returning empty metrics")
        return ProjectMetrics(
            total_conversations=0,
            date_range_start=None,
            date_range_end=None,
            avg_duration_ms=None,
            avg_turns=None,
            error_rate=None,
            voice_count=0,
            text_count=0,
        )

    # Determine table name
    if project.source_database and project.source_schema and project.source_table:
        table_name = (
            f"{project.source_database}.{project.source_schema}.{project.source_table}"
        )
    else:
        database = os.getenv("SNOWFLAKE_DATABASE", "AI_FDE")
        schema = os.getenv("SNOWFLAKE_SCHEMA", "CX360_DEMO")
        table_name = f"{database}.{schema}.AGENT_TRACES"

    logger.info(f"Querying metrics from table: {table_name}")

    try:
        # Query for metrics using Snowflake session
        query = text(f"""
            WITH conversation_stats AS (
                SELECT
                    conversation_id,
                    MIN(start_time) as conv_start,
                    MAX(end_time) as conv_end,
                    COUNT(*) as turn_count,
                    MAX(CASE WHEN status_code != '200' THEN 1 ELSE 0 END) as has_error,
                    MAX(triggered_by) as triggered_by
                FROM {table_name}
                WHERE conversation_id IS NOT NULL
                GROUP BY conversation_id
            )
            SELECT
                COUNT(*) as total_conversations,
                MIN(conv_start) as date_range_start,
                MAX(conv_end) as date_range_end,
                AVG(DATEDIFF('millisecond', conv_start, conv_end)) as avg_duration_ms,
                AVG(turn_count) as avg_turns,
                SUM(has_error)::FLOAT / COUNT(*)::FLOAT as error_rate,
                SUM(CASE WHEN triggered_by = 'voice' THEN 1 ELSE 0 END) as voice_count,
                SUM(CASE WHEN triggered_by = 'text' THEN 1 ELSE 0 END) as text_count
            FROM conversation_stats
        """)

        result = snowflake_db.execute(query).fetchone()

        if not result or result[0] == 0:
            # No conversations found
            return ProjectMetrics(
                total_conversations=0,
                date_range_start=None,
                date_range_end=None,
                avg_duration_ms=None,
                avg_turns=None,
                error_rate=None,
                voice_count=0,
                text_count=0,
            )

        return ProjectMetrics(
            total_conversations=result[0] or 0,
            date_range_start=result[1],
            date_range_end=result[2],
            avg_duration_ms=float(result[3]) if result[3] else None,
            avg_turns=float(result[4]) if result[4] else None,
            error_rate=float(result[5]) if result[5] else None,
            voice_count=result[6] or 0,
            text_count=result[7] or 0,
        )

    except Exception as e:
        logger.error(f"Failed to query metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to query metrics: {str(e)}"
        )
