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


def generate_gradient(primary_color: str, steps: int = 6) -> list[str]:
    """
    Generate a gradient from white to the primary color.

    Args:
        primary_color: Hex color string (e.g., "#7A00E6")
        steps: Number of colors in the gradient

    Returns:
        List of hex color strings from white to primary
    """
    primary = primary_color.lstrip("#")
    r2, g2, b2 = int(primary[0:2], 16), int(primary[2:4], 16), int(primary[4:6], 16)
    r1, g1, b1 = 255, 255, 255

    gradient = []
    for i in range(steps):
        t = i / (steps - 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        gradient.append(f"#{r:02X}{g:02X}{b:02X}")

    return gradient


PRIMARY_COLOR = "#7A00E6"
COLOR_SCALE = generate_gradient(PRIMARY_COLOR)
