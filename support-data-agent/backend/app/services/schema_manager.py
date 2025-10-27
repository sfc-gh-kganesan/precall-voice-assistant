"""Schema management using Snowpark DataFrame API."""

import json

from snowflake.snowpark.functions import col, current_timestamp, parse_json
from snowflake.snowpark.types import StringType, StructField, StructType

from ..config import snowflake_settings
from ..logging_config import get_logger
from . import snowflake as snowflake_service
from .fake_case_generator import generate_fake_cases

logger = get_logger(__name__)


class SchemaManager:
    def __init__(self):
        self.session = snowflake_service._get_session()

    def create_tables(self, include_sample_data: bool = False, num_cases: int = 100) -> dict[str, bool]:
        logger.info(f"Creating tables with sample_data={include_sample_data}")

        try:
            self._create_cases_table()
            self._create_topics_table()
            self._create_products_table()
            self._create_kpi_summary_table()
            self._create_configurations_table()
            self._create_generation_jobs_table()
            self._create_views()

            if include_sample_data:
                self._insert_sample_data(num_cases=num_cases)
            else:
                self._insert_minimal_data()

            self._add_table_comments()

            logger.info("Schema creation completed")
            return {
                "success": True,
                "sample_data": include_sample_data,
                "num_cases": num_cases if include_sample_data else 0,
            }

        except Exception as e:
            logger.error(f"Schema creation failed: {str(e)}")
            raise

    def clean_schema(self) -> dict[str, bool]:
        logger.info("Cleaning schema")

        try:
            tables_to_drop = [
                "TOPICS",
                "PRODUCTS",
                "KPI_SUMMARY",
                "GENERATION_JOBS",
                "CONFIGURATIONS",
            ]
            for table in tables_to_drop:
                self.session.sql(f"DROP TABLE IF EXISTS {table}").collect()

            self.session.sql("""
                UPDATE CASES
                SET GENERATED_TOPIC = NULL, GENERATED_PRODUCT = NULL,
                    GENERATED_PRODUCT_CATEGORY = NULL, GENERATED_SENTIMENT = NULL,
                    ENRICHED_AT = NULL
            """).collect()

            self._create_topics_table()
            self._create_products_table()
            self._create_kpi_summary_table()
            self._create_configurations_table()
            self._create_generation_jobs_table()
            self._insert_minimal_data()
            self._add_table_comments()

            logger.info("Schema cleaning completed")
            return {"success": True, "cleaned": True}

        except Exception as e:
            logger.error(f"Schema cleaning failed: {str(e)}")
            raise

    def _create_cases_table(self):
        """
        Create the CASES table for demo purposes.

        NOTE: This creates a hardcoded 'CASES' table for demo/development.
        In production, table names should be driven by user configuration.
        """
        create_sql = """
        CREATE OR REPLACE TABLE CASES (
            ID VARCHAR(50) PRIMARY KEY,
            CASE_NUMBER VARCHAR(20) NOT NULL,
            CREATED_AT TIMESTAMP_NTZ NOT NULL,
            UPDATED_AT TIMESTAMP_NTZ NOT NULL,
            CLOSED_AT TIMESTAMP_NTZ,
            LAST_MODIFIED_AT TIMESTAMP_NTZ NOT NULL,
            STATUS VARCHAR(50) NOT NULL,
            SEVERITY VARCHAR(100) NOT NULL,
            INITIAL_SEVERITY VARCHAR(100),
            PEAK_SEVERITY VARCHAR(100),
            SUBJECT VARCHAR(500) NOT NULL,
            DESCRIPTION TEXT,
            ACCOUNT_ID VARCHAR(50),
            ACCOUNT_NAME VARCHAR(255),
            IS_PRIORITY_SUPPORT BOOLEAN,
            TOTAL_COMMENTS INTEGER,
            HAS_JIRA_ISSUES BOOLEAN,
            HAS_ESCALATIONS BOOLEAN,
            HAS_COLLABORATIONS BOOLEAN,
            GENERATED_TOPIC VARCHAR(100),
            GENERATED_PRODUCT_CATEGORY VARCHAR(100),
            GENERATED_PRODUCT VARCHAR(100),
            GENERATED_FEATURE VARCHAR(100),
            GENERATED_SENTIMENT VARCHAR(20),
            RESOLUTION_TIME_HOURS FLOAT,
            SLA_VIOLATED BOOLEAN,
            ENRICHED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(create_sql).collect()

    def _create_topics_table(self):
        create_sql = """
        CREATE OR REPLACE TABLE TOPICS (
            TOPIC_ID VARCHAR(50) PRIMARY KEY,
            TOPIC_SLUG VARCHAR(100) NOT NULL,
            TOPIC_NAME VARCHAR(100) NOT NULL,
            PERIOD VARCHAR(20) NOT NULL,
            START_DATE DATE NOT NULL,
            END_DATE DATE NOT NULL,
            TOTAL_CASES INTEGER NOT NULL,
            PREVIOUS_CASES INTEGER DEFAULT 0,
            CHANGE_ABSOLUTE INTEGER DEFAULT 0,
            CHANGE_PERCENTAGE FLOAT DEFAULT 0.0,
            CHANGE_TYPE VARCHAR(20) DEFAULT 'stable',
            AVG_RESOLUTION_TIME FLOAT DEFAULT 0.0,
            RESOLUTION_RATE FLOAT DEFAULT 0.0,
            SENTIMENT_POSITIVE FLOAT DEFAULT 0.0,
            SENTIMENT_NEUTRAL FLOAT DEFAULT 0.0,
            SENTIMENT_NEGATIVE FLOAT DEFAULT 0.0,
            TOP_PRODUCTS VARIANT,
            AI_SUMMARY TEXT,
            CUSTOMER_FEEDBACK TEXT,
            SENTIMENT_ANALYSIS TEXT,
            TOP_ISSUES TEXT,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(create_sql).collect()

    def _create_products_table(self):
        create_sql = """
        CREATE OR REPLACE TABLE PRODUCTS (
            PRODUCT_ID VARCHAR(50) PRIMARY KEY,
            PRODUCT_SLUG VARCHAR(100) NOT NULL,
            PRODUCT_NAME VARCHAR(100) NOT NULL,
            PRODUCT_CATEGORY VARCHAR(100) NOT NULL,
            PERIOD VARCHAR(20) NOT NULL,
            START_DATE DATE NOT NULL,
            END_DATE DATE NOT NULL,
            METRICS VARIANT NOT NULL,
            TOP_ISSUES VARIANT,
            TREND_DATA VARIANT,
            AI_SUMMARY TEXT,
            CUSTOMER_FEEDBACK TEXT,
            ROOT_CAUSES TEXT,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(create_sql).collect()

    def _create_kpi_summary_table(self):
        create_sql = """
        CREATE OR REPLACE TABLE KPI_SUMMARY (
            KPI_ID VARCHAR(50) PRIMARY KEY,
            PERIOD VARCHAR(20) NOT NULL,
            START_DATE DATE NOT NULL,
            END_DATE DATE NOT NULL,
            TOTAL_CASES INTEGER NOT NULL,
            AVG_CASE_LIFE_HOURS FLOAT NOT NULL,
            RESOLUTION_RATE_PERCENT FLOAT NOT NULL,
            FIRST_RESPONSE_TIME_HOURS FLOAT DEFAULT 0.0,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(create_sql).collect()

    def _create_configurations_table(self):
        create_sql = """
        CREATE OR REPLACE TABLE CONFIGURATIONS (
            CONFIG_ID VARCHAR(50) PRIMARY KEY,
            NAME VARCHAR(255) NOT NULL UNIQUE,
            DATABASE_NAME VARCHAR(255) NOT NULL,
            SCHEMA_NAME VARCHAR(255) NOT NULL,
            TABLES VARIANT NOT NULL,
            OUTPUT_TABLE VARCHAR(255) NOT NULL,
            MAPPINGS VARIANT NOT NULL,
            STATUS VARCHAR(20) DEFAULT 'draft',
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(create_sql).collect()

    def _create_generation_jobs_table(self):
        create_sql = """
        CREATE OR REPLACE TABLE GENERATION_JOBS (
            JOB_ID VARCHAR(50) PRIMARY KEY,
            CONFIG_ID VARCHAR(50),
            JOB_TYPE VARCHAR(20) NOT NULL,
            STATUS VARCHAR(20) DEFAULT 'queued',
            PROGRESS INTEGER DEFAULT 0,
            ESTIMATED_TIME INTEGER,
            PROCESSED_RECORDS INTEGER DEFAULT 0,
            ERROR_RECORDS INTEGER DEFAULT 0,
            ERROR_MESSAGE TEXT,
            STARTED_AT TIMESTAMP_NTZ,
            COMPLETED_AT TIMESTAMP_NTZ,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        self.session.sql(create_sql).collect()

    def _create_views(self):
        view_sql = """
        CREATE OR REPLACE VIEW CASES_WITH_METRICS AS
        SELECT
            c.*,
            DATEDIFF('hour', c.CREATED_AT, COALESCE(c.CLOSED_AT, CURRENT_TIMESTAMP())) AS CURRENT_AGE_HOURS,
            CASE
                WHEN c.STATUS = 'Closed' THEN 'Resolved'
                WHEN c.STATUS IN ('New', 'In Progress') THEN 'Open'
                ELSE 'Pending'
            END AS STATUS_CATEGORY,
            CASE
                WHEN c.SEVERITY LIKE 'Severity-1%' THEN 1
                WHEN c.SEVERITY LIKE 'Severity-2%' THEN 2
                WHEN c.SEVERITY LIKE 'Severity-3%' THEN 3
                ELSE 4
            END AS SEVERITY_LEVEL
        FROM CASES c
        """
        self.session.sql(view_sql).collect()

    def _insert_minimal_data(self):
        # Get the actual configured schema and database from environment
        connection_params = snowflake_settings.get_connection_params()
        configured_schema = connection_params.get("schema", "PUBLIC")
        configured_database = connection_params.get("database", "SDA")

        config_data = [
            {
                "CONFIG_ID": "config_default_cases",
                "NAME": "Default Cases Configuration",
                "DATABASE_NAME": configured_database,
                "SCHEMA_NAME": configured_schema,
                "TABLES": '["CASES"]',
                "OUTPUT_TABLE": "CASES",
                "MAPPINGS": json.dumps(
                    [
                        {
                            "targetField": "topic",
                            "sourceType": "generated",
                            "sourceColumns": ["SUBJECT", "DESCRIPTION"],
                            "aiInstruction": "Classify the support ticket into topics: "
                            "Performance & Optimization, Authentication & Access, Data Loading & Ingestion, etc.",
                            "generationType": "llm",
                        },
                        {
                            "targetField": "product",
                            "sourceType": "generated",
                            "sourceColumns": ["SUBJECT", "DESCRIPTION"],
                            "aiInstruction": "Identify the Snowflake product: "
                            "Query Performance, Data Storage, Virtual Warehouses, Snowpipe, Tasks & Streams, etc.",
                            "generationType": "llm",
                        },
                    ]
                ),
                "STATUS": "active",
            }
        ]

        schema = StructType(
            [
                StructField("CONFIG_ID", StringType()),
                StructField("NAME", StringType()),
                StructField("DATABASE_NAME", StringType()),
                StructField("SCHEMA_NAME", StringType()),
                StructField("TABLES", StringType()),
                StructField("OUTPUT_TABLE", StringType()),
                StructField("MAPPINGS", StringType()),
                StructField("STATUS", StringType()),
            ]
        )

        config_df = self.session.create_dataframe(config_data, schema)

        final_df = config_df.select(
            col("CONFIG_ID"),
            col("NAME"),
            col("DATABASE_NAME"),
            col("SCHEMA_NAME"),
            parse_json(col("TABLES")).alias("TABLES"),
            col("OUTPUT_TABLE"),
            parse_json(col("MAPPINGS")).alias("MAPPINGS"),
            col("STATUS"),
            current_timestamp().alias("CREATED_AT"),
            current_timestamp().alias("UPDATED_AT"),
        )

        final_df.write.mode("append").save_as_table("CONFIGURATIONS")

    def _insert_sample_data(self, num_cases: int = 100):
        """
        Insert sample data including fake cases.

        Args:
            num_cases: Number of fake cases to generate (default: 100)
        """
        self._insert_minimal_data()

        logger.info(f"Generating {num_cases} fake support cases...")
        fake_cases_sql = generate_fake_cases(num_cases)
        self.session.sql(fake_cases_sql).collect()
        logger.info(f"Successfully inserted {num_cases} fake cases")

    def _add_table_comments(self):
        comments = {
            "CASES": "Main support case data with AI-generated taxonomy fields",
            "TOPICS": "Topic-level metrics generated from case data",
            "PRODUCTS": "Product-level metrics generated from case data",
            "KPI_SUMMARY": "KPI summary calculated from case data",
            "CONFIGURATIONS": "Configuration for enrichment jobs",
            "GENERATION_JOBS": "Tracks enrichment job execution",
        }

        for table, comment in comments.items():
            self.session.sql(f"COMMENT ON TABLE {table} IS '{comment}'").collect()

    def drop_all_tables(self) -> dict[str, bool]:
        tables = [
            "GENERATION_JOBS",
            "CONFIGURATIONS",
            "KPI_SUMMARY",
            "PRODUCTS",
            "TOPICS",
            "CASES",
        ]

        try:
            for table in tables:
                self.session.sql(f"DROP TABLE IF EXISTS {table}").collect()
            self.session.sql("DROP VIEW IF EXISTS CASES_WITH_METRICS").collect()

            return {"success": True, "dropped_tables": tables}

        except Exception as e:
            logger.error(f"Failed to drop tables: {str(e)}")
            raise

    def get_schema_status(self) -> dict[str, any]:
        tables = [
            "CASES",
            "TOPICS",
            "PRODUCTS",
            "KPI_SUMMARY",
            "CONFIGURATIONS",
            "GENERATION_JOBS",
        ]
        status = {}

        for table in tables:
            try:
                count = self.session.table(table).count()
                status[table] = {"exists": True, "row_count": count}
            except Exception:
                status[table] = {"exists": False, "row_count": 0}

        return status


def initialize_schema(include_sample_data: bool = False, num_cases: int = 100) -> dict[str, bool]:
    return SchemaManager().create_tables(include_sample_data=include_sample_data, num_cases=num_cases)


def clean_schema() -> dict[str, bool]:
    return SchemaManager().clean_schema()


def reset_schema(include_sample_data: bool = False, num_cases: int = 100) -> dict[str, bool]:
    manager = SchemaManager()
    manager.drop_all_tables()
    return manager.create_tables(include_sample_data=include_sample_data, num_cases=num_cases)
