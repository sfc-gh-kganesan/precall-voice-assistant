"""
cortex_context.py — CortexContext: SPCS/GS backend for Cortex Automations.

Provides the ``ctx`` object that automation code uses to interact with
Snowflake services from inside the SPCS runner container.  This is the
production backend of the ``AutomationContext`` ABC; for local development
see ``local_backend.LocalBackend``.

**OAuth token refresh** (C12 findings):
  The SPCS platform mounts a short-lived OAuth token at
  ``/snowflake/session/token``.  GS ``ResourceSetReconcilerBG`` rotates this
  file approximately every 5 minutes.  The token is intentionally re-read on
  *every* ``_get_connection()`` call; caching it would cause auth failures
  after the first rotation.  No connection pool is maintained for the same
  reason — each SQL call gets a fresh connection that reads the current token.

**EXECUTE AS OWNER semantics**:
  The OAuth token is issued for the automation's service identity, which runs
  under the definer's-rights role (EXECUTE AS OWNER).  All SQL executed
  through ``CortexContext`` inherits this role; user code cannot escalate
  privileges beyond what the automation owner has been granted.

**Secret file mounts**:
  Automation secrets are mounted by SPCS as plain-text files under
  ``/snowflake/secrets/<name>``, where ``<name>`` matches the key defined in
  the automation's ``[secrets]`` configuration.  Reading from files rather
  than environment variables is a security requirement (C9): environment
  variables are visible to child processes and may appear in crash dumps.

**HITL checkpoint-and-release**:
  ``human_action()`` does *not* block in-process.  It raises
  ``HumanActionInterrupt``, which unwinds the call stack back to the runner's
  Go supervisor.  The supervisor checkpoints the full LangGraph state to
  Hybrid Tables, sets the run status to ``WAITING_FOR_HUMAN`` in
  ``_cortex_automation_run_history``, and terminates the SPCS job (zero idle
  cost).  When a human submits a response, GS cold-starts a new SPCS job,
  loads the checkpoint, injects the response into the graph state, and resumes
  execution from the interrupted node.  Cold-start latency is typically 30–90 s.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from p67_sdk.automation_context import AutomationContext

logger = logging.getLogger("cortex_context")

# SPCS environment defaults
DEFAULT_TOKEN_PATH = "/snowflake/session/token"
DEFAULT_SECRETS_DIR = "/snowflake/secrets"


class CortexContext(AutomationContext):
    """SPCS/GS implementation of ``AutomationContext``.

    All SQL executes via a fresh ``snowflake.connector`` connection per call,
    re-reading the OAuth token file each time (see module docstring).  This
    class is instantiated by ``context_factory.create_context()`` when
    ``SNOWFLAKE_HOST`` is set, and should not be constructed directly in
    user automation code.

    Usage inside a LangGraph node::

        from cortex_automations import CortexContext

        ctx = CortexContext()
        rows = ctx.query("SELECT * FROM my_table WHERE id = :1", {"1": some_id})
        summary = ctx.complete("mistral-large2", "Summarize: " + text)
    """

    def __init__(
        self,
        *,
        account: str | None = None,
        host: str | None = None,
        token_path: str | None = None,
        secrets_dir: str | None = None,
    ) -> None:
        self._account = account or os.environ.get("SNOWFLAKE_ACCOUNT", "")
        self._host = host or os.environ.get("SNOWFLAKE_HOST", "")
        self._token_path = token_path or os.environ.get(
            "SNOWFLAKE_TOKEN_PATH", DEFAULT_TOKEN_PATH
        )
        self._secrets_dir = secrets_dir or os.environ.get(
            "SNOWFLAKE_SECRETS_DIR", DEFAULT_SECRETS_DIR
        )
        self._run_id = os.environ.get("AUTOMATION_RUN_ID", "")
        self._automation_name = os.environ.get("AUTOMATION_NAME", "")
        self._output_value: Any = None

    def _read_token(self) -> str:
        """Read the current OAuth token from the SPCS-mounted file.

        IMPORTANT: Must re-read on every connection. The token file is
        refreshed by GS ResourceSetReconcilerBG every 5 minutes (C12).
        Caching the token would cause auth failures after expiry.
        """
        with open(self._token_path, "r") as f:
            return f.read().strip()

    def _get_connection(self):
        """Create a fresh Snowflake connection with the current OAuth token.

        A new connection is created on every call (no pool) so that the
        most-recently-rotated token is always used.  The connection runs under
        the automation's EXECUTE AS OWNER role; the caller's session role is
        not inherited.

        Returns:
            An open ``snowflake.connector.SnowflakeConnection``.  Caller is
            responsible for closing it (``conn.close()``).
        """
        import snowflake.connector

        token = self._read_token()
        return snowflake.connector.connect(
            account=self._account,
            host=self._host,
            authenticator="oauth",
            token=token,
        )

    # ---- Data Access ----

    def query(self, sql: str, bindings: dict[str, Any] | None = None) -> list[dict]:
        """Execute a SQL query and return results as a list of dicts.

        Args:
            sql: SQL query string. Use :1, :2 for positional bindings.
            bindings: Optional parameter bindings.

        Returns:
            List of row dicts with column names as keys.
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, bindings or {})
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def query_df(self, sql: str, bindings: dict[str, Any] | None = None):
        """Execute a SQL query and return results as a pandas DataFrame.

        Args:
            sql: SQL query string.
            bindings: Optional parameter bindings.

        Returns:
            pandas.DataFrame with query results.
        """
        import pandas as pd

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, bindings or {})
            return cur.fetch_pandas_all()
        finally:
            conn.close()

    # ---- Cortex AI ----

    def complete(
        self, model: str, prompt: str, **kwargs: Any
    ) -> str | dict:
        """Call Cortex COMPLETE() for LLM inference.

        Args:
            model: Model name (e.g., 'mistral-large2', 'llama3.1-70b').
            prompt: The prompt string.
            **kwargs: Additional options (temperature, max_tokens, etc.).

        Returns:
            String response or dict if structured output requested.
        """
        options_json = json.dumps(kwargs) if kwargs else "{}"
        sql = (
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(:1, :2, PARSE_JSON(:3)) AS result"
        )
        rows = self.query(sql, {"1": model, "2": prompt, "3": options_json})
        if rows:
            result = rows[0].get("RESULT", "")
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return str(result)
        return ""

    def search(
        self, service: str, query: str, limit: int = 10
    ) -> list[dict]:
        """Call Cortex Search service.

        Args:
            service: FQN of the Cortex Search service.
            query: Search query string.
            limit: Max results to return.

        Returns:
            List of search result dicts.
        """
        sql = f"SELECT * FROM TABLE(CORTEX_SEARCH_PREVIEW('{service}', :1, :2))"
        return self.query(sql, {"1": query, "2": limit})

    def analyst(self, semantic_view: str, question: str) -> dict:
        """Call Cortex Analyst with a natural language question.

        Args:
            semantic_view: FQN of the semantic view.
            question: Natural language question.

        Returns:
            Dict with generated SQL and results.
        """
        sql = (
            "SELECT SNOWFLAKE.CORTEX.ANALYST(:1, :2) AS result"
        )
        rows = self.query(sql, {"1": semantic_view, "2": question})
        if rows:
            result = rows[0].get("RESULT", "{}")
            return json.loads(result) if isinstance(result, str) else result
        return {}

    # ---- External Access ----

    def http(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict | str | None = None,
    ) -> dict:
        """Make an HTTP request via external access integration.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Target URL.
            headers: Optional request headers.
            body: Optional request body (dict or string).

        Returns:
            Dict with status, headers, and body from response.
        """
        headers_json = json.dumps(headers or {})
        body_json = json.dumps(body) if isinstance(body, dict) else (body or "")
        sql = (
            "SELECT SNOWFLAKE.CORTEX.HTTP_REQUEST(:1, :2, "
            "PARSE_JSON(:3), :4) AS result"
        )
        rows = self.query(
            sql, {"1": method, "2": url, "3": headers_json, "4": body_json}
        )
        if rows:
            result = rows[0].get("RESULT", "{}")
            return json.loads(result) if isinstance(result, str) else result
        return {}

    # ---- Cross-automation ----

    def agent(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
        timeout_seconds: int = 120,
    ) -> str:
        """Call a Cortex Agent.

        Args:
            agent_name: FQN of the Cortex Agent.
            message: User message to send.
            thread_id: Optional thread ID for conversation continuity.
            timeout_seconds: Timeout for the agent call.

        Returns:
            Agent response string.
        """
        sql = (
            "SELECT SNOWFLAKE.CORTEX.AGENT(:1, :2, :3, :4) AS result"
        )
        rows = self.query(
            sql,
            {"1": agent_name, "2": message, "3": thread_id or "", "4": timeout_seconds},
        )
        return str(rows[0].get("RESULT", "")) if rows else ""

    def automation(
        self,
        automation_name: str,
        input_data: dict | str,
        await_result: bool = True,
    ) -> str | dict:
        """Call another Cortex Automation (sub-automation).

        Args:
            automation_name: FQN of the target automation.
            input_data: Input payload (dict or JSON string).
            await_result: If True, wait for completion. If False, fire-and-forget.

        Returns:
            Automation output (string or dict).
        """
        input_json = (
            json.dumps(input_data) if isinstance(input_data, dict) else input_data
        )
        sql = "CALL IDENTIFIER(:1)(:2)"
        rows = self.query(sql, {"1": automation_name, "2": input_json})
        if rows:
            result = rows[0].get("RESULT", "")
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return str(result)
        return ""

    # ---- HITL ----

    def human_action(
        self,
        prompt: str,
        payload: dict | None = None,
        notify: dict | None = None,
        timeout_hours: int = 24,
    ) -> dict:
        """Pause the automation and wait for a human response (checkpoint-and-release).

        **Execution flow**:

        1. Raises ``HumanActionInterrupt`` (a Python exception), immediately
           unwinding the call stack back to the LangGraph runner loop.
        2. The runner's Go supervisor catches the interrupt (via Python process
           exit code / IPC), checkpoints the full LangGraph graph state to
           ``_cortex_automation_checkpoints`` and related Hybrid Tables.
        3. The run status in ``_cortex_automation_run_history`` is set to
           ``WAITING_FOR_HUMAN``, and the SPCS job terminates (no idle cost).
        4. A GS background task monitors pending human actions.  When the human
           submits a response via the Snowflake UI or API, GS cold-starts a new
           SPCS job, loads the checkpoint, injects the human response dict into
           the graph state, and resumes execution from the interrupted node.

        This design means the automation does **not** consume SPCS credits while
        waiting.  Cold-start latency on resume is typically 30–90 seconds.

        .. note::
           This differs from ``LocalBackend.human_action()``, which calls
           ``WorkflowSDK.interrupt()`` and blocks synchronously via IPC until
           the controld runner provides a response value.

        Args:
            prompt: Description of the action required from the human.
            payload: Optional data to display alongside the prompt.
            notify: Optional notification config (e.g., email, Slack).
            timeout_hours: Maximum hours to wait before timing out (default 24).

        Returns:
            Dict containing the human's response (populated after resume; this
            method never actually returns — it always raises).

        Raises:
            HumanActionInterrupt: Caught by the Go runner, not user code.
        """
        raise HumanActionInterrupt(
            prompt=prompt,
            payload=payload or {},
            notify=notify or {},
            timeout_hours=timeout_hours,
            run_id=self._run_id,
        )

    # ---- Secrets ----

    def secret(self, name: str) -> str:
        """Read a secret value from SPCS file mount.

        Secrets are mounted as files at /snowflake/secrets/<name> by SPCS,
        NOT as environment variables (security requirement from C9).

        Args:
            name: Secret key name (as defined in automation.toml [secrets]).

        Returns:
            Secret value string.
        """
        secret_path = os.path.join(self._secrets_dir, name)
        try:
            with open(secret_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise ValueError(
                f"Secret '{name}' not found at {secret_path}. "
                "Ensure it is defined in automation.toml [secrets] section."
            )

    # ---- Events & Output ----

    def emit(self, event: str, data: dict | None = None) -> None:
        """Emit a custom event (for monitoring/observability).

        Args:
            event: Event name.
            data: Optional event data.
        """
        logger.info("automation_event", extra={"event": event, "data": data or {}})

    def output(self, value: Any) -> None:
        """Set the automation's output value.

        This value is returned to the caller of CALL automation(input).

        Args:
            value: Output value (must be JSON-serializable).
        """
        self._output_value = value


class HumanActionInterrupt(Exception):
    """Raised by ``CortexContext.human_action()`` to trigger checkpoint-and-release.

    This exception is the signal mechanism between the Python automation code
    and the Go runner supervisor.  When raised, it unwinds the LangGraph
    execution stack completely.  The runner catches it (via process exit code
    or an inter-process signal), serialises the interrupt parameters alongside
    the checkpoint, and then terminates the SPCS container.

    User automation code should never catch or inspect this exception.  It is
    an internal protocol detail of the Cortex Automation platform.

    Attributes:
        prompt: Human-readable description of the required action.
        payload: Optional structured data to show the human (e.g. a document
                 to review, a form to fill in).
        notify: Optional notification routing config (email, Slack channel, etc.).
        timeout_hours: Maximum wall-clock hours the runner will wait for a
                       human response before marking the run as timed out.
        run_id: The automation run UUID, used by the runner to look up the
                corresponding ``_cortex_automation_run_history`` row.
    """

    def __init__(
        self,
        prompt: str,
        payload: dict,
        notify: dict,
        timeout_hours: int,
        run_id: str,
    ) -> None:
        self.prompt = prompt
        self.payload = payload
        self.notify = notify
        self.timeout_hours = timeout_hours
        self.run_id = run_id
        super().__init__(f"Human action required: {prompt}")
