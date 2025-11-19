-- Optional HTML utility functions for knowledge base analysis
-- These functions help identify outbound links and potential knowledge leakage

-- Python UDF to extract domains from HTML content
CREATE OR REPLACE FUNCTION <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(HTML_TEXT STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
HANDLER = 'extract_domains_handler'
COMMENT = 'Extract unique external domains from HTML content (comma-separated). Useful for identifying knowledge leakage to external systems like Confluence, SharePoint, etc.'
AS
$$
import re
from urllib.parse import urlparse, unquote

def extract_domains_handler(html_text):
    """
    Extract unique domains from hrefs or https links in HTML, skipping malformed ones.
    Returns comma-separated string of domains.
    """
    if not isinstance(html_text, str) or not html_text:
        return ""
    
    # Find href attributes and raw https links
    urls = re.findall(r'href=["\']?([^"\'>\s]+)', html_text, flags=re.IGNORECASE)
    urls += re.findall(r'https?://[^\s"\'>]+', html_text, flags=re.IGNORECASE)
    
    domains = []
    for raw in urls:
        try:
            u = unquote(raw.strip())
            
            # Add scheme if missing for www URLs
            if u.lower().startswith("www."):
                u = "https://" + u
            
            # Skip relative or malformed URLs
            if not u.lower().startswith(("http://", "https://")):
                continue
            
            parsed = urlparse(u)
            domain = parsed.netloc.lower()
            
            # Ignore empty or invalid hostnames
            if not domain or domain in ("server", "localhost"):
                continue
            
            domains.append(domain)
            
        except Exception:
            # Ignore malformed URLs silently
            continue
    
    unique_domains = list(set(domains))
    return ",".join(sorted(unique_domains)) if unique_domains else ""
$$;

-- Helper function to split domains into rows (for easier aggregation)
CREATE OR REPLACE FUNCTION <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.SPLIT_DOMAINS(DOMAINS_CSV STRING)
RETURNS TABLE(DOMAIN STRING)
LANGUAGE SQL
COMMENT = 'Split comma-separated domains into rows for aggregation'
AS
$$
    SELECT TRIM(VALUE)::STRING AS DOMAIN
    FROM TABLE(SPLIT_TO_TABLE(DOMAINS_CSV, ','))
    WHERE TRIM(VALUE) != ''
$$;

-- ========================================
-- SIMPLE TESTS
-- ========================================

-- Test 1: Basic extraction with literal HTML
SELECT <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(
    '<a href="https://example.com">Link</a> Visit https://github.com'
) AS EXTRACTED_DOMAINS;
-- Expected: 'example.com,github.com'

-- Test 2: Test with www URLs
SELECT <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(
    '<a href="www.google.com">Google</a>'
) AS EXTRACTED_DOMAINS;
-- Expected: 'www.google.com'

-- Test 3: Test SPLIT_DOMAINS function
SELECT d.DOMAIN
FROM TABLE(<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.SPLIT_DOMAINS('example.com,github.com,google.com')) d;
-- Expected: 3 rows with domains

-- ========================================
-- USAGE EXAMPLES WITH YOUR KB TABLE
-- (Uncomment and replace with your actual table name)
-- ========================================

/*
-- Example 1: Extract domains from actual KB articles
SELECT 
    SYS_ID,
    TITLE,
    <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(TEXT) AS OUTBOUND_DOMAINS
FROM YOUR_DATABASE.YOUR_SCHEMA.YOUR_KB_TABLE
WHERE TEXT IS NOT NULL
LIMIT 5;

-- Example 2: Count top domains across all articles
WITH article_domains AS (
    SELECT 
        SYS_ID,
        <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(TEXT) AS DOMAINS_CSV
    FROM YOUR_DATABASE.YOUR_SCHEMA.YOUR_KB_TABLE
    WHERE TEXT IS NOT NULL
)
SELECT 
    d.DOMAIN,
    COUNT(*) AS REFERENCE_COUNT
FROM article_domains ad,
     TABLE(<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.SPLIT_DOMAINS(ad.DOMAINS_CSV)) d
WHERE ad.DOMAINS_CSV != ''
GROUP BY d.DOMAIN
ORDER BY REFERENCE_COUNT DESC
LIMIT 20;

-- Example 3: Find Confluence/SharePoint/Atlassian references
WITH article_domains AS (
    SELECT 
        SYS_ID,
        TITLE,
        <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(TEXT) AS DOMAINS_CSV
    FROM YOUR_DATABASE.YOUR_SCHEMA.YOUR_KB_TABLE
    WHERE TEXT IS NOT NULL
)
SELECT 
    ad.SYS_ID,
    ad.TITLE,
    d.DOMAIN,
    CASE 
        WHEN LOWER(d.DOMAIN) LIKE '%confluence%' THEN 'Confluence'
        WHEN LOWER(d.DOMAIN) LIKE '%sharepoint%' THEN 'SharePoint'
        WHEN LOWER(d.DOMAIN) LIKE '%atlassian%' THEN 'Atlassian'
    END AS SYSTEM_TYPE
FROM article_domains ad,
     TABLE(<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.SPLIT_DOMAINS(ad.DOMAINS_CSV)) d
WHERE 
    LOWER(d.DOMAIN) LIKE '%confluence%'
    OR LOWER(d.DOMAIN) LIKE '%sharepoint%'
    OR LOWER(d.DOMAIN) LIKE '%atlassian%'
ORDER BY ad.SYS_ID, d.DOMAIN
LIMIT 50;
*/

