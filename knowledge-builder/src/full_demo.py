from snowflake.core import Root
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark import functions as F, types as T
import pandas as pd


def ingest_knowledge():
    df = pd.read_csv("kb_knowledge.csv", encoding="latin_1").rename(columns=str.upper)
    t = session.create_dataframe(df)
    t.write.save_as_table("KB_KNOWLEDGE", mode="overwrite")


session = get_active_session()
root = Root(session)
schema_ctx = root.databases["KNOWLEDGE_BUILDER"].schemas["PUBLIC"]
ingest_knowledge()
t = session.table("KB_KNOWLEDGE")

clean_html = (
    F.trim(
        F.regexp_replace(
            F.regexp_replace(F.col("TEXT"), r"<[^>]+>|&nbsp;", " "),
            r"\s+", " "
        )
    )
)

result = (
    t
    .with_column("HTML_TEXT", clean_html)
    .ai
    .split_text_recursive_character(
        text_to_split="HTML_TEXT",
        format="none",
        chunk_size=30,
        overlap=5,
        output_column="CHUNKS"
    )
    .join_table_function(
        "flatten",
        F.col("CHUNKS")
    )
    .select("TEXT", "HTML_TEXT", F.col("CHUNKS").alias("TEXT_CHUNK"))
)

session.sql("""
CREATE OR REPLACE CORTEX SEARCH SERVICE search_on_table
  ON TEXT
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
AS (
  SELECT TEXT
  FROM KB_KNOWLEDGE
)
""")

filter_expr = F.lit(1) == 1

cols = [
    F.col("TEXT"),
    F.col("VERSION"),
    F.col("SHORT_DESCRIPTION")
]
(
    session
    .table("kb_knowledge")
    .filter(filter_expr)
    .select(cols)
    .create_or_replace_view("KB_KNOWLEDGE_VIEW")
)

session.sql("""
CREATE OR REPLACE CORTEX SEARCH SERVICE search_on_view
  ON TEXT
  WAREHOUSE = compute_wh
  TARGET_LAG = '1 hour'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
AS (
  SELECT TEXT
  FROM KB_KNOWLEDGE_VIEW
)
""")

table_service = schema_ctx.cortex_search_services["SEARCH_ON_TABLE"]
view_service = schema_ctx.cortex_search_services["SEARCH_ON_VIEW"]

search_args = dict(
    query="Hello",
    columns=["TEXT"],
    filter={},
    limit=5
)

resp_1 = table_service.search(**search_args)
resp_2 = view_service.search(**search_args)

for response in (resp_1, resp_2):
    print(response)
