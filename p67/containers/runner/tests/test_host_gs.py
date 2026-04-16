"""
Tests for host_gs.py — GS-aware runner host.

All tests use mocks; no real Snowflake connection, SPCS container, or
LangGraph installation is required.

Coverage:
  - _import_entrypoint: entrypoint string parsing, module loading, error cases
  - _is_state_graph / _is_compiled_graph: graph type detection
  - _write_results_file: P67_RESULTS_DIR present / absent
  - _call_function: arity detection, async support
  - main(): env var reading, HITL exit, execution errors, result writing
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

import host_gs


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _MockHumanActionInterrupt(Exception):
    """Minimal stand-in for p67_sdk.cortex_context.HumanActionInterrupt."""

    def __init__(
        self,
        prompt: str = "Approve?",
        payload: dict | None = None,
        run_id: str = "run-42",
        notify: bool = False,
        timeout_hours: int = 24,
    ) -> None:
        super().__init__(prompt)
        self.prompt = prompt
        self.payload = payload or {}
        self.run_id = run_id
        self.notify = notify
        self.timeout_hours = timeout_hours


def _make_cortex_module(ctx: MagicMock | None = None):
    """Return (fake_cortex_context_module, mock_ctx_instance).

    The module exposes CortexContext (returns mock_ctx) and
    HumanActionInterrupt (set to _MockHumanActionInterrupt).
    """
    mock_ctx = ctx or MagicMock()
    mock_ctx._output_value = None  # must be explicitly None, not a MagicMock

    mod = MagicMock()
    mod.CortexContext.return_value = mock_ctx
    mod.HumanActionInterrupt = _MockHumanActionInterrupt
    return mod, mock_ctx


# ---------------------------------------------------------------------------
# Autouse fixture — prevent sys.modules / sys.path pollution between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_module_state():
    """Restore sys.modules and sys.path to their pre-test state."""
    modules_snapshot = set(sys.modules.keys())
    path_snapshot = list(sys.path)
    yield
    for key in list(sys.modules.keys()):
        if key not in modules_snapshot:
            del sys.modules[key]
    sys.path[:] = path_snapshot


# ---------------------------------------------------------------------------
# TestImportEntrypoint
# ---------------------------------------------------------------------------


class TestImportEntrypoint:
    """Unit tests for host_gs._import_entrypoint()."""

    def test_simple_entrypoint_loads_attribute(self, tmp_path, monkeypatch):
        """'main:app' loads /workflow/main.py and returns the 'app' attribute."""
        workflow_dir = tmp_path / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "main.py").write_text("app = 'hello_world'\n")

        monkeypatch.setattr(host_gs, "WORKFLOW_DIR", str(workflow_dir))

        result = host_gs._import_entrypoint("main:app")

        assert result == "hello_world"

    def test_dotted_module_path_maps_to_subdirectory(self, tmp_path, monkeypatch):
        """'automations.triage.graph:workflow' maps to automations/triage/graph.py."""
        workflow_dir = tmp_path / "workflow"
        (workflow_dir / "automations" / "triage").mkdir(parents=True)
        (workflow_dir / "automations" / "triage" / "graph.py").write_text(
            "workflow = 99\n"
        )

        monkeypatch.setattr(host_gs, "WORKFLOW_DIR", str(workflow_dir))

        result = host_gs._import_entrypoint("automations.triage.graph:workflow")

        assert result == 99

    def test_callable_attribute_returned(self, tmp_path, monkeypatch):
        """A callable defined in the module is returned correctly."""
        workflow_dir = tmp_path / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "main.py").write_text("def app(ctx): return 42\n")

        monkeypatch.setattr(host_gs, "WORKFLOW_DIR", str(workflow_dir))

        result = host_gs._import_entrypoint("main:app")

        assert callable(result)

    def test_no_colon_raises_value_error(self):
        """Entrypoint string without ':' raises ValueError."""
        with pytest.raises(ValueError, match="must be 'module:attribute' format"):
            host_gs._import_entrypoint("mainapp")

    def test_empty_string_raises_value_error(self):
        """Empty entrypoint string raises ValueError."""
        with pytest.raises(ValueError, match="must be 'module:attribute' format"):
            host_gs._import_entrypoint("")

    def test_missing_module_file_raises_import_error(self, tmp_path, monkeypatch):
        """Non-existent module file raises ImportError."""
        workflow_dir = tmp_path / "workflow"
        workflow_dir.mkdir()
        # Intentionally do not create the file.

        monkeypatch.setattr(host_gs, "WORKFLOW_DIR", str(workflow_dir))

        with pytest.raises(ImportError, match="not found"):
            host_gs._import_entrypoint("nonexistent_module:app")

    def test_missing_attribute_raises_attribute_error(self, tmp_path, monkeypatch):
        """Module file that does not define the attribute raises AttributeError."""
        workflow_dir = tmp_path / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "main.py").write_text("# nothing here\n")

        monkeypatch.setattr(host_gs, "WORKFLOW_DIR", str(workflow_dir))

        with pytest.raises(AttributeError, match="no attribute"):
            host_gs._import_entrypoint("main:missing_attr")

    def test_workflow_dir_added_to_sys_path(self, tmp_path, monkeypatch):
        """_import_entrypoint() inserts WORKFLOW_DIR into sys.path."""
        workflow_dir = tmp_path / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "main.py").write_text("app = 1\n")

        monkeypatch.setattr(host_gs, "WORKFLOW_DIR", str(workflow_dir))

        host_gs._import_entrypoint("main:app")

        assert str(workflow_dir) in sys.path


# ---------------------------------------------------------------------------
# TestGraphTypeDetection
# ---------------------------------------------------------------------------


class TestGraphTypeDetection:
    """Unit tests for _is_state_graph() and _is_compiled_graph()."""

    @staticmethod
    def _fake_langgraph_state_module():
        """Return (fake_state_module, FakeStateGraph, FakeCompiledStateGraph)."""

        class FakeStateGraph:
            pass

        class FakeCompiledStateGraph(FakeStateGraph):
            pass

        mod = MagicMock()
        mod.StateGraph = FakeStateGraph
        mod.CompiledStateGraph = FakeCompiledStateGraph
        return mod, FakeStateGraph, FakeCompiledStateGraph

    def test_state_graph_instance_is_detected(self):
        """An instance of StateGraph returns True from _is_state_graph()."""
        mod, FakeStateGraph, _ = self._fake_langgraph_state_module()

        with patch.dict(
            "sys.modules",
            {
                "langgraph": MagicMock(),
                "langgraph.graph": MagicMock(),
                "langgraph.graph.state": mod,
            },
        ):
            assert host_gs._is_state_graph(FakeStateGraph()) is True

    def test_compiled_graph_instance_is_detected(self):
        """An instance of CompiledStateGraph returns True from _is_compiled_graph()."""
        mod, _, FakeCompiledStateGraph = self._fake_langgraph_state_module()

        with patch.dict(
            "sys.modules",
            {
                "langgraph": MagicMock(),
                "langgraph.graph": MagicMock(),
                "langgraph.graph.state": mod,
            },
        ):
            assert host_gs._is_compiled_graph(FakeCompiledStateGraph()) is True

    def test_plain_callable_not_state_graph(self):
        """A plain function is not a StateGraph."""
        mod, _, _ = self._fake_langgraph_state_module()

        with patch.dict(
            "sys.modules",
            {
                "langgraph": MagicMock(),
                "langgraph.graph": MagicMock(),
                "langgraph.graph.state": mod,
            },
        ):
            assert host_gs._is_state_graph(lambda: None) is False

    def test_plain_callable_not_compiled_graph(self):
        """A plain function is not a CompiledStateGraph."""
        mod, _, _ = self._fake_langgraph_state_module()

        with patch.dict(
            "sys.modules",
            {
                "langgraph": MagicMock(),
                "langgraph.graph": MagicMock(),
                "langgraph.graph.state": mod,
            },
        ):
            assert host_gs._is_compiled_graph("not-a-graph") is False

    def test_state_graph_returns_false_when_langgraph_absent(self):
        """_is_state_graph() returns False gracefully when langgraph is not installed."""
        with patch.dict(
            "sys.modules",
            {"langgraph": None, "langgraph.graph": None, "langgraph.graph.state": None},
        ):
            assert host_gs._is_state_graph(MagicMock()) is False

    def test_compiled_graph_returns_false_when_langgraph_absent(self):
        """_is_compiled_graph() returns False gracefully when langgraph is not installed."""
        with patch.dict(
            "sys.modules",
            {"langgraph": None, "langgraph.graph": None, "langgraph.graph.state": None},
        ):
            assert host_gs._is_compiled_graph(MagicMock()) is False


# ---------------------------------------------------------------------------
# TestWriteResultsFile
# ---------------------------------------------------------------------------


class TestWriteResultsFile:
    """Unit tests for host_gs._write_results_file()."""

    def test_writes_json_file_to_results_dir(self, tmp_path, monkeypatch):
        """result.json is written with the correct content when P67_RESULTS_DIR is set."""
        monkeypatch.setenv("P67_RESULTS_DIR", str(tmp_path))

        host_gs._write_results_file("result.json", {"status": "ok", "count": 3})

        written = json.loads((tmp_path / "result.json").read_text())
        assert written == {"status": "ok", "count": 3}

    def test_creates_nested_directory_if_missing(self, tmp_path, monkeypatch):
        """_write_results_file() creates the results directory if it does not exist."""
        results_dir = tmp_path / "deep" / "nested"
        monkeypatch.setenv("P67_RESULTS_DIR", str(results_dir))

        host_gs._write_results_file("out.json", {"x": 1})

        assert (results_dir / "out.json").exists()

    def test_no_write_when_results_dir_unset(self, tmp_path, monkeypatch):
        """No file is written and no exception raised when P67_RESULTS_DIR is absent."""
        monkeypatch.delenv("P67_RESULTS_DIR", raising=False)

        host_gs._write_results_file("result.json", {"status": "ok"})

        # Nothing should exist in tmp_path.
        assert list(tmp_path.iterdir()) == []

    def test_no_write_when_results_dir_empty_string(self, monkeypatch):
        """Empty P67_RESULTS_DIR string is treated as unset (no write, no crash)."""
        monkeypatch.setenv("P67_RESULTS_DIR", "")

        # Should complete without error.
        host_gs._write_results_file("result.json", {})


# ---------------------------------------------------------------------------
# TestCallFunction
# ---------------------------------------------------------------------------


class TestCallFunction:
    """Unit tests for host_gs._call_function()."""

    def test_single_param_called_with_ctx(self):
        """A one-parameter function receives ctx and its return value is passed back."""
        mock_ctx = MagicMock()
        received: list = []

        def fn(ctx):
            received.append(ctx)
            return "single_result"

        result = host_gs._call_function(fn, mock_ctx, {"input": "data"})

        assert result == "single_result"
        assert received == [mock_ctx]

    def test_two_param_called_with_ctx_and_input(self):
        """A two-parameter function receives (ctx, input_data)."""
        mock_ctx = MagicMock()
        input_data = {"key": "value", "num": 42}
        received: list = []

        def fn(ctx, data):
            received.append((ctx, data))
            return "two_result"

        result = host_gs._call_function(fn, mock_ctx, input_data)

        assert result == "two_result"
        assert received[0] == (mock_ctx, input_data)

    def test_async_function_is_awaited(self):
        """An async single-param function is run via asyncio.run()."""
        mock_ctx = MagicMock()

        async def async_fn(ctx):
            return "async_result"

        result = host_gs._call_function(async_fn, mock_ctx, {})

        assert result == "async_result"

    def test_async_two_param_function_is_awaited(self):
        """An async two-param function is run via asyncio.run()."""
        mock_ctx = MagicMock()

        async def async_fn(ctx, data):
            return data.get("val")

        result = host_gs._call_function(async_fn, mock_ctx, {"val": 99})

        assert result == 99


# ---------------------------------------------------------------------------
# TestMain — fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_env(monkeypatch, tmp_path):
    """Set the minimum environment variables required for main() to proceed."""
    monkeypatch.setenv("AUTOMATION_ENTRYPOINT", "main:app")
    monkeypatch.setenv("AUTOMATION_RUN_ID", "run-test-999")
    monkeypatch.setenv("AUTOMATION_NAME", "mydb.myschema.my_automation")
    monkeypatch.setenv("AUTOMATION_INPUT", '{"greeting": "hello"}')
    monkeypatch.setenv("P67_RESULTS_DIR", str(tmp_path))
    return tmp_path


def _run_main_with_callable(
    mock_fn,
    cortex_mod,
    *,
    extra_sys_modules: dict | None = None,
    extra_patches: list | None = None,
):
    """Helper: run host_gs.main() with a plain-callable entrypoint."""
    sys_modules = {
        "p67_sdk": MagicMock(),
        "p67_sdk.cortex_context": cortex_mod,
    }
    if extra_sys_modules:
        sys_modules.update(extra_sys_modules)

    patches = [
        patch("host_gs._import_entrypoint", return_value=mock_fn),
        patch("host_gs._validate_config"),
        patch("host_gs._is_state_graph", return_value=False),
        patch("host_gs._is_compiled_graph", return_value=False),
        patch("host_gs._send_message"),
        patch.dict("sys.modules", sys_modules),
    ]
    if extra_patches:
        patches.extend(extra_patches)

    with _nested(*patches):
        with pytest.raises(SystemExit) as exc_info:
            host_gs.main()
    return exc_info.value.code


def _nested(*cms):
    """Apply a list of context managers as a single context manager."""
    import contextlib

    return contextlib.ExitStack().__enter__() and _ExitStackCM(cms)


class _ExitStackCM:
    """Simple helper to enter a list of CMs in sequence."""

    def __init__(self, cms):
        self._cms = cms
        self._stack = None

    def __enter__(self):
        import contextlib

        self._stack = contextlib.ExitStack()
        for cm in self._cms:
            self._stack.enter_context(cm)
        return self._stack

    def __exit__(self, *args):
        return self._stack.__exit__(*args)


# ---------------------------------------------------------------------------
# TestMain — environment variable handling
# ---------------------------------------------------------------------------


class TestMainEnvVars:

    def test_missing_entrypoint_exits_1(self, monkeypatch):
        """Missing AUTOMATION_ENTRYPOINT causes exit code 1 without crashing."""
        monkeypatch.delenv("AUTOMATION_ENTRYPOINT", raising=False)

        with patch("host_gs._send_message"):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 1

    def test_cortex_context_is_instantiated(self, base_env):
        """CortexContext() is called exactly once during a successful run."""
        mock_fn = MagicMock(return_value=None)
        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit):
                host_gs.main()

        cortex_mod.CortexContext.assert_called_once()

    def test_invalid_json_input_treated_as_empty_dict(self, base_env, monkeypatch):
        """Non-JSON AUTOMATION_INPUT is ignored; execution still succeeds."""
        monkeypatch.setenv("AUTOMATION_INPUT", "not-valid-json{{")
        received_inputs: list = []

        def mock_fn(ctx, data):
            received_inputs.append(data)
            return None

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        # Input falls back to empty dict when JSON is invalid.
        assert received_inputs == [{}]

    def test_non_dict_json_input_wrapped(self, base_env, monkeypatch):
        """A non-dict JSON value (e.g. a list) is wrapped under 'value' key."""
        monkeypatch.setenv("AUTOMATION_INPUT", "[1, 2, 3]")
        received_inputs: list = []

        def mock_fn(ctx, data):
            received_inputs.append(data)
            return None

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit):
                host_gs.main()

        assert received_inputs == [{"value": [1, 2, 3]}]


# ---------------------------------------------------------------------------
# TestMain — graph type routing
# ---------------------------------------------------------------------------


class TestMainGraphRouting:

    def test_state_graph_compiled_with_checkpointer(self, base_env):
        """An uncompiled StateGraph is compiled with SnowflakeCheckpointer before invoke."""
        mock_graph = MagicMock()
        compiled = MagicMock()
        compiled.invoke.return_value = {"final": "state"}
        mock_graph.compile.return_value = compiled

        mock_checkpointer = MagicMock()
        mock_checkpointer_class = MagicMock(return_value=mock_checkpointer)

        cortex_mod, _ = _make_cortex_module()
        mock_checkpointer_mod = MagicMock()
        mock_checkpointer_mod.SnowflakeCheckpointer = mock_checkpointer_class

        with patch("host_gs._import_entrypoint", return_value=mock_graph), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=True), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
                 "p67_sdk.checkpointer": mock_checkpointer_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        mock_checkpointer_class.assert_called_once()
        mock_graph.compile.assert_called_once_with(checkpointer=mock_checkpointer)
        compiled.invoke.assert_called_once()

    def test_compiled_graph_invoked_without_recompile(self, base_env):
        """A CompiledStateGraph is invoked directly — .compile() is never called."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"result": 42}

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_graph), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=True), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        mock_graph.compile.assert_not_called()
        mock_graph.invoke.assert_called_once()

    def test_plain_callable_called_with_ctx(self, base_env):
        """A plain one-param callable receives the CortexContext instance."""
        received_ctx: list = []

        def mock_fn(ctx):
            received_ctx.append(ctx)
            return {"output": "done"}

        cortex_mod, mock_ctx = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        assert len(received_ctx) == 1
        assert received_ctx[0] is mock_ctx

    def test_non_callable_non_graph_exits_1(self, base_env):
        """An entrypoint that is neither callable nor a graph causes exit code 1."""
        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=42), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# TestMain — result writing
