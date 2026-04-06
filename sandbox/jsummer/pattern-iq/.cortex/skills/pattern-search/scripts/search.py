#!/usr/bin/env python3
"""
search.py -- Query the Pattern Marketplace Agent for reusable patterns.

Sends a natural-language query to the PATTERN_MARKETPLACE_AGENT Cortex Agent
via the :run REST API and returns a structured JSON response.

Usage:
    python search.py --query "patterns for building a RAG chatbot" [--context "building a Streamlit app"] [--connection aifde]
"""

import argparse
import json
import os
import sys

import requests
from snowflake.connector import connect


AGENT_DATABASE = "PATTERN_IQ"
AGENT_SCHEMA = "PUBLIC"
AGENT_NAME = "PATTERN_MARKETPLACE_AGENT"


def get_agent_url(host: str) -> str:
    """Build the Agent :run endpoint URL."""
    base = host if host.startswith("https://") else f"https://{host}"
    return (
        f"{base}/api/v2/databases/{AGENT_DATABASE}"
        f"/schemas/{AGENT_SCHEMA}"
        f"/agents/{AGENT_NAME}:run"
    )


def build_message(query: str, context: str | None = None) -> str:
    """Combine optional context with the user query."""
    if context:
        return f"Context: {context}\n\nQuery: {query}"
    return query


def call_agent(host: str, token: str, query: str, context: str | None = None) -> dict:
    """Send a non-streaming request to the Cortex Agent :run endpoint."""
    url = get_agent_url(host)
    message_text = build_message(query, context)

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message_text}
                ],
            }
        ],
        "stream": False,
    }

    headers = {
        "Authorization": f'Snowflake Token="{token}"',
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()


def parse_response(raw: dict) -> dict:
    """Extract text, citations, and metadata from the agent response."""
    text_parts = []
    citations = []

    message = raw.get("message", raw)
    content = message.get("content", [])

    for item in content:
        item_type = item.get("type", "")
        if item_type == "text":
            text_parts.append(item.get("text", ""))
        elif item_type == "tool_results":
            tool_content = item.get("tool_results", {}).get("content", [])
            for tc in tool_content:
                if tc.get("type") == "json":
                    json_data = tc.get("json", {})
                    if "text" in json_data:
                        text_parts.append(json_data["text"])
                    if "searchResults" in json_data:
                        for sr in json_data["searchResults"]:
                            citations.append(sr)
                    if "results" in json_data:
                        for r in json_data["results"]:
                            citations.append(r)

    request_id = raw.get("request_id", "")

    return {
        "text": "\n\n".join(text_parts),
        "citations": citations,
        "request_id": request_id,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search the pattern catalog via the Cortex Agent API"
    )
    parser.add_argument("--query", required=True, help="Natural-language search query")
    parser.add_argument(
        "--context",
        default=None,
        help="Optional context about what you are building",
    )
    parser.add_argument("--connection", default=None, help="Snowflake connection name")
    args = parser.parse_args()

    conn_name = args.connection or os.getenv("SNOWFLAKE_CONNECTION_NAME") or "default"

    conn = connect(connection_name=conn_name)
    try:
        token = conn.rest.token
        host = conn.host

        raw = call_agent(host, token, args.query, args.context)
        result = parse_response(raw)
        print(json.dumps(result, indent=2))
    except requests.HTTPError as exc:
        print(
            json.dumps({"error": f"Agent request failed: {exc}", "status_code": exc.response.status_code}),
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
