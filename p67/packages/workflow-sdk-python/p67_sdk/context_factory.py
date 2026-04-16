"""
context_factory.py — Environment-aware ``AutomationContext`` factory.

Detects whether the code is running inside SPCS/GS (``SNOWFLAKE_HOST`` env var
is set) and returns the appropriate backend:

- **SPCS/GS**: returns ``CortexContext`` — credentials come from the OAuth
  token file mounted by SPCS.  No external config is required or used.
- **Local/controld**: returns ``LocalBackend(WorkflowSDK(config))`` — the
  Snowflake connection is configured via the ``config`` manifest dict.

**Detection signal** — ``SNOWFLAKE_HOST``:
  ``SNOWFLAKE_HOST`` is the canonical environment variable injected by the SPCS
  platform into every container at startup (e.g.
  ``myaccount.snowflakecomputing.com``).  Its presence is the single reliable
  signal that the code is running inside a managed SPCS job.  Checking for the
  OAuth token file alone would be insufficient because developers sometimes
  mount a token file locally for testing.

**Lazy imports**:
  ``CortexContext``, ``LocalBackend``, and ``WorkflowSDK`` are imported
  *inside* the function body rather than at module level.  This prevents
  import-time failures in environments where only one of the two dependency
  sets is installed (e.g. a controld environment where
  ``snowflake-connector-python`` is absent, or an SPCS image where the
  WorkflowSDK Go bridge is not present).

Usage::

    from p67_sdk.context_factory import create_context

    ctx = create_context()  # auto-detects environment
    rows = ctx.query("SELECT 1 AS n")

Or with an explicit config dict for local/testing use::

    ctx = create_context(config={
        "snowflakeConfig": {
            "default": {
                "account": "myaccount",
                "username": "myuser",
                "token": "...",
                "accessUrl": "myaccount.snowflakecomputing.com",
            }
        }
    })
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from p67_sdk.automation_context import AutomationContext

logger = logging.getLogger(__name__)


def create_context(
    config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> AutomationContext:
    """Create the appropriate ``AutomationContext`` for the current environment.

    Detection logic:

    - If the ``SNOWFLAKE_HOST`` environment variable is set the code is running
      inside SPCS or GS; a ``CortexContext`` is returned (credentials are read
      from the SPCS-mounted token file at runtime).
    - Otherwise a ``LocalBackend`` wrapping a ``WorkflowSDK`` instance is
      returned, suitable for local development and controld-managed runs.

    Args:
        config: Optional manifest config dict for the ``WorkflowSDK``.  Only
                used in the local/controld path.  Ignored when running in SPCS.
        **kwargs: Forwarded to the backend constructor.  For ``CortexContext``
                  the recognised keys are ``account``, ``host``,
                  ``token_path``, ``secrets_dir``.

    Returns:
        A concrete ``AutomationContext`` instance ready to use.

    Examples::

        # Auto-detect (recommended for production code)
        ctx = create_context()

        # Explicit config for local testing
        ctx = create_context(config={"snowflakeConfig": {"default": {...}}})
    """
    if os.environ.get("SNOWFLAKE_HOST"):
        # SNOWFLAKE_HOST is injected by the SPCS platform at container startup.
        # Its presence is the canonical signal that we are inside a managed SPCS
        # job.  Import CortexContext lazily to avoid pulling in
        # snowflake-connector-python in environments where it is not installed.
        logger.debug(
            "SNOWFLAKE_HOST is set — using CortexContext (SPCS/GS environment)"
        )
        from p67_sdk.cortex_context import CortexContext  # lazy import

        return CortexContext(**kwargs)

    # No SNOWFLAKE_HOST → running locally or under controld.
    # Import WorkflowSDK and LocalBackend lazily; the Go-backed WorkflowSDK
    # bridge is only available in the controld / local runner environment, not
    # in the SPCS image.
    logger.debug(
        "SNOWFLAKE_HOST is not set — using LocalBackend (local/controld environment)"
    )
    from p67_sdk.sdk import WorkflowSDK  # lazy import
    from p67_sdk.local_backend import LocalBackend  # lazy import

    sdk = WorkflowSDK(config or {})
    return LocalBackend(sdk, **kwargs)
