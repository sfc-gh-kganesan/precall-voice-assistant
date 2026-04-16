"""
Tests for SnowflakeCheckpointer.

Uses a lightweight stub context that stores data in-memory dicts,
so tests run without a Snowflake connection or langgraph installed
beyond the checkpoint base classes.
"""

from __future__ import annotations

import json
import pytest
from typing import Any
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub context that simulates Snowflake Hybrid Table queries in-memory
# ---------------------------------------------------------------------------

class InMemoryContext:
    """Minimal CortexContext stub that stores rows in dicts keyed by table name.

    Supports INSERT via MERGE (the only DML the checkpointer uses) and
    SELECT queries. Parses the SQL just enough to route to the right table.
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            "_cortex_automation_checkpoints": [],
            "_cortex_automation_checkpoint_blobs": [],
            "_cortex_automation_checkpoint_writes": [],
            "_cortex_automation_run_history": [],
        }
        self.query_log: list[tuple[str, dict]] = []

    def query(self, sql: str, bindings: dict[str, Any] | None = None) -> list[dict]:
        bindings = bindings or {}
        self.query_log.append((sql, bindings))

        sql_upper = sql.strip().upper()

        if sql_upper.startswith("MERGE INTO"):
            return self._handle_merge(sql, bindings)
        elif sql_upper.startswith("SELECT"):
            return self._handle_select(sql, bindings)
        return []

    def _find_table(self, sql: str) -> str:
        sql_lower = sql.lower()
        for table_name in self._tables:
            if table_name in sql_lower:
                return table_name
        raise ValueError(f"Could not find table in SQL: {sql[:80]}")

    def _handle_merge(self, sql: str, bindings: dict[str, Any]) -> list[dict]:
        table_name = self._find_table(sql)
        rows = self._tables[table_name]

        # Determine primary key columns per table
        pk_map = {
            "_cortex_automation_checkpoints": ["run_id", "checkpoint_ns", "checkpoint_id"],
            "_cortex_automation_checkpoint_blobs": ["run_id", "checkpoint_ns", "channel", "version"],
            "_cortex_automation_checkpoint_writes": [
                "run_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx",
            ],
        }
        pk_cols = pk_map.get(table_name, [])

        # Build the row from bindings based on table
        new_row = self._build_row(table_name, bindings)

        # Check for existing row by PK
        existing_idx = None
        for i, existing in enumerate(rows):
            if all(existing.get(col.upper()) == new_row.get(col.upper()) for col in pk_cols):
                existing_idx = i
                break

        if existing_idx is not None:
            rows[existing_idx] = new_row
        else:
            rows.append(new_row)

        return []

    def _build_row(self, table_name: str, bindings: dict[str, Any]) -> dict[str, Any]:
        if table_name == "_cortex_automation_checkpoints":
            return {
                "RUN_ID": bindings.get("1", ""),
                "CHECKPOINT_NS": bindings.get("2", ""),
                "CHECKPOINT_ID": bindings.get("3", ""),
                "PARENT_CHECKPOINT_ID": bindings.get("4", ""),
                "TYPE": bindings.get("5", ""),
                "CHECKPOINT": bytes.fromhex(bindings.get("6", "")),
                "METADATA": json.loads(bindings.get("7", "{}")),
                "CREATED_AT": "2026-01-01T00:00:00Z",
            }
        elif table_name == "_cortex_automation_checkpoint_blobs":
            return {
                "RUN_ID": bindings.get("1", ""),
                "CHECKPOINT_NS": bindings.get("2", ""),
                "CHANNEL": bindings.get("3", ""),
                "VERSION": bindings.get("4", ""),
                "TYPE": bindings.get("5", ""),
                "BLOB": bytes.fromhex(bindings.get("6", "")),
            }
        elif table_name == "_cortex_automation_checkpoint_writes":
            return {
                "RUN_ID": bindings.get("1", ""),
                "CHECKPOINT_NS": bindings.get("2", ""),
                "CHECKPOINT_ID": bindings.get("3", ""),
                "TASK_ID": bindings.get("4", ""),
                "IDX": bindings.get("5", 0),
                "CHANNEL": bindings.get("6", ""),
                "TYPE": bindings.get("7", ""),
                "BLOB": bytes.fromhex(bindings.get("8", "")),
            }
        return {}

    def _handle_select(self, sql: str, bindings: dict[str, Any]) -> list[dict]:
        table_name = self._find_table(sql)
        rows = self._tables[table_name]

        # Filter by run_id and checkpoint_ns (bindings 1, 2)
        run_id = bindings.get("1", "")
        checkpoint_ns = bindings.get("2", "")
        filtered = [
            r for r in rows
            if r.get("RUN_ID") == run_id and r.get("CHECKPOINT_NS") == checkpoint_ns
        ]

        # Additional filter by checkpoint_id if binding 3 present and it's a
        # checkpoint or writes table query
        if "3" in bindings and table_name in (
            "_cortex_automation_checkpoints",
            "_cortex_automation_checkpoint_writes",
        ):
            cp_id = bindings["3"]
            filtered = [r for r in filtered if r.get("CHECKPOINT_ID") == cp_id]

        # Handle ORDER BY ... DESC LIMIT 1 (latest checkpoint)
        sql_upper = sql.upper()
        if "ORDER BY" in sql_upper and "DESC" in sql_upper:
            filtered = list(reversed(filtered))

        if "LIMIT 1" in sql_upper:
            filtered = filtered[:1]
        elif "LIMIT" in sql_upper:
            # Extract limit value
            import re
            m = re.search(r"LIMIT\s+(\d+)", sql_upper)
            if m:
                filtered = filtered[:int(m.group(1))]

        return filtered


# ---------------------------------------------------------------------------
# Mock langgraph types for testing without full langgraph install
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_langgraph():
    """Patch langgraph imports so tests work without langgraph installed."""
    # Create mock module structure
    base_mod = MagicMock()

    # Define real-enough types
    class FakeCheckpointTuple:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class FakeBaseCheckpointSaver:
        serde = None
        def __init__(self):
            pass

    class FakeJsonPlusSerializer:
        def dumps_typed(self, obj):
            data = json.dumps(obj).encode("utf-8")
            return ("json", data)

        def loads_typed(self, type_and_data):
            type_str, data = type_and_data
            if isinstance(data, bytes):
                return json.loads(data.decode("utf-8"))
            return json.loads(data)

    base_mod.BaseCheckpointSaver = FakeBaseCheckpointSaver
    base_mod.ChannelVersions = dict
    base_mod.Checkpoint = dict
    base_mod.CheckpointMetadata = dict
    base_mod.CheckpointTuple = FakeCheckpointTuple

    serde_mod = MagicMock()
    serde_mod.JsonPlusSerializer = FakeJsonPlusSerializer

    with patch.dict("sys.modules", {
        "langgraph": MagicMock(),
        "langgraph.checkpoint": MagicMock(),
        "langgraph.checkpoint.base": base_mod,
        "langgraph.checkpoint.serde": MagicMock(),
        "langgraph.checkpoint.serde.jsonplus": serde_mod,
    }):
        # Force re-import with mocked modules
        import importlib
        import p67_sdk.checkpointer as cp_mod
        importlib.reload(cp_mod)
        yield cp_mod


@pytest.fixture
def ctx():
    return InMemoryContext()


@pytest.fixture
def checkpointer(mock_langgraph, ctx):
    return mock_langgraph.SnowflakeCheckpointer(ctx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSnowflakeCheckpointer:

    def test_put_and_get_roundtrip(self, checkpointer, ctx):
        """Put a checkpoint then get it back — values should match."""
        config = {
            "configurable": {
                "thread_id": "run-123",
                "checkpoint_ns": "",
                "checkpoint_id": "parent-0",
            }
        }
        checkpoint = {
            "id": "cp-1",
            "channel_values": {"messages": ["hello"]},
            "channel_versions": {"messages": "v1"},
        }
        metadata = {"source": "input", "step": 0}

        result_config = checkpointer.put(
            config, checkpoint, metadata, {"messages": "v1"}
        )

        assert result_config["configurable"]["checkpoint_id"] == "cp-1"

        # Now get it back
        loaded = checkpointer.get_tuple(result_config)
        assert loaded is not None
        assert loaded.checkpoint["id"] == "cp-1"
        assert loaded.checkpoint["channel_values"]["messages"] == ["hello"]

    def test_get_tuple_returns_none_for_missing(self, checkpointer):
        """get_tuple returns None when no checkpoint exists."""
        config = {
            "configurable": {
                "thread_id": "nonexistent",
                "checkpoint_ns": "",
            }
        }
        assert checkpointer.get_tuple(config) is None

    def test_get_latest_checkpoint(self, checkpointer, ctx):
        """Without checkpoint_id, get_tuple returns the latest."""
        config_base = {
            "configurable": {
                "thread_id": "run-456",
                "checkpoint_ns": "",
            }
        }

        # Put two checkpoints
        cp1 = {"id": "cp-first", "channel_values": {}, "channel_versions": {}}
        checkpointer.put({**config_base, "configurable": {
            **config_base["configurable"], "checkpoint_id": None,
        }}, cp1, {}, {})

        cp2 = {"id": "cp-second", "channel_values": {}, "channel_versions": {}}
        checkpointer.put({**config_base, "configurable": {
            **config_base["configurable"], "checkpoint_id": "cp-first",
        }}, cp2, {}, {})

        # Get without specifying checkpoint_id → should return latest (cp-second)
        loaded = checkpointer.get_tuple(config_base)
        assert loaded is not None
        assert loaded.checkpoint["id"] == "cp-second"

    def test_put_writes(self, checkpointer, ctx):
        """put_writes stores pending writes retrievable via get_tuple."""
        # First put a checkpoint
        config = {
            "configurable": {
                "thread_id": "run-789",
                "checkpoint_ns": "",
                "checkpoint_id": None,
            }
        }
        cp = {"id": "cp-w1", "channel_values": {}, "channel_versions": {}}
        result_config = checkpointer.put(config, cp, {}, {})

        # Now put writes
        checkpointer.put_writes(
            result_config,
            [("messages", {"role": "user", "content": "hi"})],
            task_id="task-abc",
        )

        # Verify writes are stored
        writes_table = ctx._tables["_cortex_automation_checkpoint_writes"]
        assert len(writes_table) == 1
        assert writes_table[0]["TASK_ID"] == "task-abc"
        assert writes_table[0]["CHANNEL"] == "messages"

    def test_list_checkpoints(self, checkpointer, ctx):
        """list returns checkpoints in reverse chronological order."""
        config = {
            "configurable": {
                "thread_id": "run-list",
                "checkpoint_ns": "",
            }
        }

        for i in range(3):
            cp = {"id": f"cp-{i}", "channel_values": {}, "channel_versions": {}}
            checkpointer.put(
                {"configurable": {**config["configurable"], "checkpoint_id": f"cp-{i-1}" if i > 0 else None}},
                cp, {"step": i}, {},
            )

        results = list(checkpointer.list(config))
        assert len(results) == 3
        # Latest first (reversed order)
        assert results[0].checkpoint["id"] == "cp-2"
        assert results[2].checkpoint["id"] == "cp-0"

    def test_list_with_limit(self, checkpointer, ctx):
        """list respects the limit parameter."""
        config = {
            "configurable": {
                "thread_id": "run-limit",
                "checkpoint_ns": "",
            }
        }

        for i in range(5):
            cp = {"id": f"cp-{i}", "channel_values": {}, "channel_versions": {}}
            checkpointer.put(
                {"configurable": {**config["configurable"], "checkpoint_id": None}},
                cp, {}, {},
            )

        results = list(checkpointer.list(config, limit=2))
        assert len(results) == 2

    def test_schema_prefix(self, mock_langgraph):
        """When schema is provided, table names are qualified."""
        ctx = InMemoryContext()
        cp = mock_langgraph.SnowflakeCheckpointer(ctx, schema="mydb.myschema")
        assert cp._table("_cortex_automation_checkpoints") == \
            "mydb.myschema._cortex_automation_checkpoints"

    def test_put_upsert_overwrites(self, checkpointer, ctx):
        """Putting a checkpoint with the same ID overwrites the previous one."""
        config = {
            "configurable": {
                "thread_id": "run-upsert",
                "checkpoint_ns": "",
                "checkpoint_id": None,
            }
        }

        cp1 = {"id": "cp-same", "channel_values": {"x": 1}, "channel_versions": {}}
        checkpointer.put(config, cp1, {"step": 0}, {})

        cp2 = {"id": "cp-same", "channel_values": {"x": 2}, "channel_versions": {}}
        checkpointer.put(config, cp2, {"step": 1}, {})

        # Should have only 1 row (upserted)
        table = ctx._tables["_cortex_automation_checkpoints"]
        matching = [r for r in table if r["RUN_ID"] == "run-upsert"]
        assert len(matching) == 1

    def test_parent_config_populated(self, checkpointer, ctx):
        """get_tuple populates parent_config when parent_checkpoint_id exists."""
        config = {
            "configurable": {
                "thread_id": "run-parent",
                "checkpoint_ns": "",
                "checkpoint_id": "parent-cp",
            }
        }
        cp = {"id": "child-cp", "channel_values": {}, "channel_versions": {}}
        result_config = checkpointer.put(config, cp, {}, {})

        loaded = checkpointer.get_tuple(result_config)
        assert loaded is not None
        assert loaded.parent_config is not None
        assert loaded.parent_config["configurable"]["checkpoint_id"] == "parent-cp"

    def test_channel_blobs_stored(self, checkpointer, ctx):
        """put stores channel blobs for new_versions."""
        config = {
            "configurable": {
                "thread_id": "run-blobs",
                "checkpoint_ns": "",
                "checkpoint_id": None,
            }
        }
        cp = {
            "id": "cp-blob",
            "channel_values": {"messages": ["msg1", "msg2"], "state": {"k": "v"}},
            "channel_versions": {"messages": "v1", "state": "v1"},
        }
        checkpointer.put(config, cp, {}, {"messages": "v1", "state": "v1"})

        blobs = ctx._tables["_cortex_automation_checkpoint_blobs"]
        assert len(blobs) == 2
        channels = {b["CHANNEL"] for b in blobs}
        assert channels == {"messages", "state"}
