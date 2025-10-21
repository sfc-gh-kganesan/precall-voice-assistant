"""
Configuration management service for querying and managing data source configurations.
"""

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from snowflake.snowpark import functions as F
from snowflake.snowpark.exceptions import SnowparkSQLException, SnowparkTableException

from . import snowflake as snowflake_service
from .enrichment import enrichment_service


def get_active_configuration() -> dict[str, str]:
    """
    Get the active configuration and return table names.

    Returns:
        Dictionary with keys: 'base', 'topics', 'products', 'kpi'
    """
    session = snowflake_service._get_session()

    try:
        result = session.sql("""
            SELECT OUTPUT_TABLE FROM CONFIGURATIONS
            WHERE STATUS = 'active'
            ORDER BY CREATED_AT DESC
            LIMIT 1
        """).collect()

        if result:
            output_table = result[0]["OUTPUT_TABLE"]
        else:
            output_table = "CASES"

        return {
            "base": output_table,
            "topics": f"{output_table}_TOPICS",
            "products": f"{output_table}_PRODUCTS",
            "kpi": f"{output_table}_KPI",
        }
    except SnowparkSQLException:
        return {
            "base": "CASES",
            "topics": "CASES_TOPICS",
            "products": "CASES_PRODUCTS",
            "kpi": "CASES_KPI",
        }


def list_configurations() -> list[dict[str, Any]]:
    """
    List all configurations with their current status.

    Returns:
        List of configuration summaries with status information
    """
    session = snowflake_service._get_session()

    # Get configurations using Snowpark DataFrame API
    configs_df = session.table("CONFIGURATIONS")

    # Select and order configurations
    results_df = configs_df.select(
        F.col("CONFIG_ID"),
        F.col("NAME"),
        F.col("DATABASE_NAME"),
        F.col("SCHEMA_NAME"),
        F.col("TABLES"),
        F.col("OUTPUT_TABLE"),
        F.col("STATUS"),
        F.col("CREATED_AT"),
        F.col("UPDATED_AT"),
    ).order_by(F.col("CREATED_AT").desc())

    results = results_df.collect()

    def _safe_table_count(table_name: str) -> int:
        try:
            return session.table(table_name).count()
        except (SnowparkSQLException, SnowparkTableException):
            return 0

    configurations = []
    for row in results:
        tables = []
        if row["TABLES"]:
            try:
                tables = json.loads(str(row["TABLES"])) if isinstance(row["TABLES"], str) else row["TABLES"]
            except (json.JSONDecodeError, TypeError):
                tables = []
        output_table = row["OUTPUT_TABLE"]
        cases_count = _safe_table_count(output_table)
        topics_count = _safe_table_count(f"{output_table}_TOPICS")
        products_count = _safe_table_count(f"{output_table}_PRODUCTS")
        kpi_count = _safe_table_count(f"{output_table}_KPI")
        status = {
            "baseTable": {
                "created": cases_count > 0,
                "rowCount": int(cases_count) if cases_count else 0,
            },
            "topicMetrics": {
                "created": topics_count > 0,
                "rowCount": int(topics_count) if topics_count else 0,
            },
            "productMetrics": {
                "created": products_count > 0,
                "rowCount": int(products_count) if products_count else 0,
            },
            "kpiSummary": {"created": kpi_count > 0},
        }

        configurations.append(
            {
                "configId": row["CONFIG_ID"],
                "name": row["NAME"],
                "database": row["DATABASE_NAME"],
                "schema": row["SCHEMA_NAME"],
                "tables": tables,
                "createdAt": row["CREATED_AT"].isoformat() if row["CREATED_AT"] else None,
                "status": status,
            }
        )

    return configurations


