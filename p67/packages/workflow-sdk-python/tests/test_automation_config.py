"""Tests for automation_config.py — automation.toml parser and validator."""

import warnings

import pytest

from p67_sdk.automation_config import (
    AutomationConfig,
    AutomationConfigError,
    validate_automation_toml,
)

# --- Valid configs ---

VALID_MINIMAL = """
[automation]
name       = "ticket_triage"
entrypoint = "automations.ticket_triage.graph:app"
runtime    = "1.0"
"""

VALID_FULL = """
[automation]
name       = "ticket_triage"
entrypoint = "automations.ticket_triage.graph:app"
runtime    = "1.0"

[secrets]
slack_token = "mydb.myschema.slack_secret"
jira_creds  = "mydb.myschema.jira_secret"

[compute]
pool = "my_regulated_pool"

[external_access]
integrations = ["slack_eai", "jira_eai"]
"""

VALID_NO_OPTIONAL = """
[automation]
name       = "simple_auto"
entrypoint = "main:run"
runtime    = "1.0"
"""


class TestValidConfigs:
    def test_minimal_config(self):
        config = validate_automation_toml(VALID_MINIMAL)
        assert config.name == "ticket_triage"
        assert config.entrypoint == "automations.ticket_triage.graph:app"
        assert config.runtime == "1.0"
        assert config.secrets == {}
        assert config.compute_pool is None
        assert config.external_access_integrations == []

    def test_full_config(self):
        config = validate_automation_toml(VALID_FULL)
        assert config.name == "ticket_triage"
        assert config.entrypoint == "automations.ticket_triage.graph:app"
        assert config.runtime == "1.0"
        assert config.secrets == {
            "slack_token": "mydb.myschema.slack_secret",
            "jira_creds": "mydb.myschema.jira_secret",
        }
        assert config.compute_pool == "my_regulated_pool"
        assert config.external_access_integrations == ["slack_eai", "jira_eai"]

    def test_no_optional_sections(self):
        config = validate_automation_toml(VALID_NO_OPTIONAL)
        assert config.name == "simple_auto"
        assert config.entrypoint == "main:run"

    def test_returns_frozen_dataclass(self):
        config = validate_automation_toml(VALID_MINIMAL)
        assert isinstance(config, AutomationConfig)
        with pytest.raises(AttributeError):
            config.name = "changed"  # type: ignore[misc]


# --- Missing required fields ---

class TestMissingRequired:
    def test_missing_automation_section(self):
        with pytest.raises(AutomationConfigError, match="Missing required \\[automation\\]"):
            validate_automation_toml("[compute]\npool = 'x'\n")

    def test_missing_name(self):
        toml = """
[automation]
entrypoint = "main:run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="name is required"):
            validate_automation_toml(toml)

    def test_missing_entrypoint(self):
        toml = """
[automation]
name    = "test"
runtime = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="entrypoint is required"):
            validate_automation_toml(toml)

    def test_missing_runtime(self):
        toml = """
[automation]
name       = "test"
entrypoint = "main:run"
"""
        with pytest.raises(AutomationConfigError, match="runtime is required"):
            validate_automation_toml(toml)


# --- Invalid name format ---

class TestInvalidName:
    def test_uppercase_name(self):
        toml = """
[automation]
name       = "TicketTriage"
entrypoint = "main:run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="name.*invalid"):
            validate_automation_toml(toml)

    def test_name_starts_with_number(self):
        toml = """
[automation]
name       = "1bad_name"
entrypoint = "main:run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="name.*invalid"):
            validate_automation_toml(toml)

    def test_name_with_dashes(self):
        toml = """
[automation]
name       = "my-automation"
entrypoint = "main:run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="name.*invalid"):
            validate_automation_toml(toml)

    def test_empty_name(self):
        toml = """
[automation]
name       = ""
entrypoint = "main:run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="name is required"):
            validate_automation_toml(toml)


# --- Invalid entrypoint format ---

class TestInvalidEntrypoint:
    def test_no_colon(self):
        toml = """
[automation]
name       = "test"
entrypoint = "main.run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="entrypoint.*invalid"):
            validate_automation_toml(toml)

    def test_starts_with_number(self):
        toml = """
[automation]
name       = "test"
entrypoint = "1main:run"
runtime    = "1.0"
"""
        with pytest.raises(AutomationConfigError, match="entrypoint.*invalid"):
            validate_automation_toml(toml)


# --- Invalid runtime ---

class TestInvalidRuntime:
    def test_unknown_runtime(self):
        toml = """
[automation]
name       = "test"
entrypoint = "main:run"
runtime    = "2.0"
"""
        with pytest.raises(AutomationConfigError, match="runtime.*not supported"):
            validate_automation_toml(toml)


# --- Invalid secret FQN ---

class TestInvalidSecretFQN:
    def test_not_three_parts(self):
        toml = """
[automation]
name       = "test"
entrypoint = "main:run"
runtime    = "1.0"

[secrets]
my_secret = "just_a_name"
"""
        with pytest.raises(AutomationConfigError, match="secrets.*not a valid FQN"):
            validate_automation_toml(toml)

    def test_two_parts(self):
        toml = """
[automation]
name       = "test"
entrypoint = "main:run"
runtime    = "1.0"

[secrets]
my_secret = "db.name"
"""
        with pytest.raises(AutomationConfigError, match="not a valid FQN"):
            validate_automation_toml(toml)


# --- Unknown top-level keys ---

class TestUnknownKeys:
    def test_warns_on_unknown_keys(self):
        toml = """
[automation]
name       = "test"
entrypoint = "main:run"
runtime    = "1.0"

[unknown_section]
foo = "bar"
"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = validate_automation_toml(toml)
            assert len(w) == 1
            assert "Unknown top-level keys" in str(w[0].message)
        assert config.name == "test"


# --- Invalid TOML syntax ---

class TestInvalidToml:
    def test_bad_toml(self):
        with pytest.raises(AutomationConfigError, match="Invalid TOML syntax"):
            validate_automation_toml("this is not [valid toml = ")
