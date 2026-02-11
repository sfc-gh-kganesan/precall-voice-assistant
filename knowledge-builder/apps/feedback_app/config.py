"""
Application configuration from environment variables.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    DATABASE: str
    SCHEMA: str
    SEARCH_SERVICE: str
    SEARCH_FEEDBACK_TABLE: str
    SEARCH_QUERIES_TABLE: str
    GOLDEN_PAIRS_TABLE: str
    SYNTHETIC_PAIRS_TABLE: str

    # UI settings
    PAGE_TITLE: str
    PAGE_ICON: str
    RATING_ADJUSTMENT: int
    SEARCH_LIMIT: int


config = Config(
    DATABASE=os.environ.get("KB_DATABASE_NAME", "KNOWLEDGE_BUILDER"),
    SCHEMA=os.environ.get("KB_SCHEMA_NAME", "PUBLIC"),
    SEARCH_SERVICE=os.environ.get("KB_SEARCH_SERVICE", "KB_SEARCH"),
    SEARCH_FEEDBACK_TABLE=os.environ.get("SEARCH_FEEDBACK_TABLE", "SEARCH_FEEDBACK"),
    SEARCH_QUERIES_TABLE=os.environ.get("SEARCH_QUERIES_TABLE", "SEARCH_QUERIES"),
    GOLDEN_PAIRS_TABLE=os.environ.get("GOLDEN_PAIRS_TABLE", "GOLDEN_PAIRS"),
    SYNTHETIC_PAIRS_TABLE=os.environ.get("SYNTHETIC_PAIRS_TABLE", "SYNTHETIC_PAIRS"),
    PAGE_TITLE="Feedback App",
    PAGE_ICON="📝",
    RATING_ADJUSTMENT=1,
    SEARCH_LIMIT=5,
)


# LLM models for playground responses
LLM_MODELS = (
    "llama3.1-8b",
    "llama3.1-70b",
    "mistral-large2",
)
