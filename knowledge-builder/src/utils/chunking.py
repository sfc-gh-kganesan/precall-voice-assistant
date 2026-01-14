from snowflake.snowpark import Session, Window
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T
from snowflake.snowpark.table import Table

DEFAULT_CHUNK_SIZE = 1800
DEFAULT_CHUNK_OVERLAP = 300
DEFAULT_PROCESSING_VERSION = "v1"


def clean_html_expr(text_col: str = "TEXT"):
    return F.trim(F.regexp_replace(F.regexp_replace(F.col(text_col), r"<[^>]+>|&nbsp;", " "), r"\s+", " "))


def chunk_knowledge_articles(
    session: Session,
    source_table: str = "KB_KNOWLEDGE",
    target_table: str = "KB_CHUNKS",
    text_col: str = "TEXT",
    id_col: str = "NUMBER",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    processing_version: str = DEFAULT_PROCESSING_VERSION,
    write_mode: str = "overwrite",
) -> Table:
    kb_knowledge = session.table(source_table)

    result = (
        kb_knowledge.with_column("CLEAN_HTML", clean_html_expr(text_col))
        .ai.split_text_recursive_character(
            text_to_split="CLEAN_HTML",
            format="none",
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            output_column="CHUNK_TEXT",
        )
        .join_table_function("flatten", F.col("CHUNK_TEXT"))
        .select(
            F.col(id_col).alias("KB_SYS_ID"),
            F.row_number().over(Window.order_by(F.lit(1))).alias("CHUNK_INDEX"),
            F.col("VALUE").cast(T.StringType()).alias("CHUNK_TEXT"),
            F.current_timestamp().alias("SOURCE_UPDATED_ON"),
            F.lit(processing_version).alias("PROCESSING_VERSION"),
            F.current_timestamp().alias("CREATED_AT"),
        )
    )

    result.write.save_as_table(target_table, mode=write_mode)
    return session.table(target_table)
