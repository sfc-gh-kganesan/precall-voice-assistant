"""
automation_context.py — Abstract base class for Cortex Automation context objects.

Defines the unified API that all automation backends (CortexContext, LocalBackend,
MockCortexContext) must implement, allowing user code to run unchanged in SPCS,
local dev, and test environments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AutomationContext(ABC):
    """Abstract interface for interacting with Snowflake services from automation code.

    Concrete implementations:
    - ``CortexContext``  — SPCS/GS environment (OAuth token from file mount)
    - ``LocalBackend``   — local / controld mode (wraps ``WorkflowSDK``)
    - ``MockCortexContext`` — unit-test double

    Usage::

        from p67_sdk.context_factory import create_context

        ctx = create_context()
        rows = ctx.query("SELECT id, name FROM my_table WHERE id = %s", {"1": some_id})
        summary = ctx.complete("mistral-large2", "Summarize: " + text)
    """

    # ---- Data access --------------------------------------------------------

    @abstractmethod
    def query(self, sql: str, bindings: dict[str, Any] | None = None) -> list[dict]:
        """Execute a SQL query and return results as a list of row dicts.

        Args:
            sql: SQL query string.
            bindings: Optional parameter bindings.

        Returns:
            List of dicts mapping column name → value.
        """

    @abstractmethod
    def query_df(self, sql: str, bindings: dict[str, Any] | None = None):
        """Execute a SQL query and return results as a pandas DataFrame.

        Args:
            sql: SQL query string.
            bindings: Optional parameter bindings.

        Returns:
            pandas.DataFrame with query results.
        """

    # ---- Cortex AI ----------------------------------------------------------

    @abstractmethod
    def complete(self, model: str, prompt: str, **kwargs: Any) -> str | dict:
        """Call Cortex LLM for text completion.

        Args:
            model: Model name (e.g. ``'mistral-large2'``, ``'llama3.1-70b'``).
            prompt: Prompt string.
            **kwargs: Additional options (``temperature``, ``max_tokens``, etc.).

        Returns:
            Response string, or parsed dict if the model returns structured JSON.
        """

    @abstractmethod
    def search(self, service: str, query: str, limit: int = 10) -> list[dict]:
        """Call a Cortex Search service.

        Args:
            service: Fully-qualified name of the Cortex Search service.
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of search-result dicts.
        """

    @abstractmethod
    def analyst(self, semantic_view: str, question: str) -> dict:
        """Call Cortex Analyst with a natural-language question.

        Args:
            semantic_view: Fully-qualified name of the semantic view.
            question: Natural-language question.

        Returns:
            Dict with generated SQL and result data.
        """

    # ---- External access ----------------------------------------------------

    @abstractmethod
    def http(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict | str | None = None,
    ) -> dict:
        """Make an HTTP request.

        Args:
            method: HTTP method (``'GET'``, ``'POST'``, etc.).
            url: Target URL.
            headers: Optional request headers.
            body: Optional request body (dict serialised to JSON, or raw string).

        Returns:
            Dict with ``status``, ``headers``, and ``body`` keys.
        """

    # ---- Cross-automation ---------------------------------------------------

    @abstractmethod
    def agent(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
        timeout_seconds: int = 120,
    ) -> str:
        """Call a Cortex Agent.

        Args:
            agent_name: Fully-qualified name of the Cortex Agent.
            message: User message to send.
            thread_id: Optional thread ID for conversation continuity.
            timeout_seconds: Timeout for the agent call.

        Returns:
            Agent response text.
        """

    @abstractmethod
    def automation(
        self,
        automation_name: str,
        input_data: dict | str,
        await_result: bool = True,
    ) -> str | dict:
        """Invoke another Cortex Automation as a sub-automation.

        Args:
            automation_name: Fully-qualified name of the target automation.
            input_data: Input payload (dict or JSON string).
            await_result: If ``True``, block until completion; otherwise fire-and-forget.

        Returns:
            Automation output (string or parsed dict).
        """

    # ---- HITL ---------------------------------------------------------------

    @abstractmethod
    def human_action(
        self,
        prompt: str,
        payload: dict | None = None,
        notify: dict | None = None,
        timeout_hours: int = 24,
    ) -> dict:
        """Pause execution and wait for a human response.

        Args:
            prompt: Description of the action required from the human.
            payload: Optional data to display alongside the prompt.
            notify: Optional notification config (e.g. Slack).
            timeout_hours: Maximum hours to wait before timing out.

        Returns:
            Dict containing the human's response.
        """

    # ---- Secrets ------------------------------------------------------------

    @abstractmethod
    def secret(self, name: str) -> str:
        """Read a secret value by name.

        Args:
            name: Secret key name (as defined in automation configuration).

        Returns:
            Secret value string.

        Raises:
            ValueError: If the secret cannot be found.
        """

    # ---- Events & output ----------------------------------------------------

    @abstractmethod
    def emit(self, event: str, data: dict | None = None) -> None:
        """Emit a custom event for monitoring/observability.

        Args:
            event: Event name.
            data: Optional event payload.
        """

    @abstractmethod
    def output(self, value: Any) -> None:
        """Set the automation's return value.

        Args:
            value: JSON-serialisable output value returned to the caller.
        """
