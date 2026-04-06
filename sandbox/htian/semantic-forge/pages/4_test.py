import json
import sys
from pathlib import Path

import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_config
from core.snowflake.exec import connect

st.set_page_config(page_title="Test | Semantic Forge", layout="wide")
st.title("🧪 Test Agent")

config = get_config()
agent_fqn = f"{config.target_database}.{config.target_schema}.{config.agent.name}"

st.sidebar.markdown(f"**Agent:** `{agent_fqn}`")
st.sidebar.markdown(f"**Model:** `{config.cortex_model}`")
st.sidebar.markdown(f"**Warehouse:** `{config.warehouse}`")

if "test_messages" not in st.session_state:
    st.session_state["test_messages"] = []

if "raw_spec" in st.session_state:
    raw_spec = st.session_state["raw_spec"]
    with st.expander("Available Domains & SVs"):
        for sv in raw_spec.semantic_views:
            st.markdown(f"- **{sv.domain}**: `{sv.name}` ({', '.join(sv.base_tables[:3])})")


def call_agent(session, database: str, schema: str, agent_name: str, question: str) -> str:
    conn = session._conn._conn
    token = conn.rest.token
    host = conn.host

    url = f"https://{host}/api/v2/databases/{database}/schemas/{schema}/agents/{agent_name}:run"
    headers = {
        "Authorization": f'Snowflake Token="{token}"',
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
        "stream": False,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    message = data.get("message", {})
    content_parts = message.get("content", [])
    text_parts = [p.get("text", "") for p in content_parts if p.get("type") == "text"]
    return "\n".join(text_parts) if text_parts else json.dumps(data, indent=2)


st.subheader("Ask a Question")

question = st.text_input(
    "Enter a business question:", placeholder="e.g., How many clients are in each segment?"
)

if st.button("Run", type="primary") and question:
    with st.spinner("Agent is thinking..."):
        try:
            session = st.session_state.get("session") or connect(config.connection_name)
            answer = call_agent(
                session,
                config.target_database,
                config.target_schema,
                config.agent.name,
                question,
            )
            st.session_state["test_messages"].append({"question": question, "answer": answer})
        except Exception as e:
            st.error(f"Agent call failed: {e}")
            st.session_state["test_messages"].append({"question": question, "error": str(e)})

if st.session_state["test_messages"]:
    st.divider()
    st.subheader("Conversation")
    for msg in reversed(st.session_state["test_messages"]):
        st.markdown(f"**Q:** {msg['question']}")
        if "error" in msg:
            st.error(msg["error"])
        else:
            st.markdown(msg["answer"])
        st.divider()

if st.button("Clear History"):
    st.session_state["test_messages"] = []
    st.rerun()
