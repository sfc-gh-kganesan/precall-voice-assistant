import streamlit as st

st.set_page_config(
    page_title="Semantic Forge",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Semantic Forge")
st.markdown("Bootstrap semantic views for Snowflake AI Agent engagements.")

st.sidebar.success("Select a page above.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.page_link("pages/1_upload.py", label="Upload", icon="📤")
with col2:
    st.page_link("pages/2_preview.py", label="Preview", icon="👁️")
with col3:
    st.page_link("pages/3_deploy.py", label="Deploy", icon="🚀")
with col4:
    st.page_link("pages/4_test.py", label="Test", icon="🧪")

st.divider()

st.markdown("""
### Workflow
1. **Upload** — Upload a CSV config defining semantic views, tables, and joins
2. **Preview** — Explore the data model: SV mapping, column inventory, interactive graph
3. **Deploy** — Generate descriptions, create semantic views, sync to registry
4. **Test** — Review sample questions and link to Cortex Agent
""")
