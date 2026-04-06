import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_config
from core.parse_csv import CSVParseError, parse_csv_content

st.set_page_config(page_title="Upload | Semantic Forge", layout="wide")
st.title("📤 Upload Config")

config = get_config()

uploaded_csv = st.file_uploader(
    "Upload SV Config CSV",
    type=["csv"],
    help="CSV with columns: sv_name, domain, table_name, join_to, left_key, right_key, join_type",
)

uploaded_excel = st.file_uploader(
    "Upload Column Metadata Excel (optional)",
    type=["xlsx", "xls"],
    help="Excel with 'Column List - {Domain}' and 'Table Desc {Domain}' sheets",
)

if uploaded_csv is not None:
    csv_content = uploaded_csv.getvalue().decode("utf-8")
    try:
        raw_spec = parse_csv_content(csv_content, uploaded_csv.name)
        st.session_state["raw_spec"] = raw_spec
        st.session_state["csv_content"] = csv_content
        st.session_state["csv_filename"] = uploaded_csv.name
        st.success(
            f"Parsed {len(raw_spec.semantic_views)} semantic view(s) from **{uploaded_csv.name}**"
        )

        for sv in raw_spec.semantic_views:
            with st.expander(f"**{sv.name}** — Domain: {sv.domain}"):
                st.write(f"**Base tables:** {', '.join(sv.base_tables)}")
                if sv.joins:
                    st.write("**Joins:**")
                    for j in sv.joins:
                        st.write(
                            f"  - `{j.table}` → `{j.join_to}` on `{j.left_key}` = `{j.right_key}` ({j.join_type})"
                        )
                if sv.description:
                    st.write(f"**Description:** {sv.description}")

    except CSVParseError as e:
        st.error(f"CSV Parse Error: {e}")

if uploaded_excel is not None:
    st.session_state["excel_bytes"] = uploaded_excel.getvalue()
    st.session_state["excel_filename"] = uploaded_excel.name
    st.info(f"Excel metadata loaded: **{uploaded_excel.name}**")

if "raw_spec" in st.session_state:
    st.divider()
    st.markdown("**Next step:**")
    st.page_link("pages/2_preview.py", label="Preview →", icon="👁️")
