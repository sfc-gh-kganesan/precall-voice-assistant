"""API routes for browsing conversations from Snowflake."""

import logging
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.database import get_db, get_snowflake_db
from backend.models.models import Project
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ConversationSummary(BaseModel):
    """Summary of a conversation from Snowflake."""

    conversation_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    turn_count: int
    triggered_by: Optional[str]
    has_error: bool
    status_code: Optional[str]


class ConversationsResponse(BaseModel):
    """Paginated conversations response."""

    conversations: List[ConversationSummary]
    total: int
    limit: int
    offset: int


class ConversationMessage(BaseModel):
    """A single message in a conversation."""

    role: str
    content: str
    timestamp: Optional[datetime]


class ConversationDetails(BaseModel):
    """Full conversation details with messages."""

    conversation_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    turn_count: int
    triggered_by: Optional[str]
    has_error: bool
    messages: List[ConversationMessage]


@router.get("/{project_id}/conversations", response_model=ConversationsResponse)
async def get_project_conversations(
    project_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    triggered_by: Optional[str] = Query(None),
    errors_only: bool = Query(False),
    sqlite_db: Session = Depends(get_db),
    snowflake_db: Session = Depends(get_snowflake_db),
):
    """Browse conversations from Snowflake AGENT_TRACES table."""

    # Get project from SQLite
    project = sqlite_db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if Snowflake is configured
    if snowflake_db is None:
        logger.warning("Snowflake is not configured - returning empty conversations")
        return ConversationsResponse(
            conversations=[], total=0, limit=limit, offset=offset
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

    logger.info(f"Querying conversations from table: {table_name}")

    try:
        # Build WHERE clause
        where_clauses = ["conversation_id IS NOT NULL"]
        if triggered_by:
            where_clauses.append(f"triggered_by = '{triggered_by}'")
        if errors_only:
            where_clauses.append("status_code != '200'")

        where_clause = " AND ".join(where_clauses)

        # Query for conversation summaries using Snowflake session
        query = text(f"""
            WITH conversation_stats AS (
                SELECT
                    conversation_id,
                    MIN(start_time) as start_time,
                    MAX(end_time) as end_time,
                    DATEDIFF('millisecond', MIN(start_time), MAX(end_time)) as duration_ms,
                    COUNT(*) as turn_count,
                    MAX(triggered_by) as triggered_by,
                    MAX(CASE WHEN status_code != '200' THEN 1 ELSE 0 END) as has_error,
                    MAX(status_code) as status_code
                FROM {table_name}
                WHERE {where_clause}
                GROUP BY conversation_id
            )
            SELECT
                conversation_id,
                start_time,
                end_time,
                duration_ms,
                turn_count,
                triggered_by,
                has_error,
                status_code
            FROM conversation_stats
            ORDER BY start_time DESC
            LIMIT :limit OFFSET :offset
        """)
        # Get total count
        count_query = text(f"""
            SELECT COUNT(DISTINCT conversation_id)
            FROM {table_name}
            WHERE {where_clause}
        """)

        total_result = snowflake_db.execute(count_query).fetchone()
        total = total_result[0] if total_result else 0

        # Get conversations
        results = snowflake_db.execute(
            query, {"limit": limit, "offset": offset}
        ).fetchall()

        conversations = [
            ConversationSummary(
                conversation_id=row[0],
                start_time=row[1],
                end_time=row[2],
                duration_ms=int(row[3]) if row[3] else None,
                turn_count=row[4],
                triggered_by=row[5],
                has_error=bool(row[6]),
                status_code=row[7],
            )
            for row in results
        ]

        return ConversationsResponse(
            conversations=conversations, total=total, limit=limit, offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to query conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to query conversations: {str(e)}"
        )


@router.get(
    "/{project_id}/conversations/{conversation_id}",
    response_model=ConversationDetails,
)
async def get_conversation_details(
    project_id: int,
    conversation_id: str,
    sqlite_db: Session = Depends(get_db),
    snowflake_db: Session = Depends(get_snowflake_db),
):
    """Get full conversation details with messages from Snowflake."""

    # Get project from SQLite
    project = sqlite_db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if Snowflake is configured
    if snowflake_db is None:
        raise HTTPException(status_code=503, detail="Snowflake is not configured")

    # Determine table name
    if project.source_database and project.source_schema and project.source_table:
        table_name = (
            f"{project.source_database}.{project.source_schema}.{project.source_table}"
        )
    else:
        database = os.getenv("SNOWFLAKE_DATABASE", "AI_FDE")
        schema = os.getenv("SNOWFLAKE_SCHEMA", "CX360_DEMO")
        table_name = f"{database}.{schema}.AGENT_TRACES"

    logger.info(f"Querying conversation {conversation_id} from table: {table_name}")

    try:
        # Query for all turns in the conversation
        query = text(f"""
            SELECT
                conversation_id,
                MIN(start_time) as start_time,
                MAX(end_time) as end_time,
                DATEDIFF('millisecond', MIN(start_time), MAX(end_time)) as duration_ms,
                COUNT(*) as turn_count,
                MAX(triggered_by) as triggered_by,
                MAX(CASE WHEN status_code != '200' THEN 1 ELSE 0 END) as has_error
            FROM {table_name}
            WHERE conversation_id = :conversation_id
            GROUP BY conversation_id
        """)

        result = snowflake_db.execute(
            query, {"conversation_id": conversation_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Query for messages
        messages_query = text(f"""
            SELECT
                input_text,
                output_text,
                start_time,
                end_time
            FROM {table_name}
            WHERE conversation_id = :conversation_id
            ORDER BY start_time ASC
        """)

        message_results = snowflake_db.execute(
            messages_query, {"conversation_id": conversation_id}
        ).fetchall()

        # Build messages list (user input, then assistant output for each turn)
        messages = []
        for row in message_results:
            input_text = row[0]
            output_text = row[1]
            start_time = row[2]
            end_time = row[3]

            # Add user message
            if input_text:
                messages.append(
                    ConversationMessage(
                        role="user",
                        content=input_text,
                        timestamp=start_time,
                    )
                )

            # Add assistant message
            if output_text:
                messages.append(
                    ConversationMessage(
                        role="assistant",
                        content=output_text,
                        timestamp=end_time,
                    )
                )

        return ConversationDetails(
            conversation_id=result[0],
            start_time=result[1],
            end_time=result[2],
            duration_ms=int(result[3]) if result[3] else None,
            turn_count=result[4],
            triggered_by=result[5],
            has_error=bool(result[6]),
            messages=messages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query conversation details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query conversation details: {str(e)}",
        )
