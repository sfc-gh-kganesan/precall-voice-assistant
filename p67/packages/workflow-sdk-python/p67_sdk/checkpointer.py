"""
checkpointer.py — SnowflakeCheckpointer for LangGraph checkpoint persistence.

Implements LangGraph's ``BaseCheckpointSaver`` protocol backed by Snowflake
Hybrid Tables.  Used by the Cortex Automation runner to persist graph state
across HITL checkpoint-and-release cycles and for run resumption.

**Deployment constraint**: This module only executes inside SPCS containers
managed by the Cortex Automation runner.  It requires a live ``CortexContext``
(or ``MockCortexContext``) for SQL execution and cannot be used in local dev
mode.

---

**Hybrid Table schemas** (DDL owned by ``AutomationHybridTableBootstrapper.java``):

``_cortex_automation_checkpoints``
  Primary checkpoint record — one row per ``(run_id, checkpoint_ns,
  checkpoint_id)``.  Stores the full serialised LangGraph ``Checkpoint`` dict
  as a BINARY column and ``CheckpointMetadata`` as a VARIANT (JSON).  The
  ``type`` column carries the serialiser type tag emitted by
  ``JsonPlusSerializer`` (e.g. ``"json"``).  ``parent_checkpoint_id`` links to
  the preceding checkpoint, enabling history traversal.

  Columns::

    run_id               VARCHAR   -- LangGraph thread_id / automation run UUID
    checkpoint_ns        VARCHAR   -- LangGraph namespace (empty string for root graph)
    checkpoint_id        VARCHAR   -- UUID assigned by LangGraph at each graph step
    parent_checkpoint_id VARCHAR   -- UUID of preceding checkpoint (empty if first)
    type                 VARCHAR   -- serialiser type tag from JsonPlusSerializer
    checkpoint           BINARY    -- serialised Checkpoint dict (see serialisation note)
    metadata             VARIANT   -- CheckpointMetadata as JSON
    created_at           TIMESTAMP -- server-side insertion timestamp (used for ordering)

``_cortex_automation_checkpoint_blobs``
  Per-channel value blobs — one row per ``(run_id, checkpoint_ns, channel,
  version)``.  LangGraph assigns a monotonically increasing ``version`` token
  to each distinct channel value.  Keeping blobs in a separate table means only
  the *changed* channels produce new rows on each ``put()`` call; unchanged
  channel versions simply reference their existing blob row.

  Columns::

    run_id        VARCHAR
    checkpoint_ns VARCHAR
    channel       VARCHAR -- LangGraph channel name (e.g. ``"messages"``, ``"__root__"``)
    version       VARCHAR -- monotonic version token from LangGraph's channel versioning
    type          VARCHAR -- serialiser type tag
    blob          BINARY  -- serialised channel value

``_cortex_automation_checkpoint_writes``
  Pending writes — one row per ``(run_id, checkpoint_ns, checkpoint_id,
  task_id, idx)``.  Records intermediate task outputs that have been emitted by
  a node but not yet folded into the next full checkpoint.  LangGraph uses
  these rows for conflict detection and exactly-once delivery when the runner
  resumes after a crash: on restart, writes that were persisted here are
  replayed rather than re-executed.  ``idx`` preserves the original ordering of
  writes within a single task execution.

  Columns::

    run_id        VARCHAR
    checkpoint_ns VARCHAR
    checkpoint_id VARCHAR -- the checkpoint *before* these writes (not yet folded in)
    task_id       VARCHAR -- LangGraph task UUID
    idx           INTEGER -- write index within the task (0-based, for ordering)
    channel       VARCHAR -- destination channel name
    type          VARCHAR -- serialiser type tag
    blob          BINARY  -- serialised write value

``_cortex_automation_run_history``
  Run lifecycle metadata — owned and written exclusively by the GS runner
  (Java).  Not written by this Python module.  Contains run status
  (``RUNNING`` / ``WAITING_FOR_HUMAN`` / ``COMPLETED`` / ``FAILED``),
  timestamps, input/output payloads, and HITL action metadata.

---

**Serialisation** (BINARY columns):

``JsonPlusSerializer.dumps_typed(value)`` returns ``(type_tag, bytes_or_str)``.
The bytes value is hex-encoded via ``bytes.hex()`` and stored in Snowflake
using ``TO_BINARY(:N, 'HEX')``.  Hex transport avoids binary framing issues
with the Python connector's parameter binding.

On read, the Snowflake Python connector returns BINARY columns as ``bytes``
objects.  In some connector versions the value arrives as a latin-1 string
(a transparent byte→char mapping); the code defensively re-encodes any ``str``
via ``.encode("latin-1")`` before passing the raw bytes to
``serde.loads_typed()``.

---

**MERGE upsert pattern** (idempotency):

All write operations use ``MERGE … WHEN MATCHED THEN UPDATE … WHEN NOT MATCHED
THEN INSERT`` rather than plain ``INSERT``.  This guarantees idempotency: if
the SPCS container crashes *after* writing to Hybrid Tables but *before*
signalling GS, the runner restarts and replays the same ``put()`` call.  The
MERGE overwrites the existing row instead of raising a duplicate-key error.
Hybrid Tables enforce the primary-key constraint referenced in the ``ON``
clause, so the key lookup is index-backed.

---

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

        # Deserialize checkpoint from BINARY.
        # The connector normally returns BINARY as bytes, but some versions
        # return a latin-1 str (transparent byte→char encoding).  Re-encode
        # to bytes before passing to serde.loads_typed().
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

        # Load channel versions (blobs).
        # All blob rows for this (run_id, checkpoint_ns) are fetched; blobs are
        # keyed by channel name and the latest version is used to reconstruct the
        # channel_versions dict that LangGraph needs for conflict detection.
        blob_rows = self._ctx.query(
            f"SELECT channel, version, type, blob "
            f"FROM {self._table(BLOBS_TABLE)} "
            f"WHERE run_id = :1 AND checkpoint_ns = :2",
            {"1": run_id, "2": checkpoint_ns},
        )
        channel_versions: ChannelVersions = {}
        for br in blob_rows:
            channel_versions[br["CHANNEL"]] = br["VERSION"]

        # Load pending writes for this checkpoint.
        # Pending writes are outputs produced by node executions that have been
        # persisted to _cortex_automation_checkpoint_writes but not yet folded
        # into a new checkpoint via put().  LangGraph uses them for exactly-once
        # delivery on resume.  Ordered by idx to reconstruct original emit order.
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

        # Serialize checkpoint to bytes.
        # dumps_typed returns (type_tag, bytes_or_str).  Normalise to bytes
        # so .hex() is always available.
        type_str, cp_bytes = self.serde.dumps_typed(checkpoint)
        if isinstance(cp_bytes, str):
            cp_bytes = cp_bytes.encode("utf-8")

        # Serialize metadata
        import json
        metadata_json = json.dumps(
            metadata if isinstance(metadata, dict) else {}
        )

        # MERGE checkpoint (upsert).
        # MERGE is used instead of INSERT to guarantee idempotency.  If the
        # SPCS container crashes after writing but before notifying GS, the
        # runner restarts and replays this exact put() call.  The MERGE
        # overwrites the existing row rather than raising a primary-key error.
        # cp_bytes.hex() converts bytes to a hex string; TO_BINARY(:N, 'HEX')
        # converts it back to Snowflake BINARY on the server side.
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

        # Write channel version blobs.
        # Only channels in new_versions (i.e. those whose value changed in this
        # step) produce new blob rows.  Each (channel, version) pair is unique;
        # MERGE handles the rare case where the same version is written twice
        # (container restart).
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

        Each write is a ``(channel, value)`` pair emitted by a single task
        execution (one LangGraph node run).  These rows live in
        ``_cortex_automation_checkpoint_writes`` and are associated with the
        *current* checkpoint (the one recorded in ``config["configurable"]
        ["checkpoint_id"]``).

        On the next ``put()`` call, LangGraph folds these writes into the new
        checkpoint and they are superseded.  If the container crashes before
        the next ``put()``, these rows allow the runner to reconstruct the
        pending outputs and avoid re-executing the node.

        ``idx`` is the write's position within this task; preserved so that
        multi-write tasks can be replayed in the correct order.
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
