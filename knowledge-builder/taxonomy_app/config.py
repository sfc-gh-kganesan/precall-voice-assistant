"""
Application configuration from environment variables.

Environment variables (with defaults):
- KB_SCHEMA_NAME: Schema name (default: CORE)
- SYNTHETIC_PAIRS_TABLE: Synthetic pairs table (default: SYNTHETIC_PAIRS)
- SEARCH_QUERIES_TABLE: Search queries table (default: SEARCH_QUERIES)
- EVALUATION_RESULTS_TABLE: Evaluation results table (default: EVALUATION_RESULTS)
- KB_CHUNKS_VIEW: KB chunks view (default: KB_CHUNKS_V)
- KB_SEARCH_SERVICE: Cortex Search service name (default: KB_SEARCH)
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    SCHEMA: str
    SYNTHETIC_PAIRS_TABLE: str
    SEARCH_QUERIES_TABLE: str
    EVALUATION_RESULTS_TABLE: str
    KB_CHUNKS_VIEW: str
    KB_SEARCH_SERVICE: str


config = Config(
    SCHEMA=os.environ.get("KB_SCHEMA_NAME", "CORE"),
    SYNTHETIC_PAIRS_TABLE=os.environ.get("SYNTHETIC_PAIRS_TABLE", "SYNTHETIC_PAIRS"),
    SEARCH_QUERIES_TABLE=os.environ.get("SEARCH_QUERIES_TABLE", "SEARCH_QUERIES"),
    EVALUATION_RESULTS_TABLE=os.environ.get("EVALUATION_RESULTS_TABLE", "EVALUATION_RESULTS"),
    KB_CHUNKS_VIEW=os.environ.get("KB_CHUNKS_VIEW", "KB_CHUNKS_V"),
    KB_SEARCH_SERVICE=os.environ.get("KB_SEARCH_SERVICE", "KB_SEARCH"),
)
