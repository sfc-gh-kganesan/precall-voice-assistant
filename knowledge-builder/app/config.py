import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    database: str = "KNOWLEDGE_BUILDER"
    schema: str = "PUBLIC"
    search_service: str = "KB_SEARCH"
    target_table: str = "SEARCH_FEEDBACK"
    results_table: str = "SEARCH_QUERIES"
    evaluation_results_table: str = "EVALUATION_RESULTS"
    golden_pairs_table: str = "GOLDEN_PAIRS"
    synthetic_pairs_table: str = "SYNTHETIC_PAIRS"
    kb_knowledge_table: str = "KB_KNOWLEDGE"
    kb_chunks_table: str = "KB_CHUNKS"

    def get_table_name(self, table: str) -> str:
        return f"{self.database}.{self.schema}.{table}"


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_size: int = 1800
    chunk_overlap: int = 300
    processing_version: str = "v1"
    text_column: str = "TEXT"
    id_column: str = "NUMBER"


@dataclass(frozen=True)
class SearchConfig:
    columns: tuple = ("CHUNK_TEXT",)
    filter: dict = None
    limit: int = 5

    def __post_init__(self):
        if self.filter is None:
            object.__setattr__(self, "filter", {})

    def to_dict(self):
        return {
            "columns": list(self.columns),
            "filter": self.filter,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class UIConfig:
    page_title: str = "Knowledge Builder"
    page_icon: str = "books"
    sidebar_logo: str = "snowflake-logo-color-rgb@1x.png"
    rating_adjustment: int = 1
    feedback_placeholder: str = "I wished this came back with..."
    feedback_textarea_height: int = 100


@dataclass(frozen=True)
class EDAConfig:
    href_pattern: re.Pattern = re.compile(r'href=["\']?([^"\'>\s]+)', flags=re.IGNORECASE)
    url_pattern: re.Pattern = re.compile(r'https?://[^\s"\'>]+', flags=re.IGNORECASE)


db_config = DatabaseConfig()
search_config = SearchConfig()
ui_config = UIConfig()
eda_config = EDAConfig()
chunking_config = ChunkingConfig()
