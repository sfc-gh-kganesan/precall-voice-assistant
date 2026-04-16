#!/usr/bin/env python3
"""
host_gs.py — GS-aware Python host for the SPCS runner container.

One-shot execution model: reads configuration from environment variables,
imports the user's automation entrypoint, executes it, and writes results
to stdout / P67_RESULTS_DIR. No IPC loop, no stdin reading.

Environment variables (set by GS/SPCS):
    SNOWFLAKE_HOST          Snowflake account host
    SNOWFLAKE_ACCOUNT       Snowflake account identifier
    AUTOMATION_RUN_ID       Unique run identifier (used as LangGraph thread_id)
    AUTOMATION_NAME         FQN of the automation object
    AUTOMATION_INPUT        JSON-encoded input payload (optional)
    AUTOMATION_ENTRYPOINT   module:attribute (e.g. "main:app" or "main:main")
    P67_RESULTS_DIR         Directory for result files (read by Go runner)

Exit codes:
    0   success
    1   execution error
   42   HITL pause (HumanActionInterrupt) — not a crash

LangGraph entrypoint requirements:
    Export an uncompiled StateGraph to get SnowflakeCheckpointer wired
    automatically (enables HITL checkpoint-and-release). If you export a
    CompiledStateGraph the host invokes it as-is without a checkpointer;
    HITL will not be available in that case.

Stdout redirect:
    After the entrypoint is imported, sys.stdout is redirected to sys.stderr
    so that user print() calls do not corrupt the JSON IPC channel on real
    stdout (sys.__stdout__). sys.stdout is restored before emitting the final
    result message.

Result files (written to P67_RESULTS_DIR, read back by the Go runner):
    result.json  — serialized return value on success (exit 0)
    error.json   — {"error": ..., "message": ..., "traceback": ...} on failure (exit 1)
    hitl.json    — HumanActionInterrupt metadata on HITL pause (exit 42)
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import os
import sys
import traceback
from typing import Any

# Exit code the Go runner and GS interpret as a HITL pause, not a crash.
EXIT_HITL = 42

WORKFLOW_DIR = "/workflow"
AUTOMATION_TOML = os.path.join(WORKFLOW_DIR, "automation.toml")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Write a timestamped diagnostic line to stderr."""
    print(f"[host_gs] {msg}", file=sys.__stderr__, flush=True)


def _write_results_file(name: str, data: Any) -> None:
    """Write a JSON file to P67_RESULTS_DIR if the env var is set."""
    results_dir = os.environ.get("P67_RESULTS_DIR", "")
    if not results_dir:
        return
    try:
        os.makedirs(results_dir, exist_ok=True)
        path = os.path.join(results_dir, name)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as exc:
        _log(f"warning: could not write {name} to results dir: {exc}")


def _send_message(msg: dict) -> None:
    """Emit a JSON IPC message to real stdout (captured by Go runner)."""
    sys.__stdout__.write(json.dumps(msg) + "\n")
    sys.__stdout__.flush()


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def _validate_config() -> None:
    """Parse automation.toml for validation only; failures are non-fatal warnings."""
    if not os.path.exists(AUTOMATION_TOML):
        return
    try:
        from p67_sdk.automation_config import validate_automation_toml

        with open(AUTOMATION_TOML, "r") as f:
            content = f.read()
        validate_automation_toml(content)
        _log("automation.toml validated OK")
    except Exception as exc:
        _log(f"warning: automation.toml validation failed: {exc}")


# ---------------------------------------------------------------------------
# Entrypoint import
# ---------------------------------------------------------------------------

