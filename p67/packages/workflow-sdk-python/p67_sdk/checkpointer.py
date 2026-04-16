"""
checkpointer.py — SnowflakeCheckpointer for LangGraph checkpoint persistence.

Implements LangGraph's BaseCheckpointSaver protocol backed by Snowflake
Hybrid Tables. Used by the Cortex Automation runner to persist graph state
across HITL checkpoint-and-release cycles and for run resumption.

The 4 backing tables are created by AutomationHybridTableBootstrapper (Java/GS):
  - _cortex_automation_checkpoints
  - _cortex_automation_checkpoint_blobs
  - _cortex_automation_checkpoint_writes
  - _cortex_automation_run_history

Requires: langgraph-checkpoint >= 2.0
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional, Sequence

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

logger = logging.getLogger("cortex_checkpointer")

# Table names (must match AutomationHybridTableBootstrapper.java)
CHECKPOINTS_TABLE = "_cortex_automation_checkpoints"
BLOBS_TABLE = "_cortex_automation_checkpoint_blobs"
WRITES_TABLE = "_cortex_automation_checkpoint_writes"


class SnowflakeCheckpointer(BaseCheckpointSaver):
    """LangGraph checkpoint saver backed by Snowflake Hybrid Tables.

    Uses a CortexContext (or MockCortexContext) for all SQL execution,
    inheriting its OAuth token refresh and connection management.

    Usage inside the automation runner::

        from p67_sdk.cortex_context import CortexContext
        from p67_sdk.checkpointer import SnowflakeCheckpointer

        ctx = CortexContext()
        checkpointer = SnowflakeCheckpointer(ctx)
        graph = my_graph.compile(checkpointer=checkpointer)

    For local testing::

        from p67_sdk.mock_cortex_context import MockCortexContext
        from p67_sdk.checkpointer import SnowflakeCheckpointer

        ctx = MockCortexContext(account="...", user="...", password="...")
        checkpointer = SnowflakeCheckpointer(ctx)
    """

    serde = JsonPlusSerializer()

    def __init__(self, ctx: Any, *, schema: str | None = None) -> None:
        """Initialize the checkpointer.

        Args:
            ctx: A CortexContext or MockCortexContext instance.
            schema: Optional schema prefix for table names (e.g. "mydb.myschema").
                    If provided, tables are qualified as schema.table_name.
                    If None, uses the connection's current schema.
        """
        super().__init__()
        self._ctx = ctx
        self._prefix = f"{schema}." if schema else ""

    def _table(self, name: str) -> str:
        return f"{self._prefix}{name}"

    # ------------------------------------------------------------------
    # BaseCheckpointSaver protocol
    # ------------------------------------------------------------------

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        """Load a checkpoint by config.

        If checkpoint_id is specified in config["configurable"], loads that
        exact checkpoint. Otherwise loads the latest checkpoint for the
        given thread_id (run_id).
        """
        configurable = config.get("configurable", {})
        run_id = configurable.get("thread_id", "")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")

        if checkpoint_id:
            rows = self._ctx.query(
                f"SELECT checkpoint_id, parent_checkpoint_id, type, "
                f"checkpoint, metadata "
                f"FROM {self._table(CHECKPOINTS_TABLE)} "
                f"WHERE run_id = :1 AND checkpoint_ns = :2 "
                f"AND checkpoint_id = :3",
                {"1": run_id, "2": checkpoint_ns, "3": checkpoint_id},
            )
        else:
            rows = self._ctx.query(
                f"SELECT checkpoint_id, parent_checkpoint_id, type, "
                f"checkpoint, metadata "
                f"FROM {self._table(CHECKPOINTS_TABLE)} "
                f"WHERE run_id = :1 AND checkpoint_ns = :2 "
                f"ORDER BY created_at DESC LIMIT 1",
                {"1": run_id, "2": checkpoint_ns},
            )

        if not rows:
            return None

        row = rows[0]
        cp_id = row["CHECKPOINT_ID"]

        # Deserialize checkpoint from BINARY
        checkpoint_bytes = row["CHECKPOINT"]
        if isinstance(checkpoint_bytes, str):
            checkpoint_bytes = checkpoint_bytes.encode("latin-1")
        checkpoint: Checkpoint = self.serde.loads_typed(
            (row.get("TYPE") or "json", checkpoint_bytes)
        )

        # Deserialize metadata
        metadata_raw = row["METADATA"]
        if isinstance(metadata_raw, str):
            import json
            metadata_raw = json.loads(metadata_raw)
        metadata = CheckpointMetadata(**metadata_raw) if isinstance(metadata_raw, dict) else CheckpointMetadata()

        # Load channel versions (blobs)
        blob_rows = self._ctx.query(
            f"SELECT channel, version, type, blob "
            f"FROM {self._table(BLOBS_TABLE)} "
            f"WHERE run_id = :1 AND checkpoint_ns = :2",
            {"1": run_id, "2": checkpoint_ns},
        )
        channel_versions: ChannelVersions = {}
        for br in blob_rows:
            channel_versions[br["CHANNEL"]] = br["VERSION"]

        # Load pending writes for this checkpoint
        write_rows = self._ctx.query(
            f"SELECT task_id, channel, type, blob, idx "
            f"FROM {self._table(WRITES_TABLE)} "
            f"WHERE run_id = :1 AND checkpoint_ns = :2 "
            f"AND checkpoint_id = :3 "
            f"ORDER BY idx",
            {"1": run_id, "2": checkpoint_ns, "3": cp_id},
        )
        pending_writes = []
        for wr in write_rows:
            blob_bytes = wr["BLOB"]
            if isinstance(blob_bytes, str):
                blob_bytes = blob_bytes.encode("latin-1")
            value = self.serde.loads_typed((wr.get("TYPE") or "json", blob_bytes))
            pending_writes.append((wr["TASK_ID"], wr["CHANNEL"], value))

        result_config = {
            "configurable": {
                "thread_id": run_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": cp_id,
            }
        }
        parent_config = None
        if row.get("PARENT_CHECKPOINT_ID"):
            parent_config = {
                "configurable": {
                    "thread_id": run_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row["PARENT_CHECKPOINT_ID"],
                }
            }

        return CheckpointTuple(
            config=result_config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    def list(
        self,
        config: Optional[dict],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints for a given thread/run, newest first."""
        configurable = (config or {}).get("configurable", {})
        run_id = configurable.get("thread_id", "")
        checkpoint_ns = configurable.get("checkpoint_ns", "")

        sql = (
            f"SELECT checkpoint_id, parent_checkpoint_id, type, "
            f"checkpoint, metadata, created_at "
            f"FROM {self._table(CHECKPOINTS_TABLE)} "
            f"WHERE run_id = :1 AND checkpoint_ns = :2"
        )
        bindings: dict[str, Any] = {"1": run_id, "2": checkpoint_ns}

        if before:
            before_id = before.get("configurable", {}).get("checkpoint_id")
            if before_id:
                sql += " AND created_at < (SELECT created_at FROM " \
                       f"{self._table(CHECKPOINTS_TABLE)} " \
                       "WHERE run_id = :1 AND checkpoint_ns = :2 " \
                       "AND checkpoint_id = :3)"
                bindings["3"] = before_id

        sql += " ORDER BY created_at DESC"

        if limit:
            sql += f" LIMIT {int(limit)}"

        rows = self._ctx.query(sql, bindings)

        for row in rows:
            cp_id = row["CHECKPOINT_ID"]
            checkpoint_bytes = row["CHECKPOINT"]
            if isinstance(checkpoint_bytes, str):
                checkpoint_bytes = checkpoint_bytes.encode("latin-1")
            checkpoint: Checkpoint = self.serde.loads_typed(
                (row.get("TYPE") or "json", checkpoint_bytes)
            )

            metadata_raw = row["METADATA"]
            if isinstance(metadata_raw, str):
                import json
                metadata_raw = json.loads(metadata_raw)
            metadata = CheckpointMetadata(**metadata_raw) if isinstance(metadata_raw, dict) else CheckpointMetadata()

            result_config = {
                "configurable": {
                    "thread_id": run_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": cp_id,
                }
            }
            parent_config = None
            if row.get("PARENT_CHECKPOINT_ID"):
                parent_config = {
                    "configurable": {
                        "thread_id": run_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["PARENT_CHECKPOINT_ID"],
                    }
                }

            yield CheckpointTuple(
                config=result_config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
            )

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict:
        """Persist a checkpoint and its channel blobs.

        Returns the updated config with the new checkpoint_id.
        """
        configurable = config.get("configurable", {})
        run_id = configurable.get("thread_id", "")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_id = configurable.get("checkpoint_id")

        # Serialize checkpoint to bytes
        type_str, cp_bytes = self.serde.dumps_typed(checkpoint)
        if isinstance(cp_bytes, str):
            cp_bytes = cp_bytes.encode("utf-8")

        # Serialize metadata
        import json
        metadata_json = json.dumps(
            metadata if isinstance(metadata, dict) else {}
        )

        # MERGE checkpoint (upsert)
        self._ctx.query(
            f"MERGE INTO {self._table(CHECKPOINTS_TABLE)} AS tgt "
            f"USING (SELECT :1 AS run_id, :2 AS checkpoint_ns, "
            f":3 AS checkpoint_id, :4 AS parent_checkpoint_id, "
            f":5 AS type, TO_BINARY(:6, 'HEX') AS checkpoint, "
            f"PARSE_JSON(:7) AS metadata) AS src "
            f"ON tgt.run_id = src.run_id "
            f"AND tgt.checkpoint_ns = src.checkpoint_ns "
            f"AND tgt.checkpoint_id = src.checkpoint_id "
            f"WHEN MATCHED THEN UPDATE SET "
            f"tgt.checkpoint = src.checkpoint, "
            f"tgt.metadata = src.metadata, "
            f"tgt.parent_checkpoint_id = src.parent_checkpoint_id "
            f"WHEN NOT MATCHED THEN INSERT "
            f"(run_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, "
            f"type, checkpoint, metadata) "
            f"VALUES (src.run_id, src.checkpoint_ns, src.checkpoint_id, "
            f"src.parent_checkpoint_id, src.type, src.checkpoint, src.metadata)",
            {
                "1": run_id,
                "2": checkpoint_ns,
                "3": checkpoint_id,
                "4": parent_id or "",
                "5": type_str,
                "6": cp_bytes.hex(),
                "7": metadata_json,
            },
        )

        # Write channel version blobs
        for channel, version in new_versions.items():
            channel_value = checkpoint["channel_values"].get(channel)
            if channel_value is not None:
                blob_type, blob_bytes = self.serde.dumps_typed(channel_value)
                if isinstance(blob_bytes, str):
                    blob_bytes = blob_bytes.encode("utf-8")

                self._ctx.query(
                    f"MERGE INTO {self._table(BLOBS_TABLE)} AS tgt "
                    f"USING (SELECT :1 AS run_id, :2 AS checkpoint_ns, "
                    f":3 AS channel, :4 AS version, :5 AS type, "
                    f"TO_BINARY(:6, 'HEX') AS blob) AS src "
                    f"ON tgt.run_id = src.run_id "
                    f"AND tgt.checkpoint_ns = src.checkpoint_ns "
                    f"AND tgt.channel = src.channel "
                    f"AND tgt.version = src.version "
                    f"WHEN MATCHED THEN UPDATE SET "
                    f"tgt.type = src.type, tgt.blob = src.blob "
                    f"WHEN NOT MATCHED THEN INSERT "
                    f"(run_id, checkpoint_ns, channel, version, type, blob) "
                    f"VALUES (src.run_id, src.checkpoint_ns, src.channel, "
                    f"src.version, src.type, src.blob)",
                    {
                        "1": run_id,
                        "2": checkpoint_ns,
                        "3": channel,
                        "4": version,
                        "5": blob_type,
                        "6": blob_bytes.hex(),
                    },
                )

        return {
            "configurable": {
                "thread_id": run_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: dict,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Persist pending writes for conflict detection.

        Each write is a (channel, value) pair from a single task execution.
        """
        configurable = config.get("configurable", {})
        run_id = configurable.get("thread_id", "")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id", "")

        for idx, (channel, value) in enumerate(writes):
            type_str, blob_bytes = self.serde.dumps_typed(value)
            if isinstance(blob_bytes, str):
                blob_bytes = blob_bytes.encode("utf-8")

            self._ctx.query(
                f"MERGE INTO {self._table(WRITES_TABLE)} AS tgt "
                f"USING (SELECT :1 AS run_id, :2 AS checkpoint_ns, "
                f":3 AS checkpoint_id, :4 AS task_id, :5 AS idx, "
                f":6 AS channel, :7 AS type, "
                f"TO_BINARY(:8, 'HEX') AS blob) AS src "
                f"ON tgt.run_id = src.run_id "
                f"AND tgt.checkpoint_ns = src.checkpoint_ns "
                f"AND tgt.checkpoint_id = src.checkpoint_id "
                f"AND tgt.task_id = src.task_id "
                f"AND tgt.idx = src.idx "
                f"WHEN MATCHED THEN UPDATE SET "
                f"tgt.channel = src.channel, tgt.type = src.type, "
                f"tgt.blob = src.blob "
                f"WHEN NOT MATCHED THEN INSERT "
                f"(run_id, checkpoint_ns, checkpoint_id, task_id, idx, "
                f"channel, type, blob) "
                f"VALUES (src.run_id, src.checkpoint_ns, src.checkpoint_id, "
                f"src.task_id, src.idx, src.channel, src.type, src.blob)",
                {
                    "1": run_id,
                    "2": checkpoint_ns,
                    "3": checkpoint_id,
                    "4": task_id,
                    "5": idx,
                    "6": channel,
                    "7": type_str,
                    "8": blob_bytes.hex(),
                },
            )