def get_configuration(config_id: str) -> dict[str, Any]:
    """
    Get detailed configuration information by ID.

    Args:
        config_id: Configuration ID

    Returns:
        Configuration detail with full config and status

    Raises:
        HTTPException: 404 if configuration not found
    """
    session = snowflake_service._get_session()

    # Get single configuration using Snowpark DataFrame API
    configs_df = session.table("CONFIGURATIONS")
    config_df = configs_df.filter(F.col("CONFIG_ID") == config_id)

    results = config_df.collect()

    if not results:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

    row = results[0]

    def _safe_table_count(table_name: str) -> int:
        try:
            return session.table(table_name).count()
        except (SnowparkSQLException, SnowparkTableException):
            return 0

    output_table = row["OUTPUT_TABLE"]
    cases_count = _safe_table_count(output_table)
    topics_count = _safe_table_count(f"{output_table}_TOPICS")
    products_count = _safe_table_count(f"{output_table}_PRODUCTS")
    kpi_count = _safe_table_count(f"{output_table}_KPI")

    tables = []
    if row["TABLES"]:
        try:
            tables = json.loads(str(row["TABLES"])) if isinstance(row["TABLES"], str) else row["TABLES"]
        except (json.JSONDecodeError, TypeError):
            tables = []

    mappings = []
    if row["MAPPINGS"]:
        try:
            mappings = json.loads(str(row["MAPPINGS"])) if isinstance(row["MAPPINGS"], str) else row["MAPPINGS"]
        except (json.JSONDecodeError, TypeError):
            mappings = []
    config = {
        "name": row["NAME"],
        "database": row["DATABASE_NAME"],
        "schema": row["SCHEMA_NAME"],
        "tables": tables,
        "outputTable": row["OUTPUT_TABLE"],
        "mappings": mappings,
        "createdAt": row["CREATED_AT"].isoformat() if row["CREATED_AT"] else None,
        "updatedAt": row["UPDATED_AT"].isoformat() if row["UPDATED_AT"] else None,
    }
    status = {
        "baseTable": {
            "created": cases_count > 0,
            "rowCount": int(cases_count) if cases_count else 0,
        },
        "topicMetrics": {
            "created": topics_count > 0,
            "rowCount": int(topics_count) if topics_count else 0,
        },
        "productMetrics": {
            "created": products_count > 0,
            "rowCount": int(products_count) if products_count else 0,
        },
        "kpiSummary": {"created": kpi_count > 0},
    }

    return {"config": config, "status": status}


def create_configuration(payload: dict[str, Any]) -> dict[str, str]:
    session = snowflake_service._get_session()

    config_id = f"config_{int(datetime.now().timestamp() * 1000)}"
    tables_json = json.dumps(payload["tables"])
    mappings_json = json.dumps(payload["mappings"])

    escaped_config_id = config_id.replace("'", "''")
    escaped_name = payload["name"].replace("'", "''")
    escaped_database = payload["database"].replace("'", "''")
    escaped_schema = payload["schema"].replace("'", "''")
    escaped_output_table = payload["outputTable"].replace("'", "''")

    insert_sql = f"""
    INSERT INTO CONFIGURATIONS (
        CONFIG_ID, NAME, DATABASE_NAME, SCHEMA_NAME,
        TABLES, OUTPUT_TABLE, MAPPINGS, STATUS, CREATED_AT, UPDATED_AT
    )
    SELECT
        '{escaped_config_id}',
        '{escaped_name}',
        '{escaped_database}',
        '{escaped_schema}',
        PARSE_JSON('{tables_json.replace("'", "''")}'),
        '{escaped_output_table}',
        PARSE_JSON('{mappings_json.replace("'", "''")}'),
        'active',
        CURRENT_TIMESTAMP(),
        CURRENT_TIMESTAMP()
    """

    session.sql(insert_sql).collect()

    return {"configId": config_id}


def delete_configuration(config_id: str) -> dict[str, bool]:
    """
    Delete a configuration by ID.

    Args:
        config_id: Configuration ID to delete

    Returns:
        Success status

    Raises:
        HTTPException: 404 if configuration not found
    """
    session = snowflake_service._get_session()

    configs_df = session.table("CONFIGURATIONS")
    count = configs_df.filter(F.col("CONFIG_ID") == config_id).count()

    if count == 0:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

    escaped_config_id = config_id.replace("'", "''")
    delete_query = f"DELETE FROM CONFIGURATIONS WHERE CONFIG_ID = '{escaped_config_id}'"
    session.sql(delete_query).collect()

    return {"success": True}