# ---------------------------------------------------------------------------


class TestMainResultWriting:

    def test_result_json_written_on_success(self, base_env):
        """result.json is written to P67_RESULTS_DIR containing the function's return."""
        tmp_path = base_env
        mock_fn = MagicMock(return_value={"answer": 42})
        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        result = json.loads((tmp_path / "result.json").read_text())
        assert result == {"answer": 42}

    def test_ctx_output_overrides_function_return(self, base_env):
        """ctx.output() value takes precedence over the callable's return value."""
        tmp_path = base_env
        cortex_mod, mock_ctx = _make_cortex_module()
        mock_ctx._output_value = {"ctx_wins": True}

        mock_fn = MagicMock(return_value={"fn_ignored": True})

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        result = json.loads((tmp_path / "result.json").read_text())
        assert result == {"ctx_wins": True}

    def test_no_result_file_when_results_dir_unset(self, monkeypatch, tmp_path):
        """No result.json is written when P67_RESULTS_DIR is not set; exit is still 0."""
        monkeypatch.setenv("AUTOMATION_ENTRYPOINT", "main:app")
        monkeypatch.delenv("P67_RESULTS_DIR", raising=False)

        mock_fn = MagicMock(return_value={"data": 1})
        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=mock_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 0
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# TestMain — error handling
# ---------------------------------------------------------------------------


