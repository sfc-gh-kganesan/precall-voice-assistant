from typing import Literal

from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    targetField: str
    sourceType: Literal["column", "generated", "json_path"]
    sourceColumn: str | None = None
    sourceColumns: list[str] | None = None
    aiInstruction: str | None = None
    jsonPath: str | None = None
    generationType: Literal["llm", "regex", "lookup"] | None = None
    generationConfig: dict | None = None


class ConfigCreateRequest(BaseModel):
    name: str
    database: str
    schema_: str = Field(..., serialization_alias="schema", validation_alias="schema")
    tables: list[str]
    outputTable: str
    mappings: list[FieldMapping]


class ConfigurationStatus(BaseModel):
    baseTable: dict
    topicMetrics: dict
    productMetrics: dict
    kpiSummary: dict


class ConfigurationSummary(BaseModel):
    configId: str
    name: str
    database: str
    schema_: str = Field(..., serialization_alias="schema", validation_alias="schema")
    tables: list[str]
    createdAt: str
    status: ConfigurationStatus


class ConfigurationDetail(BaseModel):
    config: dict
    status: ConfigurationStatus


class GenerationJob(BaseModel):
    jobId: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int | None = None
    estimatedTime: int | None = None
    results: dict | None = None