def start_generation_job(config_id: str, job_type: str) -> dict[str, str]:
    """
    Start a new generation job for a configuration.

    Args:
        config_id: Configuration ID
        job_type: Type of job ('enrichment' or 'aggregation')

    Returns:
        Dictionary with jobId
    """
    session = snowflake_service._get_session()

    configs_df = session.table("CONFIGURATIONS")
    count = configs_df.filter(F.col("CONFIG_ID") == config_id).count()

    if count == 0:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
    job_id = f"job_{int(datetime.now().timestamp() * 1000)}"

    escaped_job_id = job_id.replace("'", "''")
    escaped_config_id = config_id.replace("'", "''")
    escaped_job_type = job_type.replace("'", "''")

    insert_job_sql = f"""
    INSERT INTO GENERATION_JOBS (
        JOB_ID, CONFIG_ID, JOB_TYPE, STATUS, PROGRESS, STARTED_AT, CREATED_AT
    )
    VALUES (
        '{escaped_job_id}',
        '{escaped_config_id}',
        '{escaped_job_type}',
        'queued',
        0,
        NULL,
        CURRENT_TIMESTAMP()
    )
    """

    session.sql(insert_job_sql).collect()

    if job_type == "enrichment":
        try:
            session.sql(f"""
                UPDATE GENERATION_JOBS
                SET STATUS = 'processing', STARTED_AT = CURRENT_TIMESTAMP()
                WHERE JOB_ID = '{escaped_job_id}'
            """).collect()

            enrichment_service.start_enrichment_job(config_id, job_id)

            session.sql(f"""
                UPDATE GENERATION_JOBS
                SET STATUS = 'completed', PROGRESS = 100, COMPLETED_AT = CURRENT_TIMESTAMP()
                WHERE JOB_ID = '{escaped_job_id}'
            """).collect()
        except (SnowparkSQLException, ValueError, RuntimeError) as e:
            escaped_error = str(e).replace("'", "''")
            update_query = f"""
                UPDATE GENERATION_JOBS
                SET STATUS = 'failed', ERROR_MESSAGE = '{escaped_error}'
                WHERE JOB_ID = '{escaped_job_id}'
            """
            session.sql(update_query).collect()
            raise
    elif job_type in ["analytics", "aggregation"]:
        try:
            session.sql(f"""
                UPDATE GENERATION_JOBS
                SET STATUS = 'processing', STARTED_AT = CURRENT_TIMESTAMP()
                WHERE JOB_ID = '{escaped_job_id}'
            """).collect()

            enrichment_service.start_analytics_job(config_id, job_id)

            session.sql(f"""
                UPDATE GENERATION_JOBS
                SET STATUS = 'completed', PROGRESS = 100, COMPLETED_AT = CURRENT_TIMESTAMP()
                WHERE JOB_ID = '{escaped_job_id}'
            """).collect()
        except (SnowparkSQLException, ValueError, RuntimeError) as e:
            escaped_error = str(e).replace("'", "''")
            update_query = f"""
                UPDATE GENERATION_JOBS
                SET STATUS = 'failed', ERROR_MESSAGE = '{escaped_error}'
                WHERE JOB_ID = '{escaped_job_id}'
            """
            session.sql(update_query).collect()
            raise

    return {"jobId": job_id}


def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Get status of a generation job.

    Args:
        job_id: Job ID

    Returns:
        Job status information

    Raises:
        HTTPException: 404 if job not found
    """
    session = snowflake_service._get_session()
    jobs_df = session.table("GENERATION_JOBS")
    job_df = jobs_df.filter(F.col("JOB_ID") == job_id).select(
        F.col("JOB_ID"),
        F.col("STATUS"),
        F.col("PROGRESS"),
        F.col("ESTIMATED_TIME"),
        F.col("PROCESSED_RECORDS"),
        F.col("ERROR_RECORDS"),
    )

    results = job_df.collect()

    if not results:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    row = results[0]

    return {
        "jobId": row["JOB_ID"],
        "status": row["STATUS"],
        "progress": int(row["PROGRESS"]) if row["PROGRESS"] else 0,
        "estimatedTime": int(row["ESTIMATED_TIME"]) if row["ESTIMATED_TIME"] else None,
        "results": {
            "processed": int(row["PROCESSED_RECORDS"]) if row["PROCESSED_RECORDS"] else 0,
            "errors": int(row["ERROR_RECORDS"]) if row["ERROR_RECORDS"] else 0,
        },
    }
