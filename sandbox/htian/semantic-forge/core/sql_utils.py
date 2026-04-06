from __future__ import annotations

import re

_UNQUOTED_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_IDENTIFIER_LENGTH = 255

ALLOWED_CORTEX_MODELS = frozenset(
    {
        "openai-gpt-4.1",
        "openai-gpt-4",
        "claude-3-5-sonnet",
        "claude-3-opus",
        "mistral-large",
        "mistral-large2",
        "llama3.1-70b",
        "llama3.1-405b",
        "snowflake-arctic",
        "reka-flash",
        "reka-core",
        "jamba-instruct",
        "gemma-7b",
    }
)


class SQLSafetyError(Exception):
    pass


def validate_identifier(name: str, identifier_type: str = "identifier") -> str:
    if not name:
        raise SQLSafetyError(f"Empty {identifier_type} name")
    if len(name) > _MAX_IDENTIFIER_LENGTH:
        raise SQLSafetyError(
            f"{identifier_type} name exceeds maximum length of {_MAX_IDENTIFIER_LENGTH}: {name[:50]}..."
        )
    dangerous_chars = [";", "--", "/*", "*/", "'", '"', "\\", "\x00"]
    for char in dangerous_chars:
        if char in name:
            raise SQLSafetyError(f"Invalid character in {identifier_type} name: {repr(char)}")
    return name


def quote_identifier(name: str, identifier_type: str = "identifier") -> str:
    validate_identifier(name, identifier_type)
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def build_fqn(database: str, schema: str, table: str) -> str:
    return (
        f"{quote_identifier(database, 'database')}"
        f".{quote_identifier(schema, 'schema')}"
        f".{quote_identifier(table, 'table')}"
    )


def validate_cortex_model(model: str) -> str:
    if model not in ALLOWED_CORTEX_MODELS:
        raise SQLSafetyError(
            f"Invalid Cortex model: {model}. Allowed models: {', '.join(sorted(ALLOWED_CORTEX_MODELS))}"
        )
    return model


def escape_string_literal(value: str) -> str:
    value = value.replace("\x00", "")
    return value.replace("'", "''")
