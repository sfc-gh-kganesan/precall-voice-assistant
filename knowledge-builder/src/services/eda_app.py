import re
from urllib.parse import unquote, urlparse

import altair as alt
import pandas as pd
import streamlit as st
from lxml import html as lxml_html
from snowflake.snowpark.context import get_active_session
from ydata_profiling import ProfileReport

from services import taxonomy

HREF_PATTERN = re.compile(r'href=["\']?([^"\'>\s]+)', flags=re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://[^\s"\'>]+', flags=re.IGNORECASE)


@st.cache_data
def knowledge_data(table_name: str) -> pd.DataFrame:
    kb_knowledge = session.table(table_name).to_pandas()
    return kb_knowledge


@st.cache_data
def profile_data(df: pd.DataFrame) -> str:
    profile = ProfileReport(df, title="Pandas Profiling Report", explorative=True)
    profile.config.html.use_local_assets = True
    profile.config.html.inline = True
    profile.config.html.navbar_show = False
    return profile.to_html()


def extract_domains_from_html(html_text: str) -> list:
    """
    Extracts all domain occurrences.
    """
    if not isinstance(html_text, str) or not html_text:
        return []

    # Use compiled patterns
    urls = HREF_PATTERN.findall(html_text)
    urls += URL_PATTERN.findall(html_text)

    domains = []
    for raw in urls:
        try:
            if not raw or len(raw) < 4:
                continue

            u = unquote(raw.strip())

            # Handle protocol
            u_lower = u.lower()
            if u_lower.startswith("www."):
                u = "https://" + u
            elif not u_lower.startswith(("http://", "https://")):
                continue

            parsed = urlparse(u)
            domain = parsed.netloc.lower()

            if not domain or domain in ("server", "localhost"):
                continue

            domains.append(domain)
        except ValueError:
            continue

    return domains


def analyze_outbound_links(df: pd.DataFrame, text_col: str = "TEXT") -> pd.DataFrame:
    """Aggregate domains, counting total occurrences and distinct articles."""
    if df.empty:
        return pd.DataFrame(columns=["DOMAIN", "COUNT", "DISTINCT_ARTICLES"])
    processed_data = [(row_id, extract_domains_from_html(text)) for row_id, text in zip(df["SYS_ID"], df[text_col], strict=False)]

    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "DOMAIN"])
    exploded_df = temp_df.explode("DOMAIN")
    exploded_df = exploded_df.dropna(subset=["DOMAIN"])
    if exploded_df.empty:
        return pd.DataFrame(columns=["DOMAIN", "COUNT", "DISTINCT_ARTICLES"])
    result = (
        exploded_df.groupby("DOMAIN")
        .agg(
            COUNT=("DOMAIN", "size"),  # Total link occurrences
            DISTINCT_ARTICLES=("ARTICLE_ID", "nunique"),  # Distinct source articles
        )
        .reset_index()
        .sort_values("COUNT", ascending=False)
    )
    return result


def extract_image_srcs(html_text: str) -> list[str]:
    """Extract all image src attributes from HTML content."""
    if not html_text or not isinstance(html_text, str):
        return []
    try:
        doc = lxml_html.fromstring(html_text)
        return doc.xpath("//img/@src")
    except Exception:
        return []


def categorize_image_src(src: str) -> str | None:
    """Categorize an image src into base64, sys_attachment, relative, or domain."""
    if not src:
        return None
    src = src.strip()
    if src.startswith("data:"):
        return "[1] base64"
    if "/sys_attachment.do?" in src or src.startswith("sys_attachment.do?"):
        return "[2] sys_attachment"
    if src.startswith(("http://", "https://", "//")):
        try:
            if src.startswith("//"):
                src = "https:" + src
            parsed = urlparse(src)
            domain = parsed.netloc.lower()
            if domain:
                return domain
        except Exception:
            pass
        return "[4] unknown_url"
    return "[3] relative"


