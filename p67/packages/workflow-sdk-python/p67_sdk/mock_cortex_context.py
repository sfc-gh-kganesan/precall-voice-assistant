"""
mock_cortex_context.py — Mock CortexContext for local testing.

Uses a local Snowflake connection (user/password) instead of SPCS OAuth.
Stubs out human_action() to return immediately.
Logs all method calls for test assertions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from p67_sdk.automation_context import AutomationContext

logger = logging.getLogger("mock_cortex_context")


@dataclass
class MethodCall:
    """Record of a method call on MockCortexContext."""

    method: str
    args: tuple
    kwargs: dict
    result: Any = None


class MockCortexContext(AutomationContext):
    """Test double for CortexContext that uses a local Snowflake connection.

    Usage::

        ctx = MockCortexContext(
            account="myaccount",
            user="myuser",
            password="mypass",
            database="mydb",
            schema="myschema",
        )
        # Use ctx in your automation code for local testing
        rows = ctx.query("SELECT 1 AS x")

        # Assert calls were made
        assert ctx.call_log[0].method == "query"
    """

    def __init__(
        self,
        *,
        account: str = "",
        user: str = "",
        password: str = "",
        database: str = "",
        schema: str = "",
        warehouse: str = "",
        role: str = "",
        secrets: dict[str, str] | None = None,
        human_action_responses: dict[str, dict] | None = None,
    ) -> None:
        self._account = account
        self._user = user
        self._password = password
        self._database = database
        self._schema = schema
        self._warehouse = warehouse
        self._role = role
        self._secrets = secrets or {}
        self._human_action_responses = human_action_responses or {}
        self._human_action_call_count = 0
        self._output_value: Any = None
        self.call_log: list[MethodCall] = []

    def _log_call(self, method: str, *args: Any, **kwargs: Any) -> MethodCall:
        call = MethodCall(method=method, args=args, kwargs=kwargs)
        self.call_log.append(call)
        logger.debug("MockCortexContext.%s(%s, %s)", method, args, kwargs)
        return call

    def _get_connection(self):
        import snowflake.connector

        return snowflake.connector.connect(
            account=self._account,
            user=self._user,
            password=self._password,
            database=self._database,
            schema=self._schema,
            warehouse=self._warehouse,
            role=self._role,
        )

    def query(self, sql: str, bindings: dict[str, Any] | None = None) -> list[dict]:
        call = self._log_call("query", sql, bindings)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, bindings or {})
            columns = [desc[0] for desc in cur.description] if cur.description else []
            result = [dict(zip(columns, row)) for row in cur.fetchall()]
            call.result = result
            return result
        finally:
            conn.close()

    def query_df(self, sql: str, bindings: dict[str, Any] | None = None):
        call = self._log_call("query_df", sql, bindings)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, bindings or {})
            result = cur.fetch_pandas_all()
            call.result = result
            return result
        finally:
            conn.close()

    def complete(self, model: str, prompt: str, **kwargs: Any) -> str | dict:
        call = self._log_call("complete", model, prompt, **kwargs)
        # Use actual Cortex COMPLETE if connected to Snowflake
        options_json = json.dumps(kwargs) if kwargs else "{}"
        rows = self.query(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(:1, :2, PARSE_JSON(:3)) AS result",
            {"1": model, "2": prompt, "3": options_json},
        )
        result = rows[0].get("RESULT", "") if rows else ""
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            pass
        call.result = result
        return result

    def search(self, service: str, query: str, limit: int = 10) -> list[dict]:
        call = self._log_call("search", service, query, limit)
        result = self.query(
            f"SELECT * FROM TABLE(CORTEX_SEARCH_PREVIEW('{service}', :1, :2))",
            {"1": query, "2": limit},
        )
        call.result = result
        return result

    def analyst(self, semantic_view: str, question: str) -> dict:
        call = self._log_call("analyst", semantic_view, question)
        rows = self.query(
            "SELECT SNOWFLAKE.CORTEX.ANALYST(:1, :2) AS result",
            {"1": semantic_view, "2": question},
        )
        result = json.loads(rows[0].get("RESULT", "{}")) if rows else {}
        call.result = result
        return result

    def http(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict | str | None = None,
    ) -> dict:
        call = self._log_call("http", method, url, headers, body)
        # For local testing, use Python requests directly
        import requests

        resp = requests.request(
            method=method,
            url=url,
            headers=headers or {},
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, str) else None,
        )
        result = {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text,
        }
        call.result = result
        return result

    def agent(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
        timeout_seconds: int = 120,
    ) -> str:
        call = self._log_call("agent", agent_name, message, thread_id, timeout_seconds)
        rows = self.query(
            "SELECT SNOWFLAKE.CORTEX.AGENT(:1, :2, :3, :4) AS result",
            {"1": agent_name, "2": message, "3": thread_id or "", "4": timeout_seconds},
        )
        result = str(rows[0].get("RESULT", "")) if rows else ""
        call.result = result
        return result

    def automation(
        self,
        automation_name: str,
        input_data: dict | str,
        await_result: bool = True,
    ) -> str | dict:
        call = self._log_call("automation", automation_name, input_data, await_result)
        # For local testing, just log and return empty
        logger.warning(
            "MockCortexContext.automation() stub — sub-automation calls "
            "not supported in local testing"
        )
        call.result = {}
        return {}

    def human_action(
        self,
        prompt: str,
        payload: dict | None = None,
        notify: dict | None = None,
        timeout_hours: int = 24,
    ) -> dict:
        """Mock human_action returns immediately with preconfigured response."""
        call = self._log_call("human_action", prompt, payload, notify, timeout_hours)
        self._human_action_call_count += 1
        key = str(self._human_action_call_count)
        result = self._human_action_responses.get(key, {"approved": True})
        call.result = result
        logger.info(
            "MockCortexContext.human_action() returning preconfigured response "
            "for call #%s: %s",
            key,
            result,
        )
        return result

    def secret(self, name: str) -> str:
        call = self._log_call("secret", name)
        if name not in self._secrets:
            raise ValueError(
                f"Secret '{name}' not found in MockCortexContext. "
                "Pass secrets={'name': 'value'} to constructor."
            )
        result = self._secrets[name]
        call.result = result
        return result

    def emit(self, event: str, data: dict | None = None) -> None:
        self._log_call("emit", event, data)
        logger.info("Mock event: %s data=%s", event, data or {})

    def output(self, value: Any) -> None:
        self._log_call("output", value)
        self._output_value = value
