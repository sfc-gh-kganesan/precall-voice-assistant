-- Stored Procedure: Analyze image src links from KB knowledge articles
-- Consolidates into categories: base64, relative, sys_attachment, or domain
-- Returns: CATEGORY, COUNT, DISTINCT_ARTICLES
-- Usage: CALL ANALYZE_IMAGE_LINKS();

CREATE OR REPLACE PROCEDURE ANALYZE_IMAGE_LINKS()
RETURNS TABLE (CATEGORY STRING, COUNT INT, DISTINCT_ARTICLES INT)
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'lxml', 'pandas')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
import pandas as pd
from lxml import html as lxml_html
from urllib.parse import urlparse
from snowflake.snowpark import Session

def extract_image_srcs(html_text: str) -> list:
    """Extract img src values using lxml"""
    if not html_text or not isinstance(html_text, str):
        return []
    try:
        doc = lxml_html.fromstring(html_text)
        return doc.xpath('//img/@src')
    except Exception:
        return []

def categorize_src(src: str) -> str:
    """Categorize an image src into: base64, sys_attachment, relative, or domain."""
    if not src:
        return None
    
    src = src.strip()
    
    # 1. Base64 encoded images
    if src.startswith('data:'):
        return '[1] base64'
    
    # 2. ServiceNow sys_attachment
    if '/sys_attachment.do?' in src or src.startswith('sys_attachment.do?'):
        return '[2] sys_attachment'
    
    # 3. Full URLs - extract domain
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
    
    # 4. Relative paths (everything else)
    return '[3] relative'

def run(session: Session):
    # Query KB knowledge articles
    df = session.sql("""
        SELECT SYS_ID, TEXT 
        FROM KB_KNOWLEDGE
        WHERE TEXT IS NOT NULL 
          AND ACTIVE = TRUE 
          AND LATEST = TRUE
    """).to_pandas()
    
    if df.empty:
        return session.create_dataframe(
            [], 
            schema=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"]
        )
    
    # Extract image srcs for each article
    processed_data = [
        (row["SYS_ID"], extract_image_srcs(row["TEXT"]))
        for _, row in df.iterrows()
    ]
    
    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "IMG_SRC"])
    exploded_df = temp_df.explode("IMG_SRC")
    exploded_df = exploded_df.dropna(subset=["IMG_SRC"])
    
    if exploded_df.empty:
        return session.create_dataframe(
            [], 
            schema=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"]
        )
    
    # Categorize each image src
    exploded_df["CATEGORY"] = exploded_df["IMG_SRC"].apply(categorize_src)
    
    # Aggregate by category
    result = (
        exploded_df
        .groupby("CATEGORY")
        .agg(
            COUNT=("CATEGORY", "size"),
            DISTINCT_ARTICLES=("ARTICLE_ID", "nunique")
        )
        .reset_index()
    )
    
    # Sort: special categories [1], [2], [3] at top (by name), then domains by count desc
    def sort_key(row):
        if row["CATEGORY"].startswith("["):
            # Special categories: sort by category name (e.g., [1], [2], [3])
            return (0, row["CATEGORY"], 0)
        else:
            # Domains: sort by count descending (use negative for desc)
            return (1, "", -row["COUNT"])
    
    result["_sort"] = result.apply(sort_key, axis=1)
    result = result.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    
    # Convert to int for Snowflake
    result["COUNT"] = result["COUNT"].astype(int)
    result["DISTINCT_ARTICLES"] = result["DISTINCT_ARTICLES"].astype(int)
    
    return session.create_dataframe(result)
$$;

-- Example usage:
-- CALL ANALYZE_IMAGE_LINKS();

-- Expected output (sorted by CATEGORY, prefixed ones at top):
-- | CATEGORY                    | COUNT | DISTINCT_ARTICLES |
-- |-----------------------------|-------|-------------------|
-- | [1] base64                  | 50    | 10                |  -- data:image/png;base64,...
-- | [2] sys_attachment          | 5000  | 1200              |  -- /sys_attachment.do?sys_id=...
-- | [3] relative                | 100   | 25                |  -- /path/image.png, -7.pngx, etc.
-- | confluence.atlassian.com    | 150   | 30                |  -- Full domain URLs
-- | sanofi.sharepoint.com       | 300   | 50                |  -- Full domain URLs

