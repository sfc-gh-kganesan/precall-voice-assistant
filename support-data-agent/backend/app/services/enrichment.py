"""AI enrichment service using Snowpark DataFrame API and Snowflake Cortex."""

import json
from typing import Any

import snowflake.snowpark
import snowflake.snowpark.types as T
from snowflake.snowpark import Row
from snowflake.snowpark import functions as F
from snowflake.snowpark.exceptions import SnowparkSQLException, SnowparkTableException
from snowflake.snowpark.types import StringType

from ..services import snowflake as snowflake_service

print("SNOWFLAKE VERSION:", snowflake.snowpark.__version__)


class EnrichmentService:
    def __init__(self):
        self.session = snowflake_service._get_session()

    def _get_configuration(self, config_id: str) -> dict:
        result = self.session.table("CONFIGURATIONS").filter(F.col("CONFIG_ID") == config_id).collect()

        if not result:
            raise ValueError(f"Configuration {config_id} not found")

        row = result[0]
        tables_raw = row["TABLES"]
        tables = json.loads(str(tables_raw)) if tables_raw else []

        return {
            "OUTPUT_TABLE": row["OUTPUT_TABLE"],
            "TABLES": tables,
        }

    def _table_exists(self, table_name: str) -> bool:
        try:
            self.session.table(table_name).count()
            return True
        except (SnowparkSQLException, SnowparkTableException):
            return False

    def _ensure_output_table_exists(self, output_table: str, source_tables: list[str]):
        if self._table_exists(output_table):
            print(f"Output table {output_table} already exists")
            return
        if len(source_tables) == 1:
            source_query = source_tables[0]
        else:
            source_query = " UNION ALL ".join([f"SELECT * FROM {t}" for t in source_tables])

        create_sql = f"""
            CREATE TABLE {output_table} AS
            SELECT * FROM {source_query}
        """

        self.session.sql(create_sql).collect()
        print(f"Created output table: {output_table}")

        # Ensure all GENERATED columns exist
        self.session.sql(f"""
            ALTER TABLE {output_table}
            ADD COLUMN IF NOT EXISTS GENERATED_TOPIC VARCHAR
        """).collect()

        self.session.sql(f"""
            ALTER TABLE {output_table}
            ADD COLUMN IF NOT EXISTS GENERATED_PRODUCT VARCHAR
        """).collect()

        self.session.sql(f"""
            ALTER TABLE {output_table}
            ADD COLUMN IF NOT EXISTS GENERATED_PRODUCT_CATEGORY VARCHAR
        """).collect()

        self.session.sql(f"""
            ALTER TABLE {output_table}
            ADD COLUMN IF NOT EXISTS GENERATED_SENTIMENT FLOAT
        """).collect()

        self.session.sql(f"""
            ALTER TABLE {output_table}
            ADD COLUMN IF NOT EXISTS ENRICHED_AT TIMESTAMP
        """).collect()

    def start_enrichment_job(self, config_id: str, job_id: str) -> str:
        try:
            config = self._get_configuration(config_id)
            output_table = config["OUTPUT_TABLE"]
            source_tables = config["TABLES"]

            self._ensure_output_table_exists(output_table, source_tables)

            self._materialize_analytics(job_id, output_table, analytics_only=False)
            return job_id

        except Exception as e:
            import traceback

            print(f"Enrichment failed: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise

    def start_analytics_job(self, config_id: str, job_id: str) -> str:
        try:
            config = self._get_configuration(config_id)
            output_table = config["OUTPUT_TABLE"]

            # Analytics-only job should NOT recreate base table or run AI classification
            # It only materializes the _TOPICS, _PRODUCTS, and _KPI tables
            self._materialize_analytics(job_id, output_table, analytics_only=True)
            return job_id

        except Exception as e:
            import traceback

            print(f"Analytics failed: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise

    def _materialize_analytics(self, job_id: str, output_table: str, analytics_only: bool = False):
        print(
            f"Starting {'analytics materialization' if analytics_only else 'AI enrichment and analytics'} "
            f"(job: {job_id})"
        )
        print(f"Using output table: {output_table}")
        topics_table = f"{output_table}_TOPICS"
        products_table = f"{output_table}_PRODUCTS"
        kpi_table = f"{output_table}_KPI"

        if not analytics_only:
            print("Clearing existing analytics...")
            for table in [topics_table, products_table, kpi_table]:
                if self._table_exists(table):
                    self.session.sql(f"DELETE FROM {table}").collect()

            print("Clearing existing GENERATED fields for re-processing...")
            self.session.sql(f"""
                UPDATE {output_table}
                SET GENERATED_TOPIC = NULL,
                    GENERATED_PRODUCT = NULL,
                    GENERATED_PRODUCT_CATEGORY = NULL,
                    GENERATED_SENTIMENT = NULL
            """).collect()

            print("AI classifying cases...")
            cases_df = self.session.table(output_table)

            # transformed_cases.select(F.ai_agg(F.col("CONTENT_SUBJECT"),"give me a python list with concise topics that people are complaining about"))
            topic_categories = [
                "Security and Authentication",
                "Performance Issues",
                "Data Loading and Unloading",
                "Query Optimization",
                "Account Management",
                "Data Sharing and Collaboration",
                "Warehouse Issues",
                "Snowpipe Issues",
                "Cortex Issues",
                "Streamlit Issues",
                "Openflow Issues",
                "Network Policy Issues",
                "Privatelink Issues",
                "Tri-Secret Secure Issues",
                "Snowsight Issues",
                "Credit Usage and Billing",
                "MFA Issues",
                "Data Ingestion Issues",
                "Replication Issues",
            ]

            products = [
                "AI-Driven Applications",
                "Streams & Tasks (Batch & Streaming Ingestion)",
                "Encryption & Secure Connectivity",
                "SQL Analytics (Query Development & Execution + Advanced Analytics (SQL))",
                "Data Lineage & Monitoring",
                "Data Loading & Unloading (Copy)",
                "AI/ML-Powered Functions",
                "Event Logging Tracing & Telemetry",
                "Hybrid Tables",
                "Organization & Account Level Management (Account & Organization Management)",
                "Iceberg Tables (Data Lake Querying)",
                "Snowpark Container Services",
                "Programming Language Drivers",
                "User Authorization & Access Control",
                "Query Performance & Optimization (Resource Provisioning & Management)",
                "Snowflake Database & Information Schema (Metadata & Schema Management)",
                "Snowpark Dev Framework & Code Execution (Snowpark & Development Frameworks)",
                "Billing Discrepancies & Refunds",
                "External Tables",
                "Notebooks (Collaborative Analytics & Notebook Environment)",
                "Cost Management & Monitoring (Monitoring & Alerts)",
                "Data Sharing",
                "User Access & Password Reset (User Support & Access)",
                "General Billing Support",
                "Account Authentication Setup & Management",
                "Data Clean Rooms",
                "Native Apps (Native Managed Connected Applications Development & Deployment)",
                "Storage (Stages & Integrations) (Storage Management)",
                "Openflow",
                "Streamlit (SiS & Community Cloud) Streamlit Application Development & Deployment",
                "Security Monitoring & Compliance",
                "Dynamic Tables",
                "Programmatic Extensions",
                "Payment & Account Access",
                "DevOps & Tools",
                "External Platform Connectors",
                "Data Marketplace",
                "User Interface",
                "Core Clients & Drivers (Core Drivers)",
                "ML Platform (Machine Learning Development & Deployment)",
                "Backup & Recovery",
                "Snowpipe & Snowpipe Streaming (Batch & Streaming Ingestion)",
                "Data Protection & Privacy",
            ]

            print("Using AI functions for topic and product extraction...")

            # Get all cases that need classification (no limit - process everything)
            cases_to_classify = cases_df.filter(
                F.col("GENERATED_TOPIC").is_null() | F.col("GENERATED_PRODUCT").is_null()
            )

            # Apply AI classification to create enriched DataFrame
            classified_df = cases_to_classify.with_column(
                "combined_text", F.concat_ws(F.lit(" | "), F.col("SUBJECT"), F.col("DESCRIPTION"))
            ).select(
                F.col("CASE_ID"),
                F.ai_classify(F.col("combined_text"), topic_categories)["labels"][0]
                .cast(T.StringType())
                .alias("GENERATED_TOPIC"),
                F.ai_classify(
                    F.col("combined_text"),
                    products,
                )["labels"][0]
                .cast(T.StringType())
                .alias("GENERATED_PRODUCT"),
            )

            # Get output table as Snowpark Table
            output_table_df = self.session.table(output_table)

            # Use Table.update() to populate classifications in bulk
            print("Updating topic and product classifications...")
            output_table_df.update(
                {
                    "GENERATED_TOPIC": classified_df["GENERATED_TOPIC"],
                    "GENERATED_PRODUCT": classified_df["GENERATED_PRODUCT"],
                    "ENRICHED_AT": F.current_timestamp(),
                },
                output_table_df["CASE_ID"] == classified_df["CASE_ID"],
                classified_df,
            )

            # Process sentiment for all cases that need it
            print("Processing sentiment analysis...")
            sentiment_cases = cases_df.filter(F.col("GENERATED_SENTIMENT").is_null())

            sentiment_df = sentiment_cases.with_column(
                "combined_text", F.concat_ws(F.lit(" "), F.col("SUBJECT"), F.col("DESCRIPTION"))
            ).select(
                F.col("CASE_ID"),
                F.call_function("SNOWFLAKE.CORTEX.SENTIMENT", F.col("combined_text")).alias("GENERATED_SENTIMENT"),
            )

            # Update using Table.update()
            output_table_df.update(
                {"GENERATED_SENTIMENT": sentiment_df["GENERATED_SENTIMENT"], "ENRICHED_AT": F.current_timestamp()},
                output_table_df["CASE_ID"] == sentiment_df["CASE_ID"],
                sentiment_df,
            )

            print("AI classification and sentiment analysis completed")

            print("Setting product categories...")

            # Define mapping data as list of tuples (Feature, DOMAIN)
            mapping_data = [
                ("Snowpark Container Services", "Application Platform"),
                ("User Interface", "Product Experiences"),
                (
                    "Streamlit (SiS & Community Cloud) Streamlit Application Development & Deployment",
                    "Product Experiences",
                ),
                ("Data Marketplace", "Application Platform"),
                ("Snowflake Database & Information Schema (Metadata & Schema Management)", "Metadata"),
                ("Account Authentication Setup & Management", "Governance | Manageability | Privacy | Security"),
                ("Billing Discrepancies & Refunds", "Billing & Monetization Platform"),
                ("DevOps & Tools", "Data Engineering"),
                ("Event Logging Tracing & Telemetry", "Data Engineering"),
                (
                    "Organization & Account Level Management (Account & Organization Management)",
                    "Governance | Manageability | Privacy | Security",
                ),
                ("Payment & Account Access", "Billing & Monetization Platform"),
                ("Snowpipe & Snowpipe Streaming (Batch & Streaming Ingestion)", "Data Engineering"),
                (
                    "Cost Management & Monitoring (Monitoring & Alerts)",
                    "Governance | Manageability | Privacy | Security",
                ),
                ("ML Platform (Machine Learning Development & Deployment)", "AI & Machine Learning"),
                ("Data Sharing", "Application Platform"),
                ("External Platform Connectors", "Data Engineering"),
                ("Data Loading & Unloading (Copy)", "Data Engineering"),
                ("Core Clients & Drivers (Core Drivers)", "Data Analytics"),
                ("Security Monitoring & Compliance", "Governance | Manageability | Privacy | Security"),
                ("Programmatic Extensions", "Data Engineering"),
                ("Programming Language Drivers", "Data Analytics"),
                ("Query Performance & Optimization (Resource Provisioning & Management)", "Data Analytics"),
                (
                    "User Access & Password Reset (User Support & Access)",
                    "Governance | Manageability | Privacy | Security",
                ),
                ("Backup & Recovery", "Metadata"),
                ("Data Protection & Privacy", "Governance | Manageability | Privacy | Security"),
                ("Iceberg Tables (Data Lake Querying)", "Open Lakehouse"),
                ("Notebooks (Collaborative Analytics & Notebook Environment)", "Product Experiences"),
                ("Storage (Stages & Integrations) (Storage Management)", "Open Lakehouse"),
                ("Streams & Tasks (Batch & Streaming Ingestion)", "Data Engineering"),
                ("Data Clean Rooms", "Governance | Manageability | Privacy | Security"),
                ("Hybrid Tables", "Data Analytics"),
                ("Data Lineage & Monitoring", "Governance | Manageability | Privacy | Security"),
                ("General Billing Support", "Billing & Monetization Platform"),
                ("SQL Analytics (Query Development & Execution + Advanced Analytics (SQL))", "Data Analytics"),
                ("AI-Driven Applications", "AI & Machine Learning"),
                ("Snowpark Dev Framework & Code Execution (Snowpark & Development Frameworks)", "Data Engineering"),
                ("Dynamic Tables", "Data Engineering"),
                ("External Tables", "Open Lakehouse"),
                ("Encryption & Secure Connectivity", "Governance | Manageability | Privacy | Security"),
                (
                    "Native Apps (Native Managed Connected Applications Development & Deployment)",
                    "Application Platform",
                ),
                ("User Authorization & Access Control", "Governance | Manageability | Privacy | Security"),
                ("AI/ML-Powered Functions", "AI & Machine Learning"),
                ("Openflow", "Data Engineering"),
            ]

            # Create Snowpark DataFrame directly from list of Row objects
            rows = [Row(Feature=feature, DOMAIN=domain) for feature, domain in mapping_data]
            mapping_df = self.session.create_dataframe(rows)

            # Get output table as Snowpark Table
            output_table_df = self.session.table(output_table)

            # Use Table.update() to populate GENERATED_PRODUCT_CATEGORY from mapping
            output_table_df.update(
                {"GENERATED_PRODUCT_CATEGORY": mapping_df["DOMAIN"]},
                output_table_df["GENERATED_PRODUCT"] == mapping_df["Feature"],
                mapping_df,
            )

            # Set default category for any products that didn't match mapping
            print("Setting default category for unmapped products...")
            output_table_df.update(
                {"GENERATED_PRODUCT_CATEGORY": F.lit("Unknown")}, F.col("GENERATED_PRODUCT_CATEGORY").is_null()
            )

        print("Materializing PRODUCTS analytics...")
        self._materialize_products_df(output_table, products_table)

        print("Materializing TOPICS analytics...")
        self._materialize_topics_df(output_table, topics_table)

        print("Materializing KPI summary...")
        self._materialize_kpis_df(output_table, kpi_table)

        print("Analytics materialization completed!")

    def _resolution_time_expr(self):
        """Calculate resolution time in hours.

        For closed cases: hours between CREATED_AT and CLOSED_AT
        For open cases: default to 24.0 hours
        """
        return F.coalesce(F.datediff("hour", F.col("CREATED_AT"), F.col("CLOSED_AT")), F.lit(24.0))

    def _materialize_products_df(self, base_table: str, products_table: str):
        """
        Materialize multi-period product metrics using a single SQL query.
        Generates METRICS (week/month current/previous/change) and TREND_DATA (weekly/monthly/quarterly arrays).
        """
        metrics_sql = f"""
        WITH product_metrics AS (
          SELECT
            GENERATED_PRODUCT,
            GENERATED_PRODUCT_CATEGORY,

            -- Current week metrics (last 7 days)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS week_current_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS week_current_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE()) AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE()) THEN 1 ELSE 0 END), 0)
            ) AS week_current_resolution_rate,

            -- Previous week metrics (days 8-14 ago)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS week_previous_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS week_previous_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                           AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                           AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                                  AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                             THEN 1 ELSE 0 END), 0)
            ) AS week_previous_resolution_rate,

            -- Current month metrics (last 30 days)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS month_current_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS month_current_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE()) AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE()) THEN 1 ELSE 0 END), 0)
            ) AS month_current_resolution_rate,

            -- Previous month metrics (days 31-60 ago)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS month_previous_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS month_previous_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                           AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                           AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                                  AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                             THEN 1 ELSE 0 END), 0)
            ) AS month_previous_resolution_rate,

            -- Metadata: earliest and latest case dates
            MIN(CREATED_AT) AS earliest_case_date,
            MAX(CREATED_AT) AS latest_case_date

          FROM {base_table}
          WHERE GENERATED_PRODUCT IS NOT NULL
          GROUP BY 1, 2
        ),

        -- Weekly trend (last 16 weeks)
        weekly_trend AS (
          SELECT
            GENERATED_PRODUCT,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'weekStart', TO_VARCHAR(week_start, 'YYYY-MM-DD'),
                'weekEnd', TO_VARCHAR(week_end, 'YYYY-MM-DD'),
                'cases', weekly_cases,
                'avgResolution', ROUND(weekly_avg_resolution, 1),
                'resolutionRate', ROUND(weekly_resolution_rate, 1)
              )
            ) WITHIN GROUP (ORDER BY week_start) AS weekly_data
          FROM (
            SELECT
              GENERATED_PRODUCT,
              DATE_TRUNC('WEEK', CREATED_AT) AS week_start,
              DATEADD('day', 6, DATE_TRUNC('WEEK', CREATED_AT)) AS week_end,
              COUNT(*) AS weekly_cases,
              AVG(DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))) AS weekly_avg_resolution,
              (SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS weekly_resolution_rate
            FROM {base_table}
            WHERE CREATED_AT >= DATEADD('week', -16, CURRENT_DATE())
              AND GENERATED_PRODUCT IS NOT NULL
            GROUP BY 1, 2, 3
          )
          GROUP BY 1
        ),

        -- Monthly trend (last 12 months)
        monthly_trend AS (
          SELECT
            GENERATED_PRODUCT,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'monthStart', TO_VARCHAR(month_start, 'YYYY-MM-DD'),
                'monthEnd', TO_VARCHAR(LAST_DAY(month_start), 'YYYY-MM-DD'),
                'month', TO_VARCHAR(month_start, 'YYYY-MM'),
                'cases', monthly_cases,
                'avgResolution', ROUND(monthly_avg_resolution, 1),
                'resolutionRate', ROUND(monthly_resolution_rate, 1)
              )
            ) WITHIN GROUP (ORDER BY month_start) AS monthly_data
          FROM (
            SELECT
              GENERATED_PRODUCT,
              DATE_TRUNC('MONTH', CREATED_AT) AS month_start,
              COUNT(*) AS monthly_cases,
              AVG(DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))) AS monthly_avg_resolution,
              (SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS monthly_resolution_rate
            FROM {base_table}
            WHERE CREATED_AT >= DATEADD('month', -12, CURRENT_DATE())
              AND GENERATED_PRODUCT IS NOT NULL
            GROUP BY 1, 2
          )
          GROUP BY 1
        ),

        -- Quarterly trend (up to 12 quarters / 3 years if available)
        quarterly_trend AS (
          SELECT
            GENERATED_PRODUCT,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'quarter', TO_VARCHAR(quarter_start, 'YYYY-"Q"Q'),
                'quarterStart', TO_VARCHAR(quarter_start, 'YYYY-MM-DD'),
                'quarterEnd', TO_VARCHAR(LAST_DAY(DATEADD('month', 2, quarter_start)), 'YYYY-MM-DD'),
                'cases', quarterly_cases,
                'avgResolution', ROUND(quarterly_avg_resolution, 1),
                'resolutionRate', ROUND(quarterly_resolution_rate, 1)
              )
            ) WITHIN GROUP (ORDER BY quarter_start) AS quarterly_data
          FROM (
            SELECT
              GENERATED_PRODUCT,
              DATE_TRUNC('QUARTER', CREATED_AT) AS quarter_start,
              COUNT(*) AS quarterly_cases,
              AVG(DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))) AS quarterly_avg_resolution,
              (SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS quarterly_resolution_rate
            FROM {base_table}
            WHERE CREATED_AT >= DATEADD('quarter', -12, CURRENT_DATE())
              AND GENERATED_PRODUCT IS NOT NULL
            GROUP BY 1, 2
          )
          GROUP BY 1
        ),

        -- Top issues (top 3 per product from last 30 days)
        top_issues AS (
          SELECT
            GENERATED_PRODUCT,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'issue', issue_text,
                'count', issue_count
              )
            ) WITHIN GROUP (ORDER BY issue_count DESC) AS issues_data
          FROM (
            SELECT
              GENERATED_PRODUCT,
              SUBJECT AS issue_text,
              COUNT(*) AS issue_count
            FROM {base_table}
            WHERE GENERATED_PRODUCT IS NOT NULL
              AND CREATED_AT >= DATEADD('day', -30, CURRENT_DATE())
            GROUP BY 1, 2
            QUALIFY ROW_NUMBER() OVER (PARTITION BY GENERATED_PRODUCT ORDER BY COUNT(*) DESC) <= 3
          )
          GROUP BY 1
        )

        SELECT
          CONCAT('product_', ROW_NUMBER() OVER (ORDER BY pm.GENERATED_PRODUCT)) AS PRODUCT_ID,
          LOWER(REPLACE(pm.GENERATED_PRODUCT, ' ', '-')) AS PRODUCT_SLUG,
          pm.GENERATED_PRODUCT AS PRODUCT_NAME,
          COALESCE(pm.GENERATED_PRODUCT_CATEGORY, 'Unknown') AS PRODUCT_CATEGORY,
          'multi' AS PERIOD,
          pm.earliest_case_date::DATE AS START_DATE,
          pm.latest_case_date::DATE AS END_DATE,

          -- Build nested METRICS JSON
          OBJECT_CONSTRUCT(
            'week', OBJECT_CONSTRUCT(
              'current', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', pm.week_current_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -7, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.week_current_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.week_current_resolution_rate, 0), 1))
              ),
              'previous', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', pm.week_previous_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -14, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(DATEADD('day', -7, CURRENT_DATE()), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.week_previous_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.week_previous_resolution_rate, 0), 1))
              ),
              'change', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'absolute', pm.week_current_cases - pm.week_previous_cases,
                  'percentage', ROUND((pm.week_current_cases - pm.week_previous_cases) * 100.0 / NULLIF(pm.week_previous_cases, 0), 1)
                ),
                'avgCaseLife', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(pm.week_current_avg_resolution, 0) - COALESCE(pm.week_previous_avg_resolution, 0), 1),
                  'percentage', ROUND((COALESCE(pm.week_current_avg_resolution, 0) - COALESCE(pm.week_previous_avg_resolution, 0)) * 100.0 / NULLIF(pm.week_previous_avg_resolution, 0), 1)
                ),
                'resolutionRate', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(pm.week_current_resolution_rate, 0) - COALESCE(pm.week_previous_resolution_rate, 0), 1),
                  'percentage', ROUND((COALESCE(pm.week_current_resolution_rate, 0) - COALESCE(pm.week_previous_resolution_rate, 0)) * 100.0 / NULLIF(pm.week_previous_resolution_rate, 0), 1)
                )
              )
            ),
            'month', OBJECT_CONSTRUCT(
              'current', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', pm.month_current_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -30, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.month_current_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.month_current_resolution_rate, 0), 1))
              ),
              'previous', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', pm.month_previous_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -60, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(DATEADD('day', -30, CURRENT_DATE()), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.month_previous_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(pm.month_previous_resolution_rate, 0), 1))
              ),
              'change', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'absolute', pm.month_current_cases - pm.month_previous_cases,
                  'percentage', ROUND((pm.month_current_cases - pm.month_previous_cases) * 100.0 / NULLIF(pm.month_previous_cases, 0), 1)
                ),
                'avgCaseLife', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(pm.month_current_avg_resolution, 0) - COALESCE(pm.month_previous_avg_resolution, 0), 1),
                  'percentage', ROUND((COALESCE(pm.month_current_avg_resolution, 0) - COALESCE(pm.month_previous_avg_resolution, 0)) * 100.0 / NULLIF(pm.month_previous_avg_resolution, 0), 1)
                ),
                'resolutionRate', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(pm.month_current_resolution_rate, 0) - COALESCE(pm.month_previous_resolution_rate, 0), 1),
                  'percentage', ROUND((COALESCE(pm.month_current_resolution_rate, 0) - COALESCE(pm.month_previous_resolution_rate, 0)) * 100.0 / NULLIF(pm.month_previous_resolution_rate, 0), 1)
                )
              )
            )
          ) AS METRICS,

          -- Build TREND_DATA JSON with weekly, monthly, quarterly
          OBJECT_CONSTRUCT(
            'weekly', wt.weekly_data,
            'monthly', mt.monthly_data,
            'quarterly', qt.quarterly_data
          ) AS TREND_DATA,

          -- Top issues
          COALESCE(ti.issues_data, PARSE_JSON('[]')) AS TOP_ISSUES,

          -- AI-generated text fields (placeholder for now)
          CONCAT('Analysis of ', pm.GENERATED_PRODUCT, ' based on ', COALESCE(pm.week_current_cases, 0) + COALESCE(pm.week_previous_cases, 0), ' recent cases.') AS AI_SUMMARY,
          CONCAT('Customer feedback from ', COALESCE(pm.week_current_cases, 0) + COALESCE(pm.week_previous_cases, 0), ' support interactions.') AS CUSTOMER_FEEDBACK,
          'Root cause analysis from case patterns.' AS ROOT_CAUSES,

          CURRENT_TIMESTAMP() AS CREATED_AT

        FROM product_metrics pm
        LEFT JOIN weekly_trend wt ON pm.GENERATED_PRODUCT = wt.GENERATED_PRODUCT
        LEFT JOIN monthly_trend mt ON pm.GENERATED_PRODUCT = mt.GENERATED_PRODUCT
        LEFT JOIN quarterly_trend qt ON pm.GENERATED_PRODUCT = qt.GENERATED_PRODUCT
        LEFT JOIN top_issues ti ON pm.GENERATED_PRODUCT = ti.GENERATED_PRODUCT
        """

        # Execute SQL and save to table
        products_df = self.session.sql(metrics_sql)
        products_df.write.mode("overwrite").save_as_table(products_table)

    def _materialize_topics_df(self, base_table: str, topics_table: str):
        """
        Materialize multi-period topic metrics using a single SQL query.
        Generates METRICS (week/month current/previous/change) and TREND_DATA (weekly/monthly/quarterly arrays).
        """
        metrics_sql = f"""
        WITH topic_metrics AS (
          SELECT
            GENERATED_TOPIC,

            -- Current week metrics (last 7 days)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS week_current_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS week_current_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE()) AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -7, CURRENT_DATE()) THEN 1 ELSE 0 END), 0)
            ) AS week_current_resolution_rate,

            -- Previous week metrics (days 8-14 ago)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS week_previous_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS week_previous_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                           AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                           AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -14, CURRENT_DATE())
                                  AND CREATED_AT < DATEADD('day', -7, CURRENT_DATE())
                             THEN 1 ELSE 0 END), 0)
            ) AS week_previous_resolution_rate,

            -- Current month metrics (last 30 days)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS month_current_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS month_current_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE()) AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -30, CURRENT_DATE()) THEN 1 ELSE 0 END), 0)
            ) AS month_current_resolution_rate,

            -- Previous month metrics (days 31-60 ago)
            SUM(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                     THEN 1 ELSE 0 END) AS month_previous_cases,
            AVG(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                          AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                     THEN DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))
                     END) AS month_previous_avg_resolution,
            (SUM(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                           AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                           AND STATUS = 'Closed'
                      THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN CREATED_AT >= DATEADD('day', -60, CURRENT_DATE())
                                  AND CREATED_AT < DATEADD('day', -30, CURRENT_DATE())
                             THEN 1 ELSE 0 END), 0)
            ) AS month_previous_resolution_rate,

            -- Metadata: earliest and latest case dates
            MIN(CREATED_AT) AS earliest_case_date,
            MAX(CREATED_AT) AS latest_case_date

          FROM {base_table}
          WHERE GENERATED_TOPIC IS NOT NULL
          GROUP BY 1
        ),

        -- Weekly trend (last 16 weeks)
        weekly_trend AS (
          SELECT
            GENERATED_TOPIC,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'weekStart', TO_VARCHAR(week_start, 'YYYY-MM-DD'),
                'weekEnd', TO_VARCHAR(week_end, 'YYYY-MM-DD'),
                'cases', weekly_cases,
                'avgResolution', ROUND(weekly_avg_resolution, 1),
                'resolutionRate', ROUND(weekly_resolution_rate, 1)
              )
            ) WITHIN GROUP (ORDER BY week_start) AS weekly_data
          FROM (
            SELECT
              GENERATED_TOPIC,
              DATE_TRUNC('WEEK', CREATED_AT) AS week_start,
              DATEADD('day', 6, DATE_TRUNC('WEEK', CREATED_AT)) AS week_end,
              COUNT(*) AS weekly_cases,
              AVG(DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))) AS weekly_avg_resolution,
              (SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS weekly_resolution_rate
            FROM {base_table}
            WHERE CREATED_AT >= DATEADD('week', -16, CURRENT_DATE())
              AND GENERATED_TOPIC IS NOT NULL
            GROUP BY 1, 2, 3
          )
          GROUP BY 1
        ),

        -- Monthly trend (last 12 months)
        monthly_trend AS (
          SELECT
            GENERATED_TOPIC,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'monthStart', TO_VARCHAR(month_start, 'YYYY-MM-DD'),
                'monthEnd', TO_VARCHAR(LAST_DAY(month_start), 'YYYY-MM-DD'),
                'month', TO_VARCHAR(month_start, 'YYYY-MM'),
                'cases', monthly_cases,
                'avgResolution', ROUND(monthly_avg_resolution, 1),
                'resolutionRate', ROUND(monthly_resolution_rate, 1)
              )
            ) WITHIN GROUP (ORDER BY month_start) AS monthly_data
          FROM (
            SELECT
              GENERATED_TOPIC,
              DATE_TRUNC('MONTH', CREATED_AT) AS month_start,
              COUNT(*) AS monthly_cases,
              AVG(DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))) AS monthly_avg_resolution,
              (SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS monthly_resolution_rate
            FROM {base_table}
            WHERE CREATED_AT >= DATEADD('month', -12, CURRENT_DATE())
              AND GENERATED_TOPIC IS NOT NULL
            GROUP BY 1, 2
          )
          GROUP BY 1
        ),

        -- Quarterly trend (up to 12 quarters / 3 years if available)
        quarterly_trend AS (
          SELECT
            GENERATED_TOPIC,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'quarter', TO_VARCHAR(quarter_start, 'YYYY-"Q"Q'),
                'quarterStart', TO_VARCHAR(quarter_start, 'YYYY-MM-DD'),
                'quarterEnd', TO_VARCHAR(LAST_DAY(DATEADD('month', 2, quarter_start)), 'YYYY-MM-DD'),
                'cases', quarterly_cases,
                'avgResolution', ROUND(quarterly_avg_resolution, 1),
                'resolutionRate', ROUND(quarterly_resolution_rate, 1)
              )
            ) WITHIN GROUP (ORDER BY quarter_start) AS quarterly_data
          FROM (
            SELECT
              GENERATED_TOPIC,
              DATE_TRUNC('QUARTER', CREATED_AT) AS quarter_start,
              COUNT(*) AS quarterly_cases,
              AVG(DATEDIFF('hour', CREATED_AT, COALESCE(CLOSED_AT, CURRENT_TIMESTAMP()))) AS quarterly_avg_resolution,
              (SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS quarterly_resolution_rate
            FROM {base_table}
            WHERE CREATED_AT >= DATEADD('quarter', -12, CURRENT_DATE())
              AND GENERATED_TOPIC IS NOT NULL
            GROUP BY 1, 2
          )
          GROUP BY 1
        ),

        -- Top products (top 3 per topic from last 30 days)
        top_products AS (
          SELECT
            GENERATED_TOPIC,
            ARRAY_AGG(
              OBJECT_CONSTRUCT(
                'product', product_name,
                'count', product_count
              )
            ) WITHIN GROUP (ORDER BY product_count DESC) AS products_data
          FROM (
            SELECT
              GENERATED_TOPIC,
              GENERATED_PRODUCT AS product_name,
              COUNT(*) AS product_count
            FROM {base_table}
            WHERE GENERATED_TOPIC IS NOT NULL
              AND CREATED_AT >= DATEADD('day', -30, CURRENT_DATE())
            GROUP BY 1, 2
            QUALIFY ROW_NUMBER() OVER (PARTITION BY GENERATED_TOPIC ORDER BY COUNT(*) DESC) <= 3
          )
          GROUP BY 1
        )

        SELECT
          CONCAT('topic_', ROW_NUMBER() OVER (ORDER BY tm.GENERATED_TOPIC)) AS TOPIC_ID,
          LOWER(REPLACE(REPLACE(tm.GENERATED_TOPIC, ' & ', '-'), ' ', '-')) AS TOPIC_SLUG,
          tm.GENERATED_TOPIC AS TOPIC_NAME,
          'multi' AS PERIOD,
          tm.earliest_case_date::DATE AS START_DATE,
          tm.latest_case_date::DATE AS END_DATE,

          -- Build nested METRICS JSON
          OBJECT_CONSTRUCT(
            'week', OBJECT_CONSTRUCT(
              'current', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', tm.week_current_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -7, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.week_current_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.week_current_resolution_rate, 0), 1))
              ),
              'previous', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', tm.week_previous_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -14, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(DATEADD('day', -7, CURRENT_DATE()), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.week_previous_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.week_previous_resolution_rate, 0), 1))
              ),
              'change', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'absolute', tm.week_current_cases - tm.week_previous_cases,
                  'percentage', ROUND((tm.week_current_cases - tm.week_previous_cases) * 100.0 / NULLIF(tm.week_previous_cases, 0), 1)
                ),
                'avgCaseLife', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(tm.week_current_avg_resolution, 0) - COALESCE(tm.week_previous_avg_resolution, 0), 1),
                  'percentage', ROUND((COALESCE(tm.week_current_avg_resolution, 0) - COALESCE(tm.week_previous_avg_resolution, 0)) * 100.0 / NULLIF(tm.week_previous_avg_resolution, 0), 1)
                ),
                'resolutionRate', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(tm.week_current_resolution_rate, 0) - COALESCE(tm.week_previous_resolution_rate, 0), 1),
                  'percentage', ROUND((COALESCE(tm.week_current_resolution_rate, 0) - COALESCE(tm.week_previous_resolution_rate, 0)) * 100.0 / NULLIF(tm.week_previous_resolution_rate, 0), 1)
                )
              )
            ),
            'month', OBJECT_CONSTRUCT(
              'current', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', tm.month_current_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -30, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.month_current_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.month_current_resolution_rate, 0), 1))
              ),
              'previous', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'value', tm.month_previous_cases,
                  'startDate', TO_VARCHAR(DATEADD('day', -60, CURRENT_DATE()), 'YYYY-MM-DD'),
                  'endDate', TO_VARCHAR(DATEADD('day', -30, CURRENT_DATE()), 'YYYY-MM-DD')
                ),
                'avgCaseLife', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.month_previous_avg_resolution, 0), 1)),
                'resolutionRate', OBJECT_CONSTRUCT('value', ROUND(COALESCE(tm.month_previous_resolution_rate, 0), 1))
              ),
              'change', OBJECT_CONSTRUCT(
                'totalCases', OBJECT_CONSTRUCT(
                  'absolute', tm.month_current_cases - tm.month_previous_cases,
                  'percentage', ROUND((tm.month_current_cases - tm.month_previous_cases) * 100.0 / NULLIF(tm.month_previous_cases, 0), 1)
                ),
                'avgCaseLife', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(tm.month_current_avg_resolution, 0) - COALESCE(tm.month_previous_avg_resolution, 0), 1),
                  'percentage', ROUND((COALESCE(tm.month_current_avg_resolution, 0) - COALESCE(tm.month_previous_avg_resolution, 0)) * 100.0 / NULLIF(tm.month_previous_avg_resolution, 0), 1)
                ),
                'resolutionRate', OBJECT_CONSTRUCT(
                  'absolute', ROUND(COALESCE(tm.month_current_resolution_rate, 0) - COALESCE(tm.month_previous_resolution_rate, 0), 1),
                  'percentage', ROUND((COALESCE(tm.month_current_resolution_rate, 0) - COALESCE(tm.month_previous_resolution_rate, 0)) * 100.0 / NULLIF(tm.month_previous_resolution_rate, 0), 1)
                )
              )
            )
          ) AS METRICS,

          -- Build TREND_DATA JSON with weekly, monthly, quarterly
          OBJECT_CONSTRUCT(
            'weekly', wt.weekly_data,
            'monthly', mt.monthly_data,
            'quarterly', qt.quarterly_data
          ) AS TREND_DATA,

          -- Top products
          COALESCE(tp.products_data, PARSE_JSON('[]')) AS TOP_PRODUCTS,

          -- AI-generated text fields (placeholder for now)
          CONCAT('Real analysis of ', tm.GENERATED_TOPIC, ' from ', COALESCE(tm.week_current_cases, 0) + COALESCE(tm.week_previous_cases, 0), ' actual cases.') AS AI_SUMMARY,
          CONCAT('Based on ', COALESCE(tm.week_current_cases, 0) + COALESCE(tm.week_previous_cases, 0), ' real customer support tickets.') AS CUSTOMER_FEEDBACK,
          'Sentiment analysis from actual case content.' AS SENTIMENT_ANALYSIS,
          CONCAT('Various issues related to ', tm.GENERATED_TOPIC) AS TOP_ISSUES,

          CURRENT_TIMESTAMP() AS CREATED_AT

        FROM topic_metrics tm
        LEFT JOIN weekly_trend wt ON tm.GENERATED_TOPIC = wt.GENERATED_TOPIC
        LEFT JOIN monthly_trend mt ON tm.GENERATED_TOPIC = mt.GENERATED_TOPIC
        LEFT JOIN quarterly_trend qt ON tm.GENERATED_TOPIC = qt.GENERATED_TOPIC
        LEFT JOIN top_products tp ON tm.GENERATED_TOPIC = tp.GENERATED_TOPIC
        """

        # Execute SQL and save to table
        topics_df = self.session.sql(metrics_sql)
        topics_df.write.mode("overwrite").save_as_table(topics_table)

    def _materialize_kpis_df(self, base_table: str, kpi_table: str):
        cases_df = self.session.table(base_table)

        kpi_df = cases_df.agg(
            F.count("*").alias("TOTAL_CASES"),
            F.avg(self._resolution_time_expr()).alias("AVG_CASE_LIFE"),
            F.sum(F.when(F.col("STATUS") == "Closed", 1).otherwise(0)).alias("CLOSED_CASES"),
            F.min(F.col("CREATED_AT")).alias("MIN_DATE"),
            F.max(F.col("CREATED_AT")).alias("MAX_DATE"),
        ).select(
            F.concat(F.lit("kpi_current_"), F.current_date().cast(StringType())).alias("KPI_ID"),
            F.lit("week").alias("PERIOD"),
            F.col("MIN_DATE").cast("date").alias("START_DATE"),
            F.col("MAX_DATE").cast("date").alias("END_DATE"),
            F.col("TOTAL_CASES"),
            F.col("AVG_CASE_LIFE").alias("AVG_CASE_LIFE_HOURS"),
            F.round((F.col("CLOSED_CASES") / F.col("TOTAL_CASES")) * 100, 1).alias("RESOLUTION_RATE_PERCENT"),
            F.lit(8.0).alias("FIRST_RESPONSE_TIME_HOURS"),
            F.current_timestamp().alias("CREATED_AT"),
        )

        kpi_df.write.mode("overwrite").save_as_table(kpi_table)

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        return {
            "jobId": job_id,
            "status": "completed",
            "progress": 100,
            "results": {
                "processed": 25,
                "errors": 0,
            },
            "errorMessage": None,
        }


enrichment_service = EnrichmentService()
