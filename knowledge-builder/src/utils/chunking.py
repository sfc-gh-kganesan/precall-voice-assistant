from snowflake.snowpark import Session
from snowflake.snowpark.table import Table

DEFAULT_CHUNK_SIZE = 1800
DEFAULT_CHUNK_OVERLAP = 300
DEFAULT_PROCESSING_VERSION = "v1"


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
    """
    Chunk knowledge articles using Snowflake Cortex SPLIT_TEXT_RECURSIVE_CHARACTER.

    Uses SQL-based chunking for reliable results with proper chunk sizes.
    """
    sql = f"""
    WITH cleaned AS (
        SELECT
            {id_col} as KB_SYS_ID,
            SHORT_DESCRIPTION,
            KB_KNOWLEDGE_BASE as KNOWLEDGE_BASE,
            CAN_READ_USER_CRITERIA,
            CANNOT_READ_USER_CRITERIA,
            SYS_UPDATED_ON as SOURCE_UPDATED_ON,
            TRIM(REGEXP_REPLACE(REGEXP_REPLACE({text_col}, '<[^>]+>|&nbsp;', ' '), '\\\\s+', ' ')) as CLEAN_TEXT
        FROM {source_table}
        WHERE {text_col} IS NOT NULL
    ),
    chunked AS (
        SELECT
            KB_SYS_ID,
            SHORT_DESCRIPTION,
            KNOWLEDGE_BASE,
            CAN_READ_USER_CRITERIA,
            CANNOT_READ_USER_CRITERIA,
            SOURCE_UPDATED_ON,
            SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
                CLEAN_TEXT,
                'none',
                {chunk_size},
                {chunk_overlap}
            ) as CHUNKS
        FROM cleaned
    )
    SELECT
        c.KB_SYS_ID,
        c.KB_SYS_ID as KB_NUMBER,
        ROW_NUMBER() OVER (PARTITION BY c.KB_SYS_ID ORDER BY f.INDEX) as CHUNK_INDEX,
        f.VALUE::STRING as CHUNK_TEXT,
        c.SHORT_DESCRIPTION,
        c.KNOWLEDGE_BASE,
        c.CAN_READ_USER_CRITERIA,
        c.CANNOT_READ_USER_CRITERIA,
        '{processing_version}' as PROCESSING_VERSION,
        c.SOURCE_UPDATED_ON,
        CURRENT_TIMESTAMP() as CREATED_AT
    FROM chunked c,
    LATERAL FLATTEN(input => c.CHUNKS) f
    """

    result = session.sql(sql)
    result.write.save_as_table(target_table, mode=write_mode)
    return session.table(target_table)
