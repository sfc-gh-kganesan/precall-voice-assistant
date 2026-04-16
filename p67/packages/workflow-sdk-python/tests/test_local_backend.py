"""
Tests for LocalBackend.

LocalBackend wraps WorkflowSDK behind the AutomationContext API so that
automation code can run locally without an SPCS container.  WorkflowSDK is
injected as a constructor argument and fully mocked here — no
snowflake-connector-python required.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_sdk() -> MagicMock:
    """A MagicMock instance standing in for a WorkflowSDK."""
    return MagicMock()


@pytest.fixture
def backend(mock_sdk: MagicMock):
    """LocalBackend instance backed by a mock SDK."""
    from p67_sdk.local_backend import LocalBackend

    return LocalBackend(mock_sdk)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_query_result(col_names: list[str], rows: list[tuple]):
    """Build a QueryResult with a mock cursor carrying column descriptions."""
    from p67_sdk.types import QueryResult

    mock_cursor = MagicMock()
    mock_cursor.description = [(name,) for name in col_names]
    return QueryResult(statement=mock_cursor, rows=rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLocalBackend:

    def test_query_converts_query_result_to_list_dict(self, backend, mock_sdk):
        """query() calls sdk.execute_query() and converts QueryResult to list[dict]."""
        mock_sdk.execute_query.return_value = _make_query_result(
            ["ID", "NAME"],
            [(1, "Alice"), (2, "Bob")],
        )

        result = backend.query("SELECT id, name FROM t")

        mock_sdk.execute_query.assert_called_once()
        assert result == [
            {"ID": 1, "NAME": "Alice"},
            {"ID": 2, "NAME": "Bob"},
        ]

    def test_query_passes_bindings(self, backend, mock_sdk):
        """bindings dict is converted to a list before being forwarded to WorkflowSDK."""
        mock_sdk.execute_query.return_value = _make_query_result(["X"], [(42,)])

        backend.query("SELECT x FROM t WHERE id = %s", {"1": 99})

        call = mock_sdk.execute_query.call_args
        # binds may be a positional or keyword argument
        if call.kwargs and "binds" in call.kwargs:
            binds = call.kwargs["binds"]
        elif call.args and len(call.args) > 1:
            binds = call.args[1]
        else:
            binds = None

        assert isinstance(binds, list), f"Expected list, got {type(binds)}: {binds}"
        assert 99 in binds

    def test_query_none_bindings_accepted(self, backend, mock_sdk):
        """query() with no bindings does not crash."""
        mock_sdk.execute_query.return_value = _make_query_result(["V"], [(7,)])

        result = backend.query("SELECT 7")

        assert result == [{"V": 7}]

    def test_complete_delegates_to_cortex_complete(self, backend, mock_sdk):
        """complete() calls sdk.cortex_complete() and extracts the text content."""
        from p67_sdk.types import (
            CortexChoice,
            CortexChoiceMessage,
            CortexCompleteResponse,
        )

        mock_sdk.cortex_complete.return_value = CortexCompleteResponse(
            success=True,
            choices=[
                CortexChoice(
                    index=0,
                    message=CortexChoiceMessage(
                        role="assistant", content="Hello, world!"
                    ),
                    finish_reason="stop",
                )
            ],
        )

        result = backend.complete("mistral-large2", "Say hello")

        mock_sdk.cortex_complete.assert_called_once()
        assert result == "Hello, world!"

    def test_http_converts_response(self, backend, mock_sdk):
        """http() calls sdk.http_request() and converts HttpResponse to a dict."""
        from p67_sdk.types import HttpResponse

        mock_sdk.http_request.return_value = HttpResponse(
            success=True,
            status=200,
            headers={"Content-Type": "application/json"},
            data={"key": "value"},
        )

        result = backend.http("GET", "https://example.com/api")

        mock_sdk.http_request.assert_called_once()
        assert result["status"] == 200
        assert result["body"] == {"key": "value"}
        assert result["headers"]["Content-Type"] == "application/json"

    def test_http_error_response_included(self, backend, mock_sdk):
        """http() preserves error information from a failed HttpResponse."""
        from p67_sdk.types import HttpResponse

        mock_sdk.http_request.return_value = HttpResponse(
            success=False,
            status=503,
            headers={},
            error="Service Unavailable",
        )

        result = backend.http("GET", "https://example.com/api")

        assert result["status"] == 503
        assert result["error"] == "Service Unavailable"

    def test_secret_reads_file_mount_first(self, mock_sdk, tmp_path, monkeypatch):
        """secret() reads the file mount before consulting env vars."""
        monkeypatch.setenv("SNOWFLAKE_SECRETS_DIR", str(tmp_path))
        (tmp_path / "MY_SECRET").write_text("file_secret_value")
        monkeypatch.setenv("MY_SECRET", "env_secret_value")

        from p67_sdk.local_backend import LocalBackend

        result = LocalBackend(mock_sdk).secret("MY_SECRET")

        assert result == "file_secret_value"

    def test_secret_falls_back_to_env_var(self, mock_sdk, tmp_path, monkeypatch):
        """secret() reads the env var when no file mount exists."""
        monkeypatch.setenv("SNOWFLAKE_SECRETS_DIR", str(tmp_path))
        monkeypatch.setenv("MY_SECRET", "env_secret_value")
        # tmp_path is empty — no file present

        from p67_sdk.local_backend import LocalBackend

        result = LocalBackend(mock_sdk).secret("MY_SECRET")

        assert result == "env_secret_value"

    def test_secret_raises_on_missing(self, mock_sdk, tmp_path, monkeypatch):
        """secret() raises ValueError when neither file nor env var is found."""
        monkeypatch.setenv("SNOWFLAKE_SECRETS_DIR", str(tmp_path))
        monkeypatch.delenv("MISSING_SECRET", raising=False)
        mock_sdk.get_parameter.side_effect = KeyError("MISSING_SECRET")

        from p67_sdk.local_backend import LocalBackend

        with pytest.raises(ValueError, match="MISSING_SECRET"):
            LocalBackend(mock_sdk).secret("MISSING_SECRET")

    def test_human_action_delegates_to_interrupt(self, backend, mock_sdk):
        """human_action() calls sdk.interrupt() and returns the resume response."""
        mock_sdk.interrupt.return_value = {"approved": True}

        result = backend.human_action(
            prompt="Please approve this action",
            payload={"item": "report-42"},
        )

        mock_sdk.interrupt.assert_called_once()
        assert result == {"approved": True}

    def test_human_action_forwards_payload(self, backend, mock_sdk):
        """The payload dict is included in the interrupt call."""
        mock_sdk.interrupt.return_value = {}
        payload = {"question": "Proceed?", "data": [1, 2, 3]}

        backend.human_action(prompt="Need input", payload=payload)

        call_args = mock_sdk.interrupt.call_args
        # payload can be positional or keyword; check it appears somewhere
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        assert any(payload == a or (isinstance(a, dict) and payload.items() <= a.items())
                   for a in all_args)

    def test_output_stores_value(self, backend):
        """output() persists the value so the runner can retrieve it."""
        backend.output({"result": 42})

        assert backend._output_value == {"result": 42}

    def test_output_overwrites_previous_value(self, backend):
        """Calling output() twice keeps only the last value."""
        backend.output("first")
        backend.output("second")

        assert backend._output_value == "second"

    def test_emit_logs_event(self, backend):
        """emit() completes without raising for both forms of the call."""
        backend.emit("my_event", {"key": "value"})
        backend.emit("bare_event")

    def test_implements_automation_context(self, mock_sdk):
        """LocalBackend is a concrete subclass of AutomationContext."""
        from p67_sdk.automation_context import AutomationContext
        from p67_sdk.local_backend import LocalBackend

        assert issubclass(LocalBackend, AutomationContext)
        # Also verify it can be instantiated (i.e., all abstract methods implemented)
        instance = LocalBackend(mock_sdk)
        assert isinstance(instance, AutomationContext)
