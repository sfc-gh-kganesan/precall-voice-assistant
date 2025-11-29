import pandas as pd
from snowflake.core import Root
from snowflake.snowpark import Window
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T
from snowflake.snowpark.context import get_active_session


def ingest_knowledge(mode: str):
    df = pd.read_csv("kb_knowledge.csv", encoding="latin_1").rename(columns=str.upper)
    t = session.create_dataframe(df)
    t.write.save_as_table("KB_KNOWLEDGE", mode=mode)


session = get_active_session()
root = Root(session)
schema_ctx = root.databases["KNOWLEDGE_BUILDER"].schemas["PUBLIC"]
ingest_knowledge(mode="overwrite")
t = session.table("KB_KNOWLEDGE")
session.sql("""
CREATE TABLE IF NOT EXISTS DMT_FCT_KB_PROCESSING_STATUS (
  KB_SYS_ID          STRING PRIMARY KEY,
  STATUS             STRING,
  SOURCE_UPDATED_ON  TIMESTAMP_NTZ,
  PROCESSED_AT       TIMESTAMP_NTZ,
  NUM_CHUNKS         INT,
  ERROR_MESSAGE      STRING,
  PROCESSING_VERSION STRING
)
""")

session.sql("""
CREATE TABLE IF NOT EXISTS DMT_FCT_KB_CHUNKS (
  KB_SYS_ID          STRING,
  CHUNK_INDEX        INT,
  CHUNK_TEXT         STRING,
  SOURCE_UPDATED_ON  TIMESTAMP_NTZ,
  PROCESSING_VERSION STRING,
  CREATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT PK_KB_CHUNK UNIQUE (KB_SYS_ID, CHUNK_INDEX)
)
""")

clean_html = F.trim(
    F.regexp_replace(
        F.regexp_replace(F.col("TEXT"), r"<[^>]+>|&nbsp;", " "), r"\s+", " "
    )
)

result = (
    t.with_column("CLEAN_HTML", clean_html)
    .ai.split_text_recursive_character(
        text_to_split="CLEAN_HTML",
        format="none",
        chunk_size=30,
        overlap=5,
        output_column="CHUNK_TEXT",
    )
    .join_table_function("flatten", F.col("CHUNK_TEXT"))
    .select(
        F.col("NUMBER").alias("KB_SYS_ID"),
        F.row_number().over(Window.order_by(F.lit(1))).alias("CHUNK_INDEX"),
        F.col("VALUE").cast(T.StringType()).alias("CHUNK_TEXT"),
        F.current_timestamp().alias("SOURCE_UPDATED_ON"),
        F.lit("v1").alias("PROCESSING_VERSION"),
        F.current_timestamp().alias("CREATED_AT"),
    )
)

result.write.save_as_table("DMT_FCT_KB_CHUNKS", mode="overwrite")

session.sql(""""
CREATE OR REPLACE CORTEX SEARCH SERVICE search_on_table
  ON CHUNK_TEXT
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
AS (
  SELECT KB_SYS_ID,
         CHUNK_INDEX,
         CHUNK_TEXT,
         SOURCE_UPDATED_ON,
         PROCESSING_VERSION,
         CREATED_AT
  FROM DMT_FCT_KB_CHUNKS
);
""")

table_service = schema_ctx.cortex_search_services["SEARCH_ON_TABLE"]

search_args = dict(
    query="I need to upgrade my computer!", columns=["CHUNK_TEXT"], filter={}, limit=5
)

resp = table_service.search(**search_args)
print(resp.results)
