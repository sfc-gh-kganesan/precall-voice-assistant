import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent import deploy_agent
from core.config import get_config
from core.describe import describe, describe_columns
from core.enrich import to_yaml as enrich_to_yaml
from core.generate_sql import generate_sql
from core.snowflake.exec import connect, execute
from core.storage import save_deployment
from core.transform import to_yaml as transform_to_yaml
from core.transform import transform
from registry.column_registry import sync_column_registry
from registry.sv_registry import sync_sv_registry

st.set_page_config(page_title="Deploy | Semantic Forge", layout="wide")
st.title("🚀 Deploy Semantic Views")

if "enriched_spec" not in st.session_state:
    st.warning("No enriched data. Please complete the Preview step first.")
    st.page_link("pages/2_preview.py", label="Preview →", icon="👁️")
    st.stop()

config = get_config()
enriched = st.session_state["enriched_spec"]

version_tag = f"v{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
st.sidebar.markdown(f"**Version:** `{version_tag}`")
st.sidebar.markdown(f"**Target:** `{config.target_database}.{config.target_schema}`")
st.sidebar.markdown(f"**Model:** `{config.cortex_model}`")

step1, step2, step3, step4, step5, step6 = st.tabs(
    ["1. Transform", "2. Describe", "3. Generate SQL", "4. Execute", "5. Registry", "6. Agent"]
)

with step1:
    st.subheader("Transform enriched spec → semantic assets")
    if "semantic_assets" not in st.session_state:
        if st.button("Run Transform", type="primary"):
            with st.spinner("Transforming..."):
                try:
                    enriched_yaml = enrich_to_yaml(enriched)
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        f.write(enriched_yaml)
                        tmp_path = f.name
                    assets_spec = transform(tmp_path)
                    st.session_state["semantic_assets"] = assets_spec
                    st.session_state["semantic_assets_path"] = tmp_path
                    st.rerun()
                except Exception as e:
                    st.error(f"Transform failed: {e}")
    else:
        assets = st.session_state["semantic_assets"]
        st.success(f"Transformed {len(assets.semantic_assets)} semantic asset(s)")
        for asset in assets.semantic_assets:
            with st.expander(f"**{asset.name}** — {len(asset.tables)} tables"):
                st.write(f"Domains: {', '.join(asset.domains)}")
                st.write(f"Relationships: {len(asset.relationships)}")

with step2:
    st.subheader("Generate LLM descriptions via Cortex COMPLETE")
    if "semantic_assets" not in st.session_state:
        st.info("Run Transform first.")
    elif "described_assets" not in st.session_state:
        col_a, col_b = st.columns(2)
        with col_a:
            gen_sv_desc = st.checkbox("Generate SV descriptions", value=True)
        with col_b:
            gen_col_desc = st.checkbox("Generate column descriptions", value=True)
        if st.button("Generate Descriptions", type="primary"):
            with st.spinner("Calling Cortex COMPLETE..."):
                try:
                    assets_yaml = transform_to_yaml(st.session_state["semantic_assets"])
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        f.write(assets_yaml)
                        assets_path = f.name
                    session = st.session_state.get("session") or connect(config.connection_name)
                    described = yaml.safe_load(assets_yaml)
                    if gen_sv_desc:
                        described = describe(
                            assets_path, session=session, model=config.cortex_model
                        )
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".yaml", delete=False
                        ) as f:
                            yaml.dump(described, f)
                            assets_path = f.name
                    if gen_col_desc:
                        described = describe_columns(
                            assets_path, session=session, model=config.cortex_model
                        )
                    st.session_state["described_assets"] = described
                    st.rerun()
                except Exception as e:
                    st.error(f"Description generation failed: {e}")
    else:
        described = st.session_state["described_assets"]
        st.success("Descriptions generated")
        for asset in described.get("semantic_assets", []):
            with st.expander(f"**{asset['name']}**"):
                st.write(asset.get("description", ""))

with step3:
    st.subheader("Generate SQL statements")
    if "described_assets" not in st.session_state:
        st.info("Run Describe first.")
    elif "generated_sql" not in st.session_state:
        if st.button("Generate SQL", type="primary"):
            with st.spinner("Generating SQL..."):
                try:
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        yaml.dump(st.session_state["described_assets"], f)
                        assets_path = f.name
                    sql = generate_sql(assets_path)
                    st.session_state["generated_sql"] = sql
                    st.rerun()
                except Exception as e:
                    st.error(f"SQL generation failed: {e}")
    else:
        sql = st.session_state["generated_sql"]
        st.success("SQL generated")
        st.code(sql, language="sql")