def analyze_image_links(df: pd.DataFrame, text_col: str = "TEXT") -> pd.DataFrame:
    """Analyze image src links from HTML content and return categorized counts."""
    if df.empty:
        return pd.DataFrame(columns=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"])

    processed_data = [(row_id, extract_image_srcs(text)) for row_id, text in zip(df["SYS_ID"], df[text_col], strict=False)]

    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "IMG_SRC"])
    exploded_df = temp_df.explode("IMG_SRC").dropna(subset=["IMG_SRC"])

    if exploded_df.empty:
        return pd.DataFrame(columns=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"])

    exploded_df["CATEGORY"] = exploded_df["IMG_SRC"].apply(categorize_image_src)
    result = (
        exploded_df.groupby("CATEGORY")
        .agg(
            COUNT=("CATEGORY", "size"),
            DISTINCT_ARTICLES=("ARTICLE_ID", "nunique"),
        )
        .reset_index()
    )

    def sort_key(cat: str) -> tuple:
        if cat.startswith("["):
            return (0, cat, 0)
        return (1, "", -result.loc[result["CATEGORY"] == cat, "COUNT"].iloc[0])

    result["_sort"] = result["CATEGORY"].apply(sort_key)
    result = result.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    return result


# table_name input needs to be reviewed for this given
# the following filter exprs where columns may not exist
# english_only = F.col("LANGUAGE") == F.lit("English")
# workflow_published = F.col("WORKFLOW_STATE") == F.lit("Published")
# is_latest = F.col("LATEST") == F.lit(True)
# filter(english_only & workflow_published & is_latest)

session = get_active_session()
kb_knowledge = knowledge_data("KB_KNOWLEDGE")
describe_df = kb_knowledge.describe()
numeric_df = kb_knowledge.select_dtypes(exclude=["object"])
cat_df = kb_knowledge.select_dtypes(include=["object"])
report_html = profile_data(numeric_df)

st.title("Snowflake AI FDE - Luma EDA")
numeric_tab, cat_tab, links_tab, ticket_taxonomy_tab, image_links_tab = st.tabs(["numeric", "categorical", "outbound links", "ticket taxonomies", "image links"])
with numeric_tab:
    st.dataframe(describe_df)
    st.components.v1.html(report_html, width=1000, height=550, scrolling=True)

with cat_tab:
    st.dataframe(cat_df.head())

with links_tab:
    st.subheader("Outbound Link Analysis (Knowledge Leakage)")
    st.caption("Extracting external domains from article HTML content.")

    link_summary = analyze_outbound_links(kb_knowledge, text_col="TEXT")

    if link_summary.empty:
        st.warning("No outbound links found in the dataset.")
    else:
        st.dataframe(link_summary)

        # Top external domains visualization
        chart = (
            alt.Chart(link_summary.head(20))
            .mark_bar()
            .encode(
                x=alt.X("COUNT:Q", title="Number of References"),
                y=alt.Y("DOMAIN:N", sort="-x", title="Domain"),
                tooltip=["DOMAIN", "COUNT"],
            )
            .properties(title="Top 20 Outbound Domains Referenced")
        )
        st.altair_chart(chart, use_container_width=True)

        st.caption("Domains such as Confluence, Atlassian, or SharePoint often indicate knowledge stored outside official systems.")

with ticket_taxonomy_tab:
    taxonomy.render_ticket_taxonomy_tab()

with image_links_tab:
    st.subheader("Image Link Analysis")
    st.caption("Categorized image sources from <img> tags in article HTML content.")

    image_summary = analyze_image_links(kb_knowledge, text_col="TEXT")

    if image_summary.empty:
        st.warning("No image links found in the dataset.")
    else:
        st.dataframe(image_summary, use_container_width=True)

        chart = (
            alt.Chart(image_summary.head(15))
            .mark_bar()
            .encode(
                x=alt.X("COUNT:Q", title="Count"),
                y=alt.Y("CATEGORY:N", sort="-x", title="Category"),
                tooltip=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"],
            )
            .properties(title="Image Source Categories")
        )
        st.altair_chart(chart, use_container_width=True)
