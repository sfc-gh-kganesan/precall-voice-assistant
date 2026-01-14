CREATE OR REPLACE FUNCTION <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.FN_DECOMPOSE_CHUNK(chunk_text STRING)
RETURNS VARIANT
LANGUAGE SQL
COMMENT = 'Extract summary and chunk_text from structured chunk format with <DOC_SUMMARY> and <CHUNK_TEXT> tags.'
AS
$$
OBJECT_CONSTRUCT(
    'summary', REGEXP_SUBSTR(chunk_text, '<DOC_SUMMARY>(.*?)</DOC_SUMMARY>', 1, 1, 's', 1),
    'chunk_text', REGEXP_SUBSTR(chunk_text, '<CHUNK_TEXT>(.*?)</CHUNK_TEXT>', 1, 1, 's', 1)
)
$$;

CREATE OR REPLACE FUNCTION <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.EXTRACT_DOMAINS_FROM_HTML(HTML_TEXT STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
HANDLER = 'extract_domains_handler'
COMMENT = 'Extract unique external domains from HTML content (comma-separated).'
AS
$$
import re
from urllib.parse import urlparse, unquote

def extract_domains_handler(html_text):
    if not isinstance(html_text, str) or not html_text:
        return ""

    urls = re.findall(r'href=["\']?([^"\'>\s]+)', html_text, flags=re.IGNORECASE)
    urls += re.findall(r'https?://[^\s"\'>]+', html_text, flags=re.IGNORECASE)

    domains = []
    for raw in urls:
        try:
            u = unquote(raw.strip())
            if u.lower().startswith("www."):
                u = "https://" + u
            if not u.lower().startswith(("http://", "https://")):
                continue
            parsed = urlparse(u)
            domain = parsed.netloc.lower()
            if domain and domain not in ("server", "localhost"):
                domains.append(domain)
        except Exception:
            continue

    return ",".join(sorted(set(domains))) if domains else ""
$$;

CREATE OR REPLACE FUNCTION <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.SPLIT_DOMAINS(DOMAINS_CSV STRING)
RETURNS TABLE(DOMAIN STRING)
LANGUAGE SQL
COMMENT = 'Split comma-separated domains into rows for aggregation.'
AS
$$
    SELECT TRIM(VALUE)::STRING AS DOMAIN
    FROM TABLE(SPLIT_TO_TABLE(DOMAINS_CSV, ','))
    WHERE TRIM(VALUE) != ''
$$;