with step4:
    st.subheader("Execute SQL against Snowflake")
    if "generated_sql" not in st.session_state:
        st.info("Generate SQL first.")
    else:
        sql = st.session_state["generated_sql"]
        st.warning("This will create/replace semantic views in the target schema.")
        if st.button("Deploy to Snowflake", type="primary"):
            with st.spinner("Deploying..."):
                try:
                    session = st.session_state.get("session") or connect(config.connection_name)
                    blocks = []
                    current = []
                    in_dollar = False
                    for line in sql.splitlines():
                        stripped = line.strip()
                        if "$$" in stripped:
                            in_dollar = not in_dollar
                        current.append(line)
                        if not in_dollar and stripped.endswith(";"):
                            blocks.append("\n".join(current))
                            current = []
                    if current:
                        leftover = "\n".join(current).strip()
                        if leftover:
                            blocks.append(leftover)
                    statements = [
                        b.strip()
                        for b in blocks
                        if b.strip() and "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in b
                    ]
                    results = []
                    deploy_errors = []
                    for stmt in statements:
                        if "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in stmt:
                            try:
                                result = execute(session, stmt)
                                results.append(result)
                            except Exception as ex:
                                deploy_errors.append(str(ex))
                    st.session_state["deploy_results"] = results
                    deployment_id = save_deployment(
                        session=session,
                        semantic_assets=st.session_state["described_assets"],
                        model_used=config.cortex_model,
                        connection_name=config.connection_name,
                        version_tag=version_tag,
                    )
                    st.session_state["deployment_id"] = deployment_id
                    st.session_state["version_tag"] = version_tag
                    if deploy_errors:
                        st.warning(f"Deployed with {len(deploy_errors)} error(s):")
                        for err in deploy_errors:
                            st.error(err)
                    st.success(
                        f"Deployed {len(results)} SV(s). Version: `{version_tag}` | ID: `{deployment_id}`"
                    )
                except Exception as e:
                    st.error(f"Deployment failed: {e}")

with step5:
    st.subheader("Sync to Cortex Search Registry")
    if "deployment_id" not in st.session_state:
        st.info("Deploy first.")
    else:
        col_sv, col_col = st.columns(2)
        with col_sv:
            sync_sv = st.checkbox("Sync SV metadata", value=True)
        with col_col:
            sync_col = st.checkbox("Sync column metadata", value=True)
        if st.button("Sync Registry", type="primary"):
            with st.spinner("Syncing to registry..."):
                try:
                    session = st.session_state.get("session") or connect(config.connection_name)
                    raw_spec = st.session_state["raw_spec"]
                    sv_config = {sv.name: sv.domain for sv in raw_spec.semantic_views}
                    if sync_sv:
                        sv_result = sync_sv_registry(
                            session=session,
                            sv_config=sv_config,
                            database=config.target_database,
                            schema=config.target_schema,
                            warehouse=config.warehouse,
                            table_name=config.registry.sv_table,
                            service_name=config.registry.sv_service,
                        )
                        st.write("**SV Registry:**", sv_result)
                    if sync_col:
                        col_result = sync_column_registry(
                            session=session,
                            sv_config=sv_config,
                            database=config.target_database,
                            schema=config.target_schema,
                            warehouse=config.warehouse,
                            table_name=config.registry.column_table,
                            service_name=config.registry.column_service,
                        )
                        st.write("**Column Registry:**", col_result)
                    st.success("Registry sync complete!")
                    st.session_state["registry_synced"] = True
                except Exception as e:
                    st.error(f"Registry sync failed: {e}")

with step6:
    st.subheader("Deploy Baseline Cortex Agent")
    if "registry_synced" not in st.session_state and "deployment_id" not in st.session_state:
        st.info("Complete Deploy and Registry Sync first.")
    else:
        agent_fqn = f"{config.target_database}.{config.target_schema}.{config.agent.name}"
        st.markdown(f"""
**Agent:** `{agent_fqn}`
**Tools:** `{config.agent.retrieval_tool}`, `{config.agent.sql_gen_tool}`, `{config.agent.sql_exec_tool}`
**Model:** `{config.cortex_model}` | **Warehouse:** `{config.warehouse}`
        """)
        st.markdown(
            "This will create 3 stored procedures (retrieval, sql_gen, sql_exec) and 1 Cortex Agent."
        )
        if st.button("Deploy Agent", type="primary"):
            with st.spinner("Deploying agent and tools..."):
                try:
                    session = st.session_state.get("session") or connect(config.connection_name)
                    result = deploy_agent(
                        session=session,
                        database=config.target_database,
                        schema=config.target_schema,
                        warehouse=config.warehouse,
                        model=config.cortex_model,
                        search_service=config.registry.sv_service,
                        sv_table=config.registry.sv_table,
                        agent_name=config.agent.name,
                        retrieval_tool=config.agent.retrieval_tool,
                        sql_gen_tool=config.agent.sql_gen_tool,
                        sql_exec_tool=config.agent.sql_exec_tool,
                    )
                    if result.success:
                        st.success(f"Agent deployed: `{agent_fqn}`")
                        st.session_state["agent_deployed"] = True
                        st.session_state["agent_fqn"] = agent_fqn
                    else:
                        for err in result.errors or []:
                            st.error(err)
                    status = []
                    if result.retrieval_tool:
                        status.append(f"✅ {config.agent.retrieval_tool}")
                    if result.sql_gen_tool:
                        status.append(f"✅ {config.agent.sql_gen_tool}")
                    if result.sql_exec_tool:
                        status.append(f"✅ {config.agent.sql_exec_tool}")
                    if result.agent:
                        status.append(f"✅ {config.agent.name}")
                    st.markdown("\n".join(status))
                except Exception as e:
                    st.error(f"Agent deployment failed: {e}")
        if st.session_state.get("agent_deployed"):
            st.divider()
            st.markdown("### Next Steps")
            st.markdown(
                "- Test in [Snowsight](https://app.snowflake.com) → **AI & ML → Cortex Agent**"
            )
            st.markdown("- Or go to the **Test** page to try it here")
            st.page_link("pages/4_test.py", label="Test Agent →", icon="🧪")
