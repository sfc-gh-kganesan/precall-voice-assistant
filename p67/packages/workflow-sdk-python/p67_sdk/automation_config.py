"""
automation_config.py — automation.toml parser and validator for Cortex Automations.

Parses the automation.toml config file, validates all fields, and returns
a typed AutomationConfig dataclass.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        raise ImportError(
            "Python < 3.11 requires the 'tomli' package. "
            "Install with: pip install tomli"
        )


# --- Validation constants ---

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,254}$")
ENTRYPOINT_PATTERN = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*$"
)
# FQN: db.schema.name — each part is a valid SQL identifier
FQN_PATTERN = re.compile(
    r'^[a-zA-Z_][a-zA-Z0-9_$]*\.[a-zA-Z_][a-zA-Z0-9_$]*\.[a-zA-Z_][a-zA-Z0-9_$]*$'
)
KNOWN_RUNTIMES = {"1.0"}
KNOWN_TOP_KEYS = {"automation", "secrets", "compute", "external_access"}


@dataclass(frozen=True)
class AutomationConfig:
    """Validated automation configuration."""

    name: str
    entrypoint: str
    runtime: str
    secrets: dict[str, str] = field(default_factory=dict)
    compute_pool: str | None = None
    external_access_integrations: list[str] = field(default_factory=list)


class AutomationConfigError(Exception):
    """Raised when automation.toml validation fails."""

    pass


def validate_automation_toml(toml_content: str) -> AutomationConfig:
    """Parse and validate an automation.toml string.

    Args:
        toml_content: Raw TOML string content.

    Returns:
        Validated AutomationConfig.

    Raises:
        AutomationConfigError: If validation fails.
    """
    try:
        data = tomllib.loads(toml_content)
    except Exception as e:
        raise AutomationConfigError(f"Invalid TOML syntax: {e}") from e

    # Warn on unknown top-level keys (don't error — forward compat)
    unknown_keys = set(data.keys()) - KNOWN_TOP_KEYS
    if unknown_keys:
        import warnings
        warnings.warn(
            f"Unknown top-level keys in automation.toml: {unknown_keys}. "
            "These will be ignored.",
            stacklevel=2,
        )

    # --- [automation] section ---
    automation = data.get("automation")
    if not isinstance(automation, dict):
        raise AutomationConfigError(
            "Missing required [automation] section in automation.toml"
        )

    # name
    name = automation.get("name")
    if not name or not isinstance(name, str):
        raise AutomationConfigError(
            "[automation].name is required and must be a string"
        )
    if not NAME_PATTERN.match(name):
        raise AutomationConfigError(
            f"[automation].name '{name}' is invalid. "
            "Must match [a-z][a-z0-9_]{{0,254}} (lowercase, starts with letter)."
        )

    # entrypoint
    entrypoint = automation.get("entrypoint")
    if not entrypoint or not isinstance(entrypoint, str):
        raise AutomationConfigError(
            "[automation].entrypoint is required and must be a string"
        )
    if not ENTRYPOINT_PATTERN.match(entrypoint):
        raise AutomationConfigError(
            f"[automation].entrypoint '{entrypoint}' is invalid. "
            "Must be 'module.path:attribute' format (e.g., "
            "'automations.ticket_triage.graph:app')."
        )

    # runtime
    runtime = automation.get("runtime")
    if not runtime or not isinstance(runtime, str):
        raise AutomationConfigError(
            "[automation].runtime is required and must be a string"
        )
    if runtime not in KNOWN_RUNTIMES:
        raise AutomationConfigError(
            f"[automation].runtime '{runtime}' is not supported. "
            f"Known runtimes: {sorted(KNOWN_RUNTIMES)}"
        )

    # --- [secrets] section (optional) ---
    secrets_section = data.get("secrets", {})
    if not isinstance(secrets_section, dict):
        raise AutomationConfigError("[secrets] must be a table of key = FQN pairs")

    secrets: dict[str, str] = {}
    for key, fqn in secrets_section.items():
        if not isinstance(fqn, str):
            raise AutomationConfigError(
                f"[secrets].{key} must be a string (Snowflake secret FQN)"
            )
        if not FQN_PATTERN.match(fqn):
            raise AutomationConfigError(
                f"[secrets].{key} = '{fqn}' is not a valid FQN. "
                "Must be 'database.schema.secret_name' format."
            )
        secrets[key] = fqn

    # --- [compute] section (optional) ---
    compute_section = data.get("compute", {})
    if not isinstance(compute_section, dict):
        raise AutomationConfigError("[compute] must be a table")

    compute_pool = compute_section.get("pool")
    if compute_pool is not None and not isinstance(compute_pool, str):
        raise AutomationConfigError("[compute].pool must be a string if specified")

    # --- [external_access] section (optional) ---
    ea_section = data.get("external_access", {})
    if not isinstance(ea_section, dict):
        raise AutomationConfigError("[external_access] must be a table")

    integrations = ea_section.get("integrations", [])
    if not isinstance(integrations, list):
        raise AutomationConfigError(
            "[external_access].integrations must be a list of strings"
        )
    for i, item in enumerate(integrations):
        if not isinstance(item, str):
            raise AutomationConfigError(
                f"[external_access].integrations[{i}] must be a string"
            )

    return AutomationConfig(
        name=name,
        entrypoint=entrypoint,
        runtime=runtime,
        secrets=secrets,
        compute_pool=compute_pool,
        external_access_integrations=list(integrations),
    )