def _import_entrypoint(entrypoint: str) -> Any:
    """Import module:attribute from /workflow and return the attribute.

    Supports dotted module paths, e.g. "automations.triage.graph:app"
    maps to /workflow/automations/triage/graph.py.

    Args:
        entrypoint: String in 'module:attribute' format.

    Returns:
        The resolved attribute object.

    Raises:
        ValueError: If the format is wrong.
        ImportError: If the module file cannot be found or loaded.
        AttributeError: If the attribute does not exist on the module.
    """
    if ":" not in entrypoint:
        raise ValueError(
            f"AUTOMATION_ENTRYPOINT '{entrypoint}' must be 'module:attribute' format"
        )
    module_path, attr_name = entrypoint.rsplit(":", 1)

    # Make /workflow importable for relative imports within the workflow package.
    if WORKFLOW_DIR not in sys.path:
        sys.path.insert(0, WORKFLOW_DIR)

    # Resolve dotted path to filesystem path.
    module_file = os.path.join(
        WORKFLOW_DIR, module_path.replace(".", os.sep) + ".py"
    )
    if not os.path.exists(module_file):
        raise ImportError(f"Entrypoint module file not found: {module_file}")

    spec = importlib.util.spec_from_file_location(module_path, module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {module_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    if not hasattr(module, attr_name):
        raise AttributeError(
            f"Module '{module_path}' has no attribute '{attr_name}'"
        )
    return getattr(module, attr_name)


# ---------------------------------------------------------------------------
# LangGraph detection helpers (lazy — langgraph may not be installed)
# ---------------------------------------------------------------------------

def _is_state_graph(obj: Any) -> bool:
    """Return True if obj is an uncompiled LangGraph StateGraph."""
    try:
        from langgraph.graph.state import StateGraph

        return isinstance(obj, StateGraph)
    except ImportError:
        return False


def _is_compiled_graph(obj: Any) -> bool:
    """Return True if obj is a LangGraph CompiledStateGraph."""
    try:
        from langgraph.graph.state import CompiledStateGraph

        return isinstance(obj, CompiledStateGraph)
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Execution strategies
# ---------------------------------------------------------------------------

def _run_graph(graph_obj: Any, ctx: Any, input_data: dict, run_id: str) -> Any:
    """Compile (if needed) and invoke a LangGraph graph.

    - StateGraph: compiled with SnowflakeCheckpointer for full HITL support.
    - CompiledStateGraph: invoked directly; checkpointer was fixed at
      compile time and cannot be re-added here.

    Args:
        graph_obj: StateGraph or CompiledStateGraph instance.
        ctx: CortexContext instance.
        input_data: Initial graph state dict.
        run_id: Automation run ID used as LangGraph thread_id.

    Returns:
        Final graph state dict returned by graph.invoke().
    """
    if _is_state_graph(graph_obj):
        from p67_sdk.checkpointer import SnowflakeCheckpointer

        _log("StateGraph detected — compiling with SnowflakeCheckpointer")
        checkpointer = SnowflakeCheckpointer(ctx)
        graph = graph_obj.compile(checkpointer=checkpointer)
    else:
        _log(
            "CompiledStateGraph detected — invoking without recompile. "
            "HITL requires exporting an uncompiled StateGraph."
        )
        graph = graph_obj

    lg_config = {"configurable": {"thread_id": run_id}}
    return graph.invoke(input_data, config=lg_config)


def _call_function(fn: Any, ctx: Any, input_data: dict) -> Any:
    """Invoke a plain callable entrypoint with arity detection.

    Supported signatures:
        fn(ctx)               — single-argument form
        fn(ctx, input_data)   — two-argument form

    Async functions are run via asyncio.run().

    Args:
        fn: Callable automation entrypoint.
        ctx: CortexContext instance.
        input_data: Parsed input payload.

    Returns:
        Return value of fn.
    """
    try:
        sig = inspect.signature(fn)
        n_params = len(sig.parameters)
    except (ValueError, TypeError):
        n_params = 1  # safe default

    if n_params >= 2:
        result = fn(ctx, input_data)
    else:
        result = fn(ctx)

    if inspect.isawaitable(result):
        import asyncio

        result = asyncio.run(result)

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _log("GS host starting")

    # --- Required environment variables ---
    entrypoint = os.environ.get("AUTOMATION_ENTRYPOINT", "").strip()
    if not entrypoint:
        _log("fatal: AUTOMATION_ENTRYPOINT is not set")
        _send_message({
            "type": "ThrowError",
            "error": "MissingEntrypoint",
            "message": "AUTOMATION_ENTRYPOINT environment variable is not set",
        })
        sys.exit(1)

    run_id = os.environ.get("AUTOMATION_RUN_ID", "unknown-run")
    automation_name = os.environ.get("AUTOMATION_NAME", "")
    input_raw = os.environ.get("AUTOMATION_INPUT", "")

    _log(f"run_id={run_id} automation={automation_name} entrypoint={entrypoint}")

    # --- Parse input payload ---
    input_data: dict = {}
    if input_raw:
        try:
            parsed = json.loads(input_raw)
            input_data = parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError as exc:
            _log(f"warning: AUTOMATION_INPUT is not valid JSON: {exc}; treating as empty")

    # --- Validate automation.toml (non-fatal) ---
    _validate_config()

    # --- Import user entrypoint ---
    try:
        _log(f"importing entrypoint: {entrypoint}")
        entrypoint_obj = _import_entrypoint(entrypoint)
        _log("import OK")
    except Exception as exc:
        tb = traceback.format_exc()
        _log(f"import error: {exc}\n{tb}")
        _send_message({
            "type": "ThrowError",
            "error": "IndexScriptImportError",
            "message": str(exc),
        })
        _write_results_file(
            "error.json",
            {"error": "IndexScriptImportError", "message": str(exc)},
        )
        sys.exit(1)

    # --- Create CortexContext ---
    from p67_sdk.cortex_context import CortexContext, HumanActionInterrupt

    ctx = CortexContext()

    # --- Redirect user stdout → stderr so print() doesn't pollute IPC stdout ---
    sys.stdout = sys.stderr

    # --- Execute ---
    try:
        if _is_state_graph(entrypoint_obj) or _is_compiled_graph(entrypoint_obj):
            _log("executing as LangGraph graph")
            result = _run_graph(entrypoint_obj, ctx, input_data, run_id)
        elif callable(entrypoint_obj):
            _log("executing as plain function")
            result = _call_function(entrypoint_obj, ctx, input_data)
        else:
            raise TypeError(
                f"Entrypoint '{entrypoint}' is neither callable nor a LangGraph graph "
                f"(got {type(entrypoint_obj).__name__})"
            )
    except HumanActionInterrupt as hitl:
        sys.stdout = sys.__stdout__
        _log(f"HumanActionInterrupt: {hitl.prompt}")
        hitl_meta = {
            "type": "HumanActionInterrupt",
            "run_id": hitl.run_id,
            "prompt": hitl.prompt,
            "payload": hitl.payload,
            "notify": hitl.notify,
            "timeout_hours": hitl.timeout_hours,
        }
        _send_message(hitl_meta)
        _write_results_file("hitl.json", hitl_meta)
        sys.exit(EXIT_HITL)
    except Exception as exc:
        sys.stdout = sys.__stdout__
        tb = traceback.format_exc()
        _log(f"execution error: {exc}\n{tb}")
        _send_message({
            "type": "ThrowError",
            "error": "ExecutionError",
            "message": str(exc),
        })
        _write_results_file(
            "error.json",
            {"error": "ExecutionError", "message": str(exc), "traceback": tb},
        )
        sys.exit(1)

    # --- Restore stdout and emit result ---
    sys.stdout = sys.__stdout__

    # Automation code may override the result via ctx.output().
    if ctx._output_value is not None:
        result = ctx._output_value

    _log("execution complete")
    _send_message({"type": "result", "data": result})
    _write_results_file("result.json", result)
    sys.exit(0)


if __name__ == "__main__":
    main()
