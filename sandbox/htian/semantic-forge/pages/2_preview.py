import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_config
from core.enrich import enrich
from core.parse_csv import to_yaml as raw_to_yaml
from core.snowflake.exec import connect

st.set_page_config(page_title="Preview | Semantic Forge", layout="wide")
st.title("👁️ Preview Data Model")

if "raw_spec" not in st.session_state:
    st.warning("No config uploaded. Please upload a CSV first.")
    st.page_link("pages/1_upload.py", label="Upload →", icon="📤")
    st.stop()

raw_spec = st.session_state["raw_spec"]
config = get_config()

tab_mapping, tab_columns, tab_graph = st.tabs(["SV Mapping", "Column Inventory", "Data Graph"])

with tab_mapping:
    st.subheader("Semantic View Mapping")
    import pandas as pd

    rows = []
    for sv in raw_spec.semantic_views:
        all_tables = list(sv.base_tables)
        for j in sv.joins:
            all_tables.append(j.table)
        rows.append(
            {
                "Semantic View": sv.name,
                "Domain": sv.domain,
                "Base Tables": ", ".join(sv.base_tables),
                "Join Tables": ", ".join(j.table for j in sv.joins),
                "Total Tables": len(all_tables),
                "Joins": len(sv.joins),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab_columns:
    st.subheader("Column Inventory")

    if "enriched_spec" not in st.session_state:
        if st.button("Enrich from Snowflake", type="primary"):
            with st.spinner("Connecting to Snowflake and fetching table metadata..."):
                try:
                    raw_yaml = raw_to_yaml(raw_spec)
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        f.write(raw_yaml)
                        tmp_path = f.name

                    excel_path = None
                    if "excel_bytes" in st.session_state:
                        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as ef:
                            ef.write(st.session_state["excel_bytes"])
                            excel_path = ef.name

                    session = connect(config.connection_name)
                    enriched = enrich(
                        raw_spec_path=tmp_path,
                        source_database=config.source_database,
                        source_schema=config.source_schema,
                        target_database=config.target_database,
                        target_schema=config.target_schema,
                        session=session,
                        excel_metadata_path=excel_path,
                    )
                    st.session_state["enriched_spec"] = enriched
                    st.session_state["session"] = session
                    st.rerun()
                except Exception as e:
                    st.error(f"Enrichment failed: {e}")
    else:
        enriched = st.session_state["enriched_spec"]
        for table_name, table_spec in enriched.tables.items():
            with st.expander(f"**{table_name}** ({len(table_spec.columns)} columns)"):
                col_rows = []
                for col in table_spec.columns:
                    col_rows.append(
                        {
                            "Column": col.name,
                            "Type": col.type,
                            "Description": col.comment or "",
                            "Synonyms": ", ".join(col.synonyms) if col.synonyms else "",
                            "Samples": ", ".join(col.sample_values[:3])
                            if col.sample_values
                            else "",
                        }
                    )
                st.dataframe(pd.DataFrame(col_rows), use_container_width=True, hide_index=True)

with tab_graph:
    st.subheader("Interactive Data Graph")
    if "enriched_spec" not in st.session_state:
        st.info("Click **Enrich from Snowflake** in the Column Inventory tab first.")
    else:
        enriched = st.session_state["enriched_spec"]
        from streamlit_flow import streamlit_flow
        from streamlit_flow.state import StreamlitFlowState

        from components.graph import DOMAIN_COLORS, build_graph

        sv_names = [sv.name for sv in enriched.semantic_views]

        col_mode, col_sv, col_spacer = st.columns([1, 1, 1])
        with col_mode:
            view_mode = st.radio(
                "View Mode",
                ["All Tables", "Semantic View Focus"],
                horizontal=True,
            )
        focus_sv = None
        if view_mode == "Semantic View Focus":
            with col_sv:
                focus_sv = st.selectbox("Select Semantic View", options=sv_names, index=0)

        mode = "focus" if view_mode == "Semantic View Focus" else "all"
        sv_dicts = [asdict(sv) for sv in enriched.semantic_views]
        table_dicts = {k: asdict(v) for k, v in enriched.tables.items()}
        flow_state, layout = build_graph(sv_dicts, table_dicts, mode=mode, focus_sv=focus_sv)

        graph_key = f"sv_graph_{mode}_{focus_sv or 'all'}_v2"
        state_key = f"_state_{graph_key}"
        if state_key not in st.session_state or not isinstance(
            st.session_state[state_key], StreamlitFlowState
        ):
            st.session_state[state_key] = flow_state

        col_graph, col_legend = st.columns([3, 1])
        with col_graph:
            if flow_state.nodes:
                result = streamlit_flow(
                    graph_key,
                    st.session_state[state_key],
                    layout=layout,
                    fit_view=True,
                    height=850,
                    show_minimap=True,
                    show_controls=True,
                    hide_watermark=True,
                    get_node_on_click=True,
                    get_edge_on_click=True,
                    pan_on_drag=True,
                    allow_zoom=True,
                    min_zoom=0.1,
                )

                if isinstance(result, StreamlitFlowState):
                    st.session_state[state_key] = result

                clicked = getattr(st.session_state[state_key], "selected_id", None)
                if clicked and clicked in table_dicts:
                    tdata = table_dicts[clicked]
                    cols = tdata.get("columns", [])
                    with st.expander(f"Table: **{clicked}**", expanded=True):
                        meta_parts = [f"**Columns:** {len(cols)}"]
                        if tdata.get("row_count") is not None:
                            meta_parts.append(f"**Rows:** {tdata['row_count']:,}")
                        if tdata.get("primary_keys"):
                            meta_parts.append(f"**PK:** {', '.join(tdata['primary_keys'])}")
                        if tdata.get("foreign_keys"):
                            meta_parts.append(f"**FK:** {', '.join(tdata['foreign_keys'])}")
                        st.markdown(" · ".join(meta_parts))
            else:
                st.warning("No graph data available.")

        with col_legend:
            with st.expander("Legend", expanded=True):
                st.markdown("**Node Styles**", unsafe_allow_html=True)
                st.markdown(
                    "<span style='display:inline-block;width:14px;height:14px;border:3px solid #333;border-radius:4px;background:#fff;margin-right:4px;vertical-align:middle'></span> Semantic View<br>"
                    "<span style='display:inline-block;width:14px;height:14px;border:2px solid #4A90D9;border-radius:3px;background:#4A90D9;margin-right:4px;vertical-align:middle'></span> Base Table<br>"
                    "<span style='display:inline-block;width:14px;height:14px;border:2px dashed #4A90D9;border-radius:3px;background:#4A90D922;margin-right:4px;vertical-align:middle'></span> Dimension Table",
                    unsafe_allow_html=True,
                )
                st.markdown("**Domains**", unsafe_allow_html=True)
                domain_html = "<br>".join(
                    f"<span style='color:{color}'>&#9679;</span> {domain.title()}"
                    for domain, color in DOMAIN_COLORS.items()
                    if domain != "default"
                )
                st.markdown(domain_html, unsafe_allow_html=True)