class TestMainErrorHandling:

    def test_import_error_exits_1(self, base_env):
        """Import failure → exit code 1."""
        with patch("host_gs._import_entrypoint", side_effect=ImportError("bad module")), \
             patch("host_gs._validate_config"), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {"p67_sdk": MagicMock()}):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 1

    def test_import_error_writes_error_json(self, base_env):
        """Import failure writes an error.json with IndexScriptImportError type."""
        tmp_path = base_env

        with patch("host_gs._import_entrypoint", side_effect=ImportError("bad module")), \
             patch("host_gs._validate_config"), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {"p67_sdk": MagicMock()}):
            with pytest.raises(SystemExit):
                host_gs.main()

        err = json.loads((tmp_path / "error.json").read_text())
        assert err["error"] == "IndexScriptImportError"
        assert "bad module" in err["message"]

    def test_execution_error_exits_1(self, base_env):
        """User code exception → exit code 1."""

        def exploding_fn(ctx):
            raise RuntimeError("boom")

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=exploding_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == 1

    def test_execution_error_writes_error_json(self, base_env):
        """User code exception writes error.json with ExecutionError type and traceback."""
        tmp_path = base_env

        def exploding_fn(ctx):
            raise RuntimeError("something went wrong")

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=exploding_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit):
                host_gs.main()

        err = json.loads((tmp_path / "error.json").read_text())
        assert err["error"] == "ExecutionError"
        assert "something went wrong" in err["message"]
        assert "traceback" in err  # stack trace is included

    def test_hitl_interrupt_exits_42(self, base_env):
        """HumanActionInterrupt → exit code 42."""

        def hitl_fn(ctx):
            raise _MockHumanActionInterrupt(prompt="Please approve", run_id="run-42")

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=hitl_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit) as exc_info:
                host_gs.main()

        assert exc_info.value.code == host_gs.EXIT_HITL

    def test_hitl_interrupt_writes_hitl_json(self, base_env):
        """HumanActionInterrupt writes hitl.json with expected fields."""
        tmp_path = base_env

        def hitl_fn(ctx):
            raise _MockHumanActionInterrupt(
                prompt="Please approve",
                payload={"item": "report-99"},
                run_id="run-42",
                notify=True,
                timeout_hours=48,
            )

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=hitl_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit):
                host_gs.main()

        hitl = json.loads((tmp_path / "hitl.json").read_text())
        assert hitl["type"] == "HumanActionInterrupt"
        assert hitl["prompt"] == "Please approve"
        assert hitl["payload"] == {"item": "report-99"}
        assert hitl["run_id"] == "run-42"
        assert hitl["notify"] is True
        assert hitl["timeout_hours"] == 48

    def test_hitl_does_not_write_result_json(self, base_env):
        """A HITL pause does not leave a result.json (only hitl.json)."""
        tmp_path = base_env

        def hitl_fn(ctx):
            raise _MockHumanActionInterrupt()

        cortex_mod, _ = _make_cortex_module()

        with patch("host_gs._import_entrypoint", return_value=hitl_fn), \
             patch("host_gs._validate_config"), \
             patch("host_gs._is_state_graph", return_value=False), \
             patch("host_gs._is_compiled_graph", return_value=False), \
             patch("host_gs._send_message"), \
             patch.dict("sys.modules", {
                 "p67_sdk": MagicMock(),
                 "p67_sdk.cortex_context": cortex_mod,
             }):
            with pytest.raises(SystemExit):
                host_gs.main()

        assert not (tmp_path / "result.json").exists()
        assert (tmp_path / "hitl.json").exists()
