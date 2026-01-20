from urllib.parse import unquote, urlparse

import pandas as pd
import streamlit as st
from data_operations import SnowflakeDataOperations
from ui_utils import create_bar_chart
from ydata_profiling import ProfileReport

from config import db_config, eda_config


def profile_data(df: pd.DataFrame) -> str:
    profile = ProfileReport(df, title="Pandas Profiling Report", explorative=True)
    profile.config.html.use_local_assets = True
    profile.config.html.inline = True
    profile.config.html.navbar_show = False
    return profile.to_html()


def extract_domains_from_html(html_text: str) -> list:
    if not isinstance(html_text, str) or not html_text:
        return []

    urls = eda_config.href_pattern.findall(html_text)
    urls += eda_config.url_pattern.findall(html_text)

    domains = []
    for raw in urls:
        try:
            if not raw or len(raw) < 4:
                continue

            u = unquote(raw.strip())

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
    if df.empty:
        return pd.DataFrame(columns=["DOMAIN", "COUNT", "DISTINCT_ARTICLES"])

    if "ARTICLE_ID" in df.columns:
        id_col = "ARTICLE_ID"
    elif "SYS_ID" in df.columns:
        id_col = "SYS_ID"
    else:
        df = df.reset_index()
        id_col = "index"

    processed_data = [(row_id, extract_domains_from_html(text)) for row_id, text in zip(df[id_col], df[text_col], strict=False)]

    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "DOMAIN"])
    exploded_df = temp_df.explode("DOMAIN")
    exploded_df = exploded_df.dropna(subset=["DOMAIN"])
    if exploded_df.empty:
        return pd.DataFrame(columns=["DOMAIN", "COUNT", "DISTINCT_ARTICLES"])
    result = (
        exploded_df.groupby("DOMAIN")
        .agg(
            COUNT=("DOMAIN", "size"),
            DISTINCT_ARTICLES=("ARTICLE_ID", "nunique"),
        )
        .reset_index()
        .sort_values("COUNT", ascending=False)
    )
    return result


def render_eda_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("Exploratory Data Analysis")
    st.caption("Analyze your knowledge base content, detect external links, and identify potential data quality issues.")

    try:
        kb_knowledge = data_ops.get_knowledge_data(db_config.kb_knowledge_table)
        describe_df = kb_knowledge.describe()
        numeric_df = kb_knowledge.select_dtypes(exclude=["object"])
        cat_df = kb_knowledge.select_dtypes(include=["object"])
        report_html = profile_data(numeric_df)

        numeric_tab, cat_tab, links_tab, image_links_tab = st.tabs(["Numeric", "Categorical", "Outbound Links", "Image Links"])

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
                chart = create_bar_chart(
                    link_summary.head(20),
                    x_col="COUNT",
                    y_col="DOMAIN",
                    title="Top 20 Outbound Domains Referenced",
                    tooltip_cols=["DOMAIN", "COUNT"],
                    x_title="Number of References",
                    y_title="Domain",
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("Domains such as Confluence, Atlassian, or SharePoint often indicate knowledge stored outside official systems.")

        with image_links_tab:
            st.subheader("Image Link Analysis")
            st.caption("Categorized image sources from <img> tags (via ANALYZE_IMAGE_LINKS SPROC).")

            try:
                image_summary = data_ops.call_stored_procedure("ANALYZE_IMAGE_LINKS")

                if image_summary.empty:
                    st.warning("No image links found in the dataset.")
                else:
                    st.dataframe(image_summary, use_container_width=True)
                    chart = create_bar_chart(
                        image_summary.head(15),
                        x_col="COUNT",
                        y_col="CATEGORY",
                        title="Image Source Categories",
                        tooltip_cols=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"],
                        x_title="Count",
                        y_title="Category",
                    )
                    st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.warning(f"Image link analysis not available. Create ANALYZE_IMAGE_LINKS stored procedure to enable this feature.\n\nError: {str(e)}")

    except Exception as e:
        st.error(f"Error loading EDA data: {str(e)}")
        st.info(f"Make sure the {db_config.kb_knowledge_table} table exists and is accessible.")
