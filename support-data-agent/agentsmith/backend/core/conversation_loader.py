"""Load real conversations from Snowflake AGENT_TRACES table."""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.core.interfaces import Scenario, Persona

logger = logging.getLogger(__name__)


class ConversationLoader:
    """Load and transform real chatbot conversations from Snowflake AGENT_TRACES."""

    def __init__(self, db: Session, project=None):
        """Initialize conversation loader.

        Args:
            db: Database session (Snowflake connection)
            project: Optional Project model instance with source table config
        """
        self.db = db

        # Get table name from project config or fall back to environment
        if (
            project
            and project.source_database
            and project.source_schema
            and project.source_table
        ):
            # Use project-specific table
            self.table_name = f"{project.source_database}.{project.source_schema}.{project.source_table}"
            logger.info(f"Using project-specific table: {self.table_name}")
        else:
            # Fall back to environment variables
            database = os.getenv("SNOWFLAKE_DATABASE", "AI_FDE")
            schema = os.getenv("SNOWFLAKE_SCHEMA", "CX360_DEMO")
            self.table_name = f"{database}.{schema}.AGENT_TRACES"
            logger.info(f"Using environment table: {self.table_name}")

    async def load_conversations(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        conversation_ids: Optional[List[str]] = None,
        triggered_by: Optional[str] = None,
        include_errors_only: bool = False,
        limit: Optional[int] = 100,
    ) -> List[Scenario]:
        """Load conversations from Snowflake AGENT_TRACES table.

        Args:
            date_from: Start date for conversation filter (default: 7 days ago)
            date_to: End date for conversation filter (default: now)
            conversation_ids: Specific conversation IDs to load
            triggered_by: Filter by interaction type ('voice' or 'text')
            include_errors_only: Only load conversations with errors
            limit: Maximum number of conversations to load

        Returns:
            List of Scenario objects representing real conversations
        """
        # Set default date range: last 7 days
        if date_to is None:
            date_to = datetime.utcnow()
        if date_from is None:
            date_from = date_to - timedelta(days=7)

        logger.info(
            f"Loading conversations from {date_from} to {date_to}, limit={limit}"
        )

        # Build query to get unique conversation IDs with metadata
        query = f"""
            SELECT
                conversation_id,
                MIN(start_time) as session_start,
                MAX(end_time) as session_end,
                COUNT(DISTINCT trace_id) as message_count,
                SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) as error_count,
                AVG(latency_ms) as avg_latency_ms,
                MAX(CASE WHEN triggered_by IS NOT NULL THEN triggered_by ELSE 'unknown' END) as interaction_type
            FROM {self.table_name}
            WHERE conversation_id IS NOT NULL
                AND start_time >= :date_from
                AND start_time <= :date_to
        """

        params = {"date_from": date_from, "date_to": date_to}

        # Add filters
        if conversation_ids:
            placeholders = ",".join(
                [f":conv_id_{i}" for i in range(len(conversation_ids))]
            )
            query += f" AND conversation_id IN ({placeholders})"
            for i, conv_id in enumerate(conversation_ids):
                params[f"conv_id_{i}"] = conv_id

        if triggered_by:
            query += " AND triggered_by = :triggered_by"
            params["triggered_by"] = triggered_by

        query += " GROUP BY conversation_id"

        if include_errors_only:
            query += (
                " HAVING SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) > 0"
            )

        query += " ORDER BY session_start DESC"

        if limit:
            query += f" LIMIT {limit}"

        # Execute query to get conversation list
        result = self.db.execute(text(query), params)
        conversations_meta = result.fetchall()

        logger.info(f"Found {len(conversations_meta)} conversations to load")

        if not conversations_meta:
            return []

        # OPTIMIZATION: Batch load all messages for all conversations in a single query
        # This replaces N individual queries with 1 batch query
        conversation_ids = [conv.conversation_id for conv in conversations_meta]

        # Build batch query to get all messages for all conversations
        messages_query = f"""
            SELECT
                conversation_id,
                trace_id,
                start_time,
                end_time,
                input_text,
                output_text,
                latency_ms,
                token_count_input,
                token_count_output,
                model_name,
                status_code,
                status_message
            FROM {self.table_name}
            WHERE conversation_id IN ({",".join([f":conv_id_{i}" for i in range(len(conversation_ids))])})
                AND name = 'api.query'
                AND (input_text IS NOT NULL OR output_text IS NOT NULL)
            ORDER BY conversation_id, start_time ASC
        """

        messages_params = {
            f"conv_id_{i}": conv_id for i, conv_id in enumerate(conversation_ids)
        }

        logger.info(
            f"Batch loading messages for {len(conversation_ids)} conversations..."
        )
        messages_result = self.db.execute(text(messages_query), messages_params)
        all_messages = messages_result.fetchall()

        logger.info(f"Loaded {len(all_messages)} total messages in batch")

        # Group messages by conversation_id
        messages_by_conversation = {}
        for msg in all_messages:
            if msg.conversation_id not in messages_by_conversation:
                messages_by_conversation[msg.conversation_id] = []
            messages_by_conversation[msg.conversation_id].append(msg)

        # Transform each conversation into a Scenario
        scenarios = []
        for conv_meta in conversations_meta:
            try:
                messages = messages_by_conversation.get(conv_meta.conversation_id, [])
                if not messages:
                    logger.warning(
                        f"No messages found for conversation {conv_meta.conversation_id}"
                    )
                    continue

                scenario = await self._build_scenario_from_messages(
                    conv_meta.conversation_id,
                    conv_meta.interaction_type,
                    conv_meta.error_count > 0,
                    messages,
                )
                if scenario:
                    scenarios.append(scenario)
            except Exception as e:
                logger.error(
                    f"Error loading conversation {conv_meta.conversation_id}: {e}",
                    exc_info=True,
                )
                continue

        logger.info(f"Successfully loaded {len(scenarios)} conversations")
        return scenarios

    async def _build_scenario_from_messages(
        self,
        conversation_id: str,
        interaction_type: str,
        has_errors: bool,
        messages: List[Any],
    ) -> Optional[Scenario]:
        """Build a Scenario from pre-loaded conversation messages.

        Args:
            conversation_id: Unique conversation ID from Snowflake
            interaction_type: 'voice', 'text', or 'unknown'
            has_errors: Whether conversation had any errors
            messages: List of pre-loaded message records

        Returns:
            Scenario object with persona, goal, and initial query
        """
        if not messages:
            logger.warning(f"No messages provided for conversation {conversation_id}")
            return None

        # Extract first user message as initial query
        first_message = messages[0]
        initial_query = first_message.input_text or "No initial query"

        # Infer persona from interaction type and first message
        persona = self._infer_persona(
            interaction_type, initial_query, len(messages), has_errors
        )

        # Create scenario from real conversation
        scenario = Scenario(
            persona=persona,
            initial_query=initial_query,
            expected_outcome=self._infer_expected_outcome(messages),
            complexity=self._infer_complexity(messages),
            category=self._infer_category(initial_query),
            metadata={
                "source": "snowflake_agent_traces",
                "conversation_id": conversation_id,
                "interaction_type": interaction_type,
                "message_count": len(messages),
                "has_errors": has_errors,
                "session_start": messages[0].start_time.isoformat()
                if messages[0].start_time
                else None,
                "session_end": messages[-1].end_time.isoformat()
                if messages[-1].end_time
                else None,
                # Store the actual messages for replay
                "messages": [
                    {
                        "role": "user",
                        "content": msg.input_text or "",
                        "timestamp": msg.start_time.isoformat()
                        if msg.start_time
                        else None,
                        "latency_ms": msg.latency_ms,
                        "token_count": msg.token_count_input,
                    }
                    if msg.input_text
                    else {
                        "role": "assistant",
                        "content": msg.output_text or "",
                        "timestamp": msg.end_time.isoformat() if msg.end_time else None,
                        "latency_ms": msg.latency_ms,
                        "token_count": msg.token_count_output,
                    }
                    for msg in messages
                ],
            },
        )

        return scenario

    def _infer_persona(
        self,
        interaction_type: str,
        initial_query: str,
        message_count: int,
        has_errors: bool,
    ) -> Persona:
        """Infer user persona from conversation metadata and first message.

        Args:
            interaction_type: voice/text/unknown
            initial_query: First user message
            message_count: Number of turns
            has_errors: Whether conversation had errors

        Returns:
            Persona object with inferred characteristics
        """
        # Infer technical level from query complexity
        query_lower = initial_query.lower()
        technical_keywords = [
            "api",
            "sql",
            "query",
            "warehouse",
            "schema",
            "cluster",
            "performance",
            "optimization",
        ]
        has_technical_terms = any(kw in query_lower for kw in technical_keywords)

        technical_level = "expert" if has_technical_terms else "beginner"

        # Infer tone from interaction type
        tone = "conversational" if interaction_type == "voice" else "professional"

        # Determine if edge case based on errors and length
        is_edge_case = has_errors or message_count > 10

        return Persona(
            name=f"{interaction_type.title()} User",
            goal="Get help with their question",
            tone=tone,
            personality_traits=[
                "patient" if message_count > 5 else "direct",
                "technical" if has_technical_terms else "non-technical",
            ],
            technical_level=technical_level,
            edge_case=is_edge_case,
        )

    def _infer_expected_outcome(self, messages: List[Any]) -> str:
        """Infer expected outcome from conversation messages.

        Args:
            messages: List of message records

        Returns:
            String describing expected outcome
        """
        # Check if conversation ended successfully
        last_message = messages[-1]
        if last_message.status_code == "ERROR":
            return "Resolve error and provide helpful response"

        # Default: expect resolution
        return "Receive helpful answer to question"

    def _infer_complexity(self, messages: List[Any]) -> str:
        """Infer conversation complexity from message count and content.

        Args:
            messages: List of message records

        Returns:
            Complexity level: simple, medium, or complex
        """
        message_count = len(messages)

        if message_count <= 2:
            return "simple"
        elif message_count <= 5:
            return "medium"
        else:
            return "complex"

    def _infer_category(self, initial_query: str) -> str:
        """Infer conversation category from initial query.

        Args:
            initial_query: First user message

        Returns:
            Category string
        """
        query_lower = initial_query.lower()

        # Category keywords
        categories = {
            "technical": ["api", "sql", "query", "error", "code", "syntax"],
            "billing": ["billing", "cost", "price", "invoice", "payment"],
            "account": ["account", "login", "password", "access", "permission"],
            "performance": ["slow", "performance", "optimize", "speed", "latency"],
            "general": [],  # default
        }

        # Find best matching category
        for category, keywords in categories.items():
            if any(kw in query_lower for kw in keywords):
                return category

        return "general"

    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Scenario]:
        """Get a specific conversation by ID.

        Args:
            conversation_id: Snowflake conversation ID

        Returns:
            Scenario object or None if not found
        """
        # Query conversation metadata
        query = f"""
            SELECT
                conversation_id,
                MIN(start_time) as session_start,
                MAX(end_time) as session_end,
                COUNT(DISTINCT trace_id) as message_count,
                SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) as error_count,
                MAX(CASE WHEN triggered_by IS NOT NULL THEN triggered_by ELSE 'unknown' END) as interaction_type
            FROM {self.table_name}
            WHERE conversation_id = :conversation_id
            GROUP BY conversation_id
        """

        result = self.db.execute(text(query), {"conversation_id": conversation_id})
        conv_meta = result.fetchone()

        if not conv_meta:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        # Load messages for this conversation
        messages_query = f"""
            SELECT
                trace_id,
                start_time,
                end_time,
                input_text,
                output_text,
                latency_ms,
                token_count_input,
                token_count_output,
                model_name,
                status_code,
                status_message
            FROM {self.table_name}
            WHERE conversation_id = :conversation_id
                AND name = 'api.query'
                AND (input_text IS NOT NULL OR output_text IS NOT NULL)
            ORDER BY start_time ASC
        """

        messages_result = self.db.execute(
            text(messages_query), {"conversation_id": conversation_id}
        )
        messages = messages_result.fetchall()

        if not messages:
            logger.warning(f"No messages found for conversation {conversation_id}")
            return None

        return await self._build_scenario_from_messages(
            conv_meta.conversation_id,
            conv_meta.interaction_type,
            conv_meta.error_count > 0,
            messages,
        )
