from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from ..schemas.admin import (
    ConfigCreateRequest,
    ConfigurationDetail,
    ConfigurationSummary,
    GenerationJob,
)
from ..services import configuration as config_service
from ..services import snowflake as snowflake_service
from ..services.schema_manager import SchemaManager

router = APIRouter()


@router.get("/databases", response_model=list[str])
async def get_databases():
    try:
        return await run_in_threadpool(snowflake_service.list_databases)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/schemas", response_model=list[str])
async def get_schemas(database: str = Query(...)):
    try:
        return await run_in_threadpool(snowflake_service.list_schemas, database)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tables", response_model=list[dict])
async def get_tables(database: str = Query(...), schema: str = Query(...)):
    try:
        return await run_in_threadpool(snowflake_service.list_tables, database, schema)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tables/analyze", response_model=list[str])
async def analyze_table(database: str, schema: str, table: str):
    return [
        "CASE_ID",
        "CASE_NUMBER",
        "CREATED_AT",
        "UPDATED_AT",
        "CLOSED_AT",
        "STATUS",
        "SEVERITY",
        "SUBJECT",
        "DESCRIPTION",
        "ACCOUNT_ID",
        "ACCOUNT_NAME",
        "PRIME_CASE_STRUCTURED",
        "CHRONICLE_XML",
        "LAST_MODIFIED_AT",
    ]


@router.get("/tables/preview", response_model=dict)
async def table_preview(database: str, schema: str, table: str, limit: int = 10):
    try:
        return await run_in_threadpool(snowflake_service.preview_table, database, schema, table, limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/configurations", response_model=dict)
async def create_configuration(payload: ConfigCreateRequest):
    try:
        return await run_in_threadpool(config_service.create_configuration, payload.model_dump(by_alias=True))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/configurations", response_model=list[ConfigurationSummary])
async def list_configurations():
    try:
        return await run_in_threadpool(config_service.list_configurations)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/configurations/{config_id}", response_model=ConfigurationDetail)
async def get_configuration(config_id: str):
    try:
        return await run_in_threadpool(config_service.get_configuration, config_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/configurations/{config_id}", response_model=dict)
async def delete_configuration(config_id: str):
    try:
        return await run_in_threadpool(config_service.delete_configuration, config_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate", response_model=dict)
async def start_generation_job(payload: dict):
    try:
        config_id = payload.get("configId")
        job_type = payload.get("jobType", "enrichment")
        return await run_in_threadpool(config_service.start_generation_job, config_id, job_type)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=GenerationJob)
async def get_job_status(job_id: str):
    try:
        return await run_in_threadpool(config_service.get_job_status, job_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/enrich/{config_id}", response_model=dict)
async def run_enrichment(config_id: str):
    try:
        result = await run_in_threadpool(config_service.start_generation_job, config_id, "enrichment")
        return {"message": "Enrichment job started", "jobId": result["jobId"]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analytics/{config_id}", response_model=dict)
async def run_analytics(config_id: str):
    """
    Run analytics aggregation for a configuration.
    Creates TOPICS, PRODUCTS, and KPI_SUMMARY tables from enriched CASES data.

    Args:
        config_id: Configuration ID to run analytics for

    Returns:
        Dictionary with analyticsJobId
    """
    try:
        result = await run_in_threadpool(config_service.start_generation_job, config_id, "analytics")
        return {"analyticsJobId": result["jobId"]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Schema Management Endpoints


@router.get("/schema/status", response_model=dict)
async def get_schema_status():
    try:
        manager = SchemaManager()
        return await run_in_threadpool(manager.get_schema_status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/schema/initialize", response_model=dict)
async def initialize_schema_endpoint(include_sample_data: bool = False):
    try:
        manager = SchemaManager()
        result = await run_in_threadpool(manager.create_tables, include_sample_data=include_sample_data)
        return {
            "message": "Schema initialized successfully",
            "sample_data_included": include_sample_data,
            **result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/schema/clean", response_model=dict)
async def clean_schema_endpoint():
    try:
        manager = SchemaManager()
        result = await run_in_threadpool(manager.clean_schema)
        return {"message": "Schema cleaned successfully", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/schema/reset", response_model=dict)
async def reset_schema_endpoint(include_sample_data: bool = False):
    try:
        manager = SchemaManager()
        await run_in_threadpool(manager.drop_all_tables)
        result = await run_in_threadpool(manager.create_tables, include_sample_data=include_sample_data)
        return {
            "message": "Schema reset successfully",
            "sample_data_included": include_sample_data,
            **result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
