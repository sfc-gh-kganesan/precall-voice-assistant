CREATE OR REPLACE PROCEDURE <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.ANALYZE_IMAGE_LINKS()
RETURNS TABLE (CATEGORY STRING, COUNT INT, DISTINCT_ARTICLES INT)
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'lxml', 'pandas')
HANDLER = 'run'
EXECUTE AS CALLER
COMMENT = 'Analyze image src links from KB articles. Returns categories: base64, relative, sys_attachment, or domain.'
AS
$$
import pandas as pd
from lxml import html as lxml_html
from urllib.parse import urlparse
from snowflake.snowpark import Session

def extract_image_srcs(html_text: str) -> list:
    if not html_text or not isinstance(html_text, str):
        return []
    try:
        doc = lxml_html.fromstring(html_text)
        return doc.xpath('//img/@src')
    except Exception:
        return []

def categorize_src(src: str) -> str:
    if not src:
        return None
    src = src.strip()
    if src.startswith('data:'):
        return '[1] base64'
    if '/sys_attachment.do?' in src or src.startswith('sys_attachment.do?'):
        return '[2] sys_attachment'
    if src.startswith(('http://', 'https://', '//')):
        try:
            if src.startswith('//'):
                src = 'https:' + src
            parsed = urlparse(src)
            domain = parsed.netloc.lower()
            if domain:
                return domain
        except Exception:
            pass
        return '[4] unknown_url'
    return '[3] relative'

def run(session: Session):
    df = session.sql("""
        SELECT SYS_ID, TEXT
        FROM KB_KNOWLEDGE
        WHERE TEXT IS NOT NULL AND ACTIVE = TRUE AND LATEST = TRUE
    """).to_pandas()

    if df.empty:
        return session.create_dataframe([], schema=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"])

    processed_data = [(row["SYS_ID"], extract_image_srcs(row["TEXT"])) for _, row in df.iterrows()]
    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "IMG_SRC"])
    exploded_df = temp_df.explode("IMG_SRC").dropna(subset=["IMG_SRC"])

    if exploded_df.empty:
        return session.create_dataframe([], schema=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"])

    exploded_df["CATEGORY"] = exploded_df["IMG_SRC"].apply(categorize_src)
    result = exploded_df.groupby("CATEGORY").agg(
        COUNT=("CATEGORY", "size"),
        DISTINCT_ARTICLES=("ARTICLE_ID", "nunique")
    ).reset_index()

    def sort_key(row):
        if row["CATEGORY"].startswith("["):
            return (0, row["CATEGORY"], 0)
        return (1, "", -row["COUNT"])

    result["_sort"] = result.apply(sort_key, axis=1)
    result = result.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    result["COUNT"] = result["COUNT"].astype(int)
    result["DISTINCT_ARTICLES"] = result["DISTINCT_ARTICLES"].astype(int)

    return session.create_dataframe(result)
$$;
