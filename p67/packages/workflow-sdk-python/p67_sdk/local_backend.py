"""
local_backend.py — LocalBackend: local/controld backend for Cortex Automations.

Wraps the existing ``WorkflowSDK`` behind the ``AutomationContext`` ABC so that
user automation code uses a single unified API regardless of whether it is
running inside SPCS (``CortexContext``) or locally / under controld
(``LocalBackend``).

Environment detection and instantiation is handled by
``context_factory.create_context()``.

---

**Adaptation mapping** — ``AutomationContext`` method → ``WorkflowSDK`` call:

+---------------------+-------------------------------------+---------------------------+
| AutomationContext   | WorkflowSDK call                    | Notes                     |
+=====================+=====================================+===========================+
| ``query()``         | ``sdk.execute_query(sql, params)``  | dict bindings → list      |
| ``query_df()``      | ``sdk.execute_query(sql, params)``  | wraps in pandas DataFrame |
| ``complete()``      | ``sdk.cortex_complete(opts)``       | REST inference API        |
| ``search()``        | ``sdk.execute_query(sql, params)``  | SQL CORTEX_SEARCH_PREVIEW |
| ``analyst()``       | ``sdk.query_cortex_analyst(q, sv)`` | REST Analyst API          |
| ``http()``          | ``sdk.http_request(opts)``          | external access           |
| ``agent()``         | ``sdk.call_cortex_agent(msg, opts)``| REST Agent API            |
| ``automation()``    | ``sdk.execute_subworkflow(opts)``   | fire-and-forget unsupport.|
| ``human_action()``  | ``sdk.interrupt(payload, opts)``    | **synchronous IPC block** |
| ``secret()``        | file mount → env var → ``sdk.get_parameter()`` | 3-tier lookup |
| ``emit()``          | ``logger.info(...)``                | structured log only       |
| ``output()``        | ``self._output_value = value``      | stored; read by runner    |
+---------------------+-------------------------------------+---------------------------+

**QueryResult conversion**:
  ``WorkflowSDK.execute_query()`` returns a ``QueryResult(statement, rows)``
  namedtuple.  ``statement.description`` is a list of ``(name, type, ...)``
  tuples matching the Python DB-API 2.0 cursor description spec.  The
  ``_result_to_dicts()`` helper zips column names with row tuples to produce
  the ``list[dict]`` contract expected by ``AutomationContext.query()``.

**Binding conversion**:
  ``CortexContext`` uses ``:N`` positional placeholders (Snowflake connector
  style) with dict bindings keyed by numeric strings (``"1"``, ``"2"``, …).
  ``WorkflowSDK.execute_query()`` uses ``%s`` placeholders with a positional
  list.  ``_bindings_to_list()`` sorts the dict by integer key and returns the
  corresponding value list.

**Secret priority chain**:
  1. SPCS/Docker file mount at ``/snowflake/secrets/<name>``
     (set via ``SNOWFLAKE_SECRETS_DIR`` env var or the default path).
  2. Environment variable named ``<name>`` — useful for local ``export SECRET=x``.
  3. ``WorkflowSDK.get_parameter(name)`` — reads from the manifest config dict
     (``parameters`` section), allowing secrets to be injected via controld.

**human_action IPC vs checkpoint-and-release**:
  In ``CortexContext``, ``human_action()`` raises ``HumanActionInterrupt``,
  which triggers an asynchronous checkpoint-and-release cycle: the SPCS
  container exits and a new one is started when the human responds (30–90 s
  cold-start latency, zero idle cost).

  In ``LocalBackend``, ``human_action()`` calls ``sdk.interrupt()`` which sends
  an interrupt message over the controld IPC channel and **blocks
  synchronously** until the runner process delivers a resume value.  There is
  no container restart; the Python process stays alive throughout.  The
  ``timeout_hours`` parameter is converted to milliseconds for the SDK.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from p67_sdk.automation_context import AutomationContext

if TYPE_CHECKING:
    from p67_sdk.sdk import WorkflowSDK

logger = logging.getLogger(__name__)

_SECRETS_DIR = "/snowflake/secrets"


class LocalBackend(AutomationContext):
    """``AutomationContext`` implementation backed by ``WorkflowSDK``.

    Used when running locally or under controld (no SPCS OAuth token).
    Authentication is provided through the ``WorkflowSDK`` configuration dict
    (``snowflakeConfig``, ``parameters``, etc.).

    .. note:: **human_action behaviour differs from CortexContext**.
       ``human_action()`` here calls ``sdk.interrupt()`` and blocks the calling
       thread via IPC until a resume value arrives.  In ``CortexContext`` it
       raises ``HumanActionInterrupt`` and the SPCS container is terminated
       (see module docstring for details).

    Example::

        from p67_sdk.sdk import WorkflowSDK
        from p67_sdk.local_backend import LocalBackend

        sdk = WorkflowSDK(config)
        ctx = LocalBackend(sdk)
        rows = ctx.query("SELECT * FROM my_table WHERE id = %s", {"1": some_id})
    """

    def __init__(self, sdk: WorkflowSDK, **kwargs: Any) -> None:
        """Initialise the backend.

        Args:
            sdk: An already-constructed ``WorkflowSDK`` instance.
            **kwargs: Reserved for future use.
        """
        self._sdk = sdk
        self._output_value: Any = None

    # ---- Internal helpers ---------------------------------------------------

    def _bindings_to_list(self, bindings: dict[str, Any] | None) -> list[Any] | None:
        """Convert a dict-style bindings map to a positional list.

        ``WorkflowSDK.execute_query`` uses positional (list) bindings, while the
        ``AutomationContext`` API accepts dict bindings keyed by numeric strings
        (``"1"``, ``"2"``, …) matching the ``:N`` placeholder convention used by
        ``CortexContext``.

        Args:
            bindings: Dict of ``{"1": val, "2": val, …}`` or ``None``.

        Returns:
            Sorted list of binding values, or ``None`` if no bindings were given.
        """
        if bindings is None:
            return None
        if isinstance(bindings, list):
            return bindings
        try:
            return [v for _, v in sorted(bindings.items(), key=lambda kv: int(kv[0]))]
        except (ValueError, TypeError):
            return list(bindings.values())

    def _result_to_dicts(self, result: Any) -> list[dict]:
        """Convert a ``QueryResult`` to a list of row dicts.

        ``WorkflowSDK.execute_query()`` returns a
        ``QueryResult(statement, rows)`` namedtuple where:

        - ``statement`` is a DB-API 2.0 cursor-like object.  Its
          ``description`` attribute is a sequence of 7-item tuples:
          ``(name, type_code, display_size, internal_size, precision,
          scale, null_ok)``.  Only ``name`` (index 0) is used here.
        - ``rows`` is a sequence of row tuples, one per result row.

        If ``description`` is absent or empty (e.g. for DDL statements that
        return no metadata), the rows are wrapped as dicts keyed by their
        integer column index.

        Args:
            result: ``QueryResult(statement, rows)`` from ``WorkflowSDK``.

        Returns:
            List of dicts mapping column name → value.
        """
        description = getattr(result.statement, "description", None) or []
        columns = [desc[0] for desc in description]
        if not columns:
            # No column metadata — return raw tuples wrapped as dicts with index keys.
            return [dict(enumerate(row)) for row in result.rows]
        return [dict(zip(columns, row)) for row in result.rows]

    # ---- Data access --------------------------------------------------------

    def query(self, sql: str, bindings: dict[str, Any] | None = None) -> list[dict]:
        """Execute a SQL query and return results as a list of row dicts.

        Args:
            sql: SQL query string. Use ``%s`` placeholders for positional bindings.
            bindings: Optional dict of ``{"1": val, "2": val}`` style bindings.
                      Converted to a positional list before execution.

        Returns:
            List of dicts mapping column name → value.
        """
        binds = self._bindings_to_list(bindings)
        result = self._sdk.execute_query(sql, binds)
        return self._result_to_dicts(result)

    def query_df(self, sql: str, bindings: dict[str, Any] | None = None):
        """Execute a SQL query and return results as a pandas DataFrame.

        Args:
            sql: SQL query string.
            bindings: Optional dict bindings (see ``query()``).

        Returns:
            ``pandas.DataFrame`` with query results.
        """
        import pandas as pd  # lazy import — pandas may not always be installed

        binds = self._bindings_to_list(bindings)
        result = self._sdk.execute_query(sql, binds)
        description = getattr(result.statement, "description", None) or []
        columns = [desc[0] for desc in description]
        return pd.DataFrame(result.rows, columns=columns or None)

    # ---- Cortex AI ----------------------------------------------------------

    def complete(self, model: str, prompt: str, **kwargs: Any) -> str | dict:
        """Call Cortex LLM via the REST inference API.

        Args:
            model: Model name (e.g. ``'mistral-large2'``).
            prompt: Prompt string.
            **kwargs: Optional overrides: ``temperature``, ``max_tokens``, ``top_p``.

        Returns:
            Response string, or parsed dict if the model returns structured JSON.
        """
        from p67_sdk.types import CortexCompleteOptions  # lazy import

        opts = CortexCompleteOptions(
            model=model,
            messages=prompt,
            temperature=kwargs.get("temperature"),
            max_tokens=kwargs.get("max_tokens"),
            top_p=kwargs.get("top_p"),
        )
        response = self._sdk.cortex_complete(opts)

        if not response.success:
            logger.warning("cortex_complete failed (model=%s): %s", model, response.error)
            return response.error or ""

        choices = response.choices or []
        if not choices:
            return ""

        content = choices[0].message.content
        if content is None:
            return ""

        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content

    def search(self, service: str, query: str, limit: int = 10) -> list[dict]:
        """Query a Cortex Search service via SQL.

        Args:
            service: Fully-qualified name of the Cortex Search service.
            query: Search query string.
            limit: Maximum number of results (default 10).

        Returns:
            List of search-result dicts.
        """
        sql = f"SELECT * FROM TABLE(CORTEX_SEARCH_PREVIEW('{service}', %s, %s))"
        result = self._sdk.execute_query(sql, [query, limit])
        return self._result_to_dicts(result)

    def analyst(self, semantic_view: str, question: str) -> dict:
        """Call Cortex Analyst via the REST API.

        Args:
            semantic_view: Fully-qualified name of the semantic view or model file.
            question: Natural-language question.

        Returns:
            Dict with generated SQL and result data from Cortex Analyst.
        """
        response = self._sdk.query_cortex_analyst(question, semantic_view)

        if not response.success:
            logger.warning("query_cortex_analyst failed: %s", response.error)
            return {}

        data = response.data
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {"result": data}

    # ---- External access ----------------------------------------------------

    def http(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict | str | None = None,
    ) -> dict:
        """Make an HTTP request via ``WorkflowSDK.http_request``.

        Args:
            method: HTTP method (``'GET'``, ``'POST'``, etc.).
            url: Target URL.
            headers: Optional request headers.
            body: Optional body — dict is JSON-serialised automatically.

        Returns:
            Dict with ``status``, ``headers``, ``body``, and optional ``error`` keys.
        """
        from p67_sdk.types import HttpRequestOptions  # lazy import

        opts = HttpRequestOptions(
            url=url,
            method=method,
            headers=headers or {},
            body=body,
        )
        resp = self._sdk.http_request(opts)
        return {
            "status": resp.status,
            "headers": dict(resp.headers or {}),
            "body": resp.data,
            "error": resp.error,
        }

    # ---- Cross-automation ---------------------------------------------------

    def agent(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
        timeout_seconds: int = 120,
    ) -> str:
        """Call a Cortex Agent via the REST API.

        ``agent_name`` should be a fully-qualified identifier of the form
        ``DATABASE.SCHEMA.AGENT_NAME``.

        Args:
            agent_name: FQN of the Cortex Agent.
            message: User message to send.
            thread_id: Optional thread / parent-message ID.
            timeout_seconds: Request timeout.

        Returns:
            Agent response as a plain text string.

        Raises:
            RuntimeError: If the agent call fails.
        """
        parts = agent_name.split(".")
        if len(parts) == 3:
            db, schema, name = parts
        elif len(parts) == 2:
            db, schema, name = None, parts[0], parts[1]
        else:
            db, schema, name = None, None, agent_name

        options: dict[str, Any] = {"agentName": name}
        if db:
            options["agentDatabase"] = db
        if schema:
            options["agentSchema"] = schema
        if thread_id:
            options["parentMessageId"] = thread_id

        response = self._sdk.call_cortex_agent(message, options)

        if not response.success:
            raise RuntimeError(
                f"Agent call failed for '{agent_name}': {response.error}"
            )

        data = response.data or {}
        msg = data.get("message", {})
        content = msg.get("content", [])

        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)

    def automation(
        self,
        automation_name: str,
        input_data: dict | str,
        await_result: bool = True,
    ) -> str | dict:
        """Run another automation as a sub-workflow via ``WorkflowSDK.execute_subworkflow``.

        Args:
            automation_name: Name of the target workflow.
            input_data: Input payload — a dict whose values are stringified, or a
                        JSON string which is decoded to build the params dict.
            await_result: Must be ``True`` (fire-and-forget is not yet supported
                          via this code path; a warning is logged if ``False``).

        Returns:
            Automation result (dict) or empty dict on failure.
        """
        from p67_sdk.types import SubworkflowOptions  # lazy import

        if not await_result:
            logger.warning(
                "LocalBackend.automation(): await_result=False is not supported "
                "via execute_subworkflow; the call will still block."
            )

        # Build a string-valued params dict from the input payload.
        if isinstance(input_data, str):
            try:
                decoded = json.loads(input_data)
                params = (
                    {k: str(v) for k, v in decoded.items()}
                    if isinstance(decoded, dict)
                    else {"input": input_data}
                )
            except json.JSONDecodeError:
                params = {"input": input_data}
        elif isinstance(input_data, dict):
            params = {
                k: v if isinstance(v, str) else json.dumps(v)
                for k, v in input_data.items()
            }
        else:
            params = {}

        opts = SubworkflowOptions(
            workflow_name=automation_name,
            params=params or None,
        )
        response = self._sdk.execute_subworkflow(opts)

        if not response.success:
            logger.warning(
                "Sub-automation '%s' failed: %s", automation_name, response.error
            )
            return {}

        result = response.result
        if result is None:
            return {}
        if isinstance(result, (dict, list)):
            return result
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return str(result)

    # ---- HITL ---------------------------------------------------------------

    def human_action(
        self,
        prompt: str,
        payload: dict | None = None,
        notify: dict | None = None,
        timeout_hours: int = 24,
    ) -> dict:
        """Pause execution and wait for a human response via IPC interrupt.

        Calls ``WorkflowSDK.interrupt()``, which sends an interrupt message
        over the controld IPC channel and **blocks the current thread
        synchronously** until the runner process delivers a resume value.
        The Python process stays alive throughout; there is no container
        restart.

        .. contrast with ``CortexContext.human_action()``:
           In the SPCS backend, ``human_action()`` raises
           ``HumanActionInterrupt``, terminates the container, and the human
           response arrives via a cold-start of a *new* container.  That
           path has 30–90 s latency and zero idle cost.  This path has no
           latency overhead but consumes controld resources while waiting.

        Args:
            prompt: Description of the action required from the human.
            payload: Optional supplementary data to display.
            notify: Optional Slack notification config dict.
            timeout_hours: Maximum hours to wait (converted to milliseconds
                           for the SDK call).

        Returns:
            Dict containing the human's response.
        """
        full_payload = {"prompt": prompt, **(payload or {})}
        options: dict[str, Any] = {
            "timeout": int(timeout_hours * 3600 * 1000),
            "notify": notify,
        }
        result = self._sdk.interrupt(full_payload, options)
        if isinstance(result, dict):
            return result
        return {"response": result}

    # ---- Secrets ------------------------------------------------------------

    def secret(self, name: str) -> str:
        """Read a secret value using a three-tier lookup.

        Priority:
        1. SPCS file mount at ``/snowflake/secrets/<name>``
        2. Environment variable named ``<name>``
        3. ``WorkflowSDK.get_parameter(name)`` (manifest config)

        Args:
            name: Secret key name.

        Returns:
            Secret value string.

        Raises:
            ValueError: If the secret cannot be found in any source.
        """
        # 1. File mount (SPCS or Docker secret mount)
        secrets_dir = os.environ.get("SNOWFLAKE_SECRETS_DIR", _SECRETS_DIR)
        secret_path = os.path.join(secrets_dir, name)
        try:
            with open(secret_path, "r") as fh:
                value = fh.read().strip()
                logger.debug("secret '%s' read from file mount", name)
                return value
        except (FileNotFoundError, OSError):
            pass

        # 2. Environment variable
        env_value = os.environ.get(name)
        if env_value is not None:
            logger.debug("secret '%s' read from environment variable", name)
            return env_value

        # 3. SDK manifest parameter
        try:
            value = self._sdk.get_parameter(name)
            logger.debug("secret '%s' read from SDK config parameter", name)
            return value
        except (KeyError, ValueError):
            pass

        raise ValueError(
            f"Secret '{name}' not found. "
            "Checked: file mount at /snowflake/secrets/, "
            "environment variable, and SDK manifest parameters."
        )

    # ---- Events & output ----------------------------------------------------

    def emit(self, event: str, data: dict | None = None) -> None:
        """Emit a named event for monitoring/observability.

        Args:
            event: Event name.
            data: Optional event payload dict.
        """
        logger.info(
            "automation_event event=%s data=%s",
            event,
            json.dumps(data or {}, default=str),
        )

    def output(self, value: Any) -> None:
        """Set the automation's return value.

        Args:
            value: JSON-serialisable output value.
        """
        self._output_value = value
