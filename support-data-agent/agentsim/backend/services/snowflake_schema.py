"""Snowflake schema management for AgentSim using Snowpark.

This module creates and manages Snowflake tables for AgentSim,
following the same pattern as 360app's schema_manager.py.
"""

import os
from snowflake.snowpark import Session
from ..config import get_logger

logger = get_logger(__name__)

_session = None


def get_snowpark_session() -> Session:
    """Get or create Snowflake Snowpark session."""
    global _session
    if _session is None:
        try:
            connection_params = {
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "user": os.getenv("SNOWFLAKE_USER"),
                "password": os.getenv("SNOWFLAKE_PASSWORD"),
                "database": os.getenv("SNOWFLAKE_DATABASE", "AGENTSIM_DB"),
                "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
                "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
                "role": os.getenv("SNOWFLAKE_ROLE"),
            }

            # Validate required parameters
            required = ["account", "user", "password", "warehouse"]
            missing = [k for k in required if not connection_params.get(k)]
            if missing:
                raise ValueError(f"Missing required Snowflake config: {', '.join(missing)}")

            logger.info("Creating Snowflake session for AgentSim")
            _session = Session.builder.configs(connection_params).create()
            logger.info("Snowflake session created successfully")

        except Exception as e:
            logger.error(f"Failed to create Snowflake session: {e}")
            raise

    return _session


