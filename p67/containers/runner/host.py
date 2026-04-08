#!/usr/bin/env python3
"""
Python workflow runtime host.

Receives RunWorkflow messages via stdin, executes Python workflows,
and communicates results back via stdout using JSON.

This is the Python equivalent of host.ts for TypeScript workflows.
"""

import sys
import json
import asyncio
import importlib.util
import inspect
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from enum import Enum


class MessageType(str, Enum):
    """Message types for IPC protocol."""
    RUN_WORKFLOW = "RunWorkflow"
    THROW_ERROR = "ThrowError"
    INTERRUPT = "Interrupt"
    RESUME_INTERRUPT = "ResumeInterrupt"
    OAUTH_TOKEN_RESPONSE = "OAuthTokenResponse"


class WorkflowError(str, Enum):
    """Workflow error types."""
    EXECUTION_ERROR = "ExecutionError"
    INDEX_SCRIPT_IMPORT_ERROR = "IndexScriptImportError"
    INDEX_SCRIPT_INVALID_CONTENTS = "IndexScriptInvalidContents"
    INDEX_SCRIPT_NOT_FOUND = "IndexScriptNotFound"
    MANIFEST_LOAD_PARSE_ERROR = "ManifestLoadParseError"
    MANIFEST_NOT_FOUND = "ManifestNotfound"
    MESSAGE_INVALID_CONTENTS = "MessageInvalidContents"
    MESSAGE_INVALID_TYPE = "MessageInvalidType"


# Track if we've started the workflow (RunWorkflow only processed once)
workflow_started = False


def send_message(msg: Dict[str, Any]) -> None:
    """Send a JSON message to stdout (parent process)."""
    sys.stdout.write(json.dumps(msg) + '\n')
    sys.stdout.flush()


def send_error(error: WorkflowError, message: str) -> None:
    """Send an error message and exit."""
    send_message({
        "type": MessageType.THROW_ERROR.value,
        "error": error.value,
        "message": message
    })
    sys.exit(1)


def read_message() -> Optional[Dict[str, Any]]:
    """Read a JSON message from stdin."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line.strip())
    except json.JSONDecodeError as e:
        send_error(WorkflowError.MESSAGE_INVALID_CONTENTS, str(e))
        return None


def handle_run_workflow(data: Dict[str, Any]) -> None:
    """Handle RunWorkflow message."""
    global workflow_started
    
    if workflow_started:
        print("RunWorkflow already processed, ignoring duplicate", file=sys.stderr)
        return
    workflow_started = True
    
    workflow_dir = data.get("dir")
    config = data.get("config", {})
    
    # Inside the runner container the workflow is bind-mounted at /workflow.
    # The dir in the message is controld's internal path which doesn't exist here.
    if os.path.isdir("/workflow"):
        workflow_dir = "/workflow"
    
    # Look for main.py in the workflow directory
    script_path = Path(workflow_dir) / "main.py"
    if not script_path.exists():
        send_error(
            WorkflowError.INDEX_SCRIPT_NOT_FOUND,
            f"{script_path} does not exist"
        )
        return
    
    # Import the workflow module
    try:
        print(f"Loading script {script_path}", file=sys.stderr)
        spec = importlib.util.spec_from_file_location("workflow", script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {script_path}")
        module = importlib.util.module_from_spec(spec)
        
        # Add the workflow directory to sys.path for relative imports
        sys.path.insert(0, str(workflow_dir))
        
        spec.loader.exec_module(module)
        print("Loaded script!", file=sys.stderr)
    except Exception as e:
        send_error(WorkflowError.INDEX_SCRIPT_IMPORT_ERROR, str(e))
        return
    
    # Check for main function
    if not hasattr(module, 'main') or not callable(module.main):
        send_error(
            WorkflowError.INDEX_SCRIPT_INVALID_CONTENTS,
            "Script does not export a main function"
        )
        return
    
    # When SECRET_BACKEND=snowflake, secrets are mounted as env vars by SPCS.
    # Resolve the env var references into the config before creating the SDK.
    secret_env_mappings = data.get("secretEnvMappings")
    if secret_env_mappings:
        for field_path, env_var_name in secret_env_mappings.items():
            value = os.environ.get(env_var_name)
            if not value:
                print(
                    f"Warning: Secret env var {env_var_name} for {field_path} is not set",
                    file=sys.stderr,
                )
                continue

            # field_path is like "config.<name>.<field>" or
            # "config.<name>.parameters.<key>"
            parts = field_path.split(".")
            if parts[0] == "config" and len(parts) >= 3:
                config_name = parts[1]
                snowflake_config = config.get("snowflakeConfig", {})
                config_entry = snowflake_config.get(config_name)
                if config_entry and isinstance(config_entry, dict):
                    if len(parts) == 3:
                        # config.<name>.<field> → direct field set
                        config_entry[parts[2]] = value
                    elif len(parts) == 4 and parts[2] == "parameters":
                        # config.<name>.parameters.<key> → nested set
                        if "parameters" not in config_entry:
                            config_entry["parameters"] = {}
                        config_entry["parameters"][parts[3]] = value

    # Create SDK and execute
    try:
        # Import the SDK - first try from the workflow directory (bundled),
        # then fall back to system installation
        workflow_sdk_path = Path(workflow_dir) / "p67_sdk"
        if workflow_sdk_path.exists():
            # Use bundled SDK from workflow directory
            sys.path.insert(0, str(workflow_dir))
            from p67_sdk import WorkflowSDK
        else:
            try:
                from p67_sdk import WorkflowSDK
            except ImportError:
                raise ImportError(
                    "p67_sdk package not found. Ensure the workflow was built with 'p67 build'"
                )
        
        # Redirect stdout to stderr so that user print() statements don't 
        # interfere with IPC messages (which use stdout)
        original_stdout = sys.stdout
        sys.stdout = sys.stderr
        
        sdk = WorkflowSDK(config)
        result = module.main(sdk)
        # If main is async, the call above returns a coroutine — run it.
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        
        # Restore stdout for sending the result message
        sys.stdout = original_stdout
        send_message({"type": "result", "data": result})
        sdk.close()
        sys.exit(0)
    except SystemExit:
        # Re-raise SystemExit to allow clean exit
        raise
    except Exception as e:
        # Restore stdout in case of exception
        sys.stdout = sys.__stdout__
        send_error(WorkflowError.EXECUTION_ERROR, str(e))


def main() -> None:
    """Main entry point for the Python runtime host."""
    print("Python runtime host started", file=sys.stderr)
    
    while True:
        message = read_message()
        if message is None:
            break
        
        msg_type = message.get("type")
        
        if msg_type == MessageType.RUN_WORKFLOW.value:
            handle_run_workflow(message)
        elif msg_type == MessageType.RESUME_INTERRUPT.value:
            # ResumeInterrupt messages are handled by the SDK's internal listener
            # Forward to SDK via a global callback mechanism
            from p67_sdk import _handle_resume_interrupt
            _handle_resume_interrupt(message)
        elif msg_type == MessageType.OAUTH_TOKEN_RESPONSE.value:
            from p67_sdk import _handle_oauth_token_response
            _handle_oauth_token_response(message)
        else:
            send_error(
                WorkflowError.MESSAGE_INVALID_TYPE,
                f"Invalid message type: {msg_type}"
            )


if __name__ == "__main__":
    main()