class AgentSimSchemaManager:
    """Manages Snowflake schema for AgentSim tables."""

    def __init__(self):
        self.session = get_snowpark_session()

    def create_tables(self) -> dict:
        """Create all AgentSim tables in Snowflake."""
        logger.info("Creating AgentSim tables in Snowflake")

        try:
            self._create_projects_table()
            self._create_persona_templates_table()
            self._create_simulations_table()
            self._create_conversations_table()
            self._create_messages_table()
            self._create_conversation_metrics_table()
            self._create_improvement_suggestions_table()
            self._add_table_comments()

            logger.info("AgentSim schema creation completed")
            return {"success": True, "tables_created": 7}

        except Exception as e:
            logger.error(f"Schema creation failed: {e}")
            raise

    def _create_projects_table(self):
        """Create PROJECTS table for agent project configurations."""
        sql = """
        CREATE TABLE IF NOT EXISTS PROJECTS (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            NAME VARCHAR(255) NOT NULL,
            DESCRIPTION TEXT,
            BUSINESS_CONTEXT TEXT NOT NULL,
            AGENT_ENDPOINT VARCHAR(512) NOT NULL,
            AUTH_TYPE VARCHAR(20) NOT NULL,
            AUTH_CREDENTIALS VARIANT,
            CUSTOM_HEADERS VARIANT,
            CONVERSATION_EXAMPLES VARIANT,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created PROJECTS table")

    def _create_persona_templates_table(self):
        """Create PERSONA_TEMPLATES table for reusable test personas."""
        sql = """
        CREATE TABLE IF NOT EXISTS PERSONA_TEMPLATES (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            PROJECT_ID INTEGER NOT NULL,
            NAME VARCHAR(255) NOT NULL,
            GOAL TEXT NOT NULL,
            TONE VARCHAR(50) DEFAULT 'professional',
            PERSONALITY_TRAITS VARIANT NOT NULL,
            TECHNICAL_LEVEL VARCHAR(50) DEFAULT 'intermediate',
            EDGE_CASE BOOLEAN DEFAULT FALSE,
            DEFAULT_QUERY TEXT,
            EXPECTED_OUTCOME TEXT,
            COMPLEXITY VARCHAR(50) DEFAULT 'simple',
            CATEGORY VARCHAR(100) DEFAULT 'general',
            KNOWLEDGE_BASE VARIANT,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            FOREIGN KEY (PROJECT_ID) REFERENCES PROJECTS(ID)
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created PERSONA_TEMPLATES table")

    def _create_simulations_table(self):
        """Create SIMULATIONS table for simulation runs."""
        sql = """
        CREATE TABLE IF NOT EXISTS SIMULATIONS (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            PROJECT_ID INTEGER NOT NULL,
            NUM_SIMULATIONS INTEGER NOT NULL,
            CONCURRENCY INTEGER DEFAULT 1,
            MAX_TURNS INTEGER DEFAULT 20,
            TIMEOUT_SECONDS INTEGER DEFAULT 300,
            STOP_CONDITIONS VARIANT NOT NULL,
            METRICS_CONFIG VARIANT NOT NULL,
            CUSTOM_SCENARIOS VARIANT,
            STATUS VARCHAR(20) DEFAULT 'pending',
            STARTED_AT TIMESTAMP_NTZ,
            COMPLETED_AT TIMESTAMP_NTZ,
            ERROR_MESSAGE TEXT,
            LLM_INSIGHTS_GENERATED BOOLEAN DEFAULT FALSE,
            LLM_INSIGHTS_GENERATED_AT TIMESTAMP_NTZ,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            FOREIGN KEY (PROJECT_ID) REFERENCES PROJECTS(ID)
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created SIMULATIONS table")

    def _create_conversations_table(self):
        """Create CONVERSATIONS table for individual conversations."""
        sql = """
        CREATE TABLE IF NOT EXISTS CONVERSATIONS (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            SIMULATION_ID INTEGER NOT NULL,
            PERSONA VARIANT NOT NULL,
            SCENARIO VARIANT NOT NULL,
            SUCCESS BOOLEAN DEFAULT FALSE,
            NUM_TURNS INTEGER DEFAULT 0,
            TOTAL_DURATION_MS FLOAT DEFAULT 0.0,
            STOP_REASON VARCHAR(255),
            STARTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            COMPLETED_AT TIMESTAMP_NTZ,
            FOREIGN KEY (SIMULATION_ID) REFERENCES SIMULATIONS(ID)
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created CONVERSATIONS table")

    def _create_messages_table(self):
        """Create MESSAGES table for conversation messages."""
        sql = """
        CREATE TABLE IF NOT EXISTS MESSAGES (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            CONVERSATION_ID INTEGER NOT NULL,
            ROLE VARCHAR(50) NOT NULL,
            CONTENT TEXT NOT NULL,
            TOOL_CALLS VARIANT,
            LATENCY_MS FLOAT,
            TOKEN_COUNT INTEGER,
            TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            FOREIGN KEY (CONVERSATION_ID) REFERENCES CONVERSATIONS(ID)
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created MESSAGES table")

    def _create_conversation_metrics_table(self):
        """Create CONVERSATION_METRICS table for performance metrics."""
        sql = """
        CREATE TABLE IF NOT EXISTS CONVERSATION_METRICS (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            CONVERSATION_ID INTEGER NOT NULL,
            METRIC_NAME VARCHAR(255) NOT NULL,
            METRIC_VALUE FLOAT NOT NULL,
            META_DATA VARIANT,
            FOREIGN KEY (CONVERSATION_ID) REFERENCES CONVERSATIONS(ID)
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created CONVERSATION_METRICS table")

    def _create_improvement_suggestions_table(self):
        """Create IMPROVEMENT_SUGGESTIONS table for AI-generated insights."""
        sql = """
        CREATE TABLE IF NOT EXISTS IMPROVEMENT_SUGGESTIONS (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            SIMULATION_ID INTEGER NOT NULL,
            CATEGORY VARCHAR(100) NOT NULL,
            TITLE VARCHAR(255) NOT NULL,
            DESCRIPTION TEXT NOT NULL,
            PRIORITY VARCHAR(50) NOT NULL,
            EVIDENCE VARIANT NOT NULL,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            FOREIGN KEY (SIMULATION_ID) REFERENCES SIMULATIONS(ID)
        )
        """
        self.session.sql(sql).collect()
        logger.info("Created IMPROVEMENT_SUGGESTIONS table")

    def _add_table_comments(self):
        """Add descriptive comments to tables."""
        comments = {
            "PROJECTS": "Agent project configurations with endpoint and auth details",
            "PERSONA_TEMPLATES": "Reusable test personas for simulations",
            "SIMULATIONS": "Simulation runs with configuration and status",
            "CONVERSATIONS": "Individual conversations within simulations",
            "MESSAGES": "Messages exchanged in conversations",
            "CONVERSATION_METRICS": "Performance metrics calculated for conversations",
            "IMPROVEMENT_SUGGESTIONS": "AI-generated insights and recommendations",
        }

        for table, comment in comments.items():
            try:
                self.session.sql(f"COMMENT ON TABLE {table} IS '{comment}'").collect()
            except Exception as e:
                logger.warning(f"Failed to add comment to {table}: {e}")

    def drop_all_tables(self) -> dict:
        """Drop all AgentSim tables (careful!)."""
        tables = [
            "IMPROVEMENT_SUGGESTIONS",
            "CONVERSATION_METRICS",
            "MESSAGES",
            "CONVERSATIONS",
            "SIMULATIONS",
            "PERSONA_TEMPLATES",
            "PROJECTS",
        ]

        try:
            for table in tables:
                self.session.sql(f"DROP TABLE IF EXISTS {table}").collect()
                logger.info(f"Dropped table: {table}")

            return {"success": True, "dropped_tables": tables}

        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def get_schema_status(self) -> dict:
        """Get status of all AgentSim tables."""
        tables = [
            "PROJECTS",
            "PERSONA_TEMPLATES",
            "SIMULATIONS",
            "CONVERSATIONS",
            "MESSAGES",
            "CONVERSATION_METRICS",
            "IMPROVEMENT_SUGGESTIONS",
        ]
        status = {}

        for table in tables:
            try:
                count = self.session.table(table).count()
                status[table] = {"exists": True, "row_count": count}
            except Exception:
                status[table] = {"exists": False, "row_count": 0}

        return status


def initialize_snowflake_schema() -> dict:
    """Initialize AgentSim schema in Snowflake."""
    return AgentSimSchemaManager().create_tables()


def reset_snowflake_schema() -> dict:
    """Drop and recreate all tables (WARNING: destroys all data!)."""
    manager = AgentSimSchemaManager()
    manager.drop_all_tables()
    return manager.create_tables()
