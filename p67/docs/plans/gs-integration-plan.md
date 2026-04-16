# Cortex Automations — GS Integration Plan

> **Status**: Draft — Internal Planning Document  
> **Last Updated**: 2026-04-10  
> **Companion docs**: `cortex-automations-prd.md`, `cortex-automations-tdd.md`, `gs-integration-product-considerations.md`  
> **Source**: Deep research across the Snowflake monorepo (GlobalServices, ExecPlatform), P67 codebase, Glean/Slack, and design docs. This document is intended to serve as the source material for both the PRD and engineering design doc.

---

## TL;DR — VStage and What It Means for Us

**VStage (Versioned Stage)** is Snowflake's internal git-like versioned file storage system. It is the **recommended and modern** way to store file-based content for any Snowflake entity — replacing the deprecated `FileBasedEntity` framework. 20 products already use it (Notebooks, Streamlits, Cortex Agents, Workspaces, DBT Projects, etc.).

**What it is:** A metadata layer (backed by `VstageVersionDPO` in FDB) on top of a regular internal Snowflake stage. It adds immutable committed versions (`VERSION$1`, `VERSION$2`, ...), mutable live versions for iterative editing, named aliases, file manifests, and background cleanup — all managed by the framework.

**What it means for Cortex Automations:**
- Workflow code (graph.py, automation.toml, requirements.txt) is stored as VStage versions
- Each `cortex automation deploy` creates a new immutable committed version
- Users manage versions via `SHOW VERSIONS`, aliases (`--tag v1.0`), and `SET DEFAULT_VERSION`
- SPCS containers mount workflow code via `snow://automation/<name>` URLs — same mechanism Notebooks and Streamlits use
- Rollback is instant: `ALTER AUTOMATION SET DEFAULT_VERSION = 'VERSION$1'`
- No user-managed staging or path management — the platform handles it

**Why VStage over a plain stage:**
- **Immutability** — committed versions cannot be modified, guaranteeing reproducibility
- **Built-in versioning** — `SHOW VERSIONS` works without us building anything
- **File manifest in FDB** — fast file enumeration without cloud LIST API calls
- **SPCS-compatible** — `snow://` URL mounting already works for VStage-backed entities
- **Future git integration** — VStage has full push/pull/merge/3-way-conflict-resolution built in (just flip a registry flag when we want GitHub sync)
- **Replication-ready** — directory-table-based cross-region replication

**Why VStage over the deprecated FileBasedEntity (what Models use):**
- `FileBasedEntity` is `@Deprecated` with explicit guidance: *"use VstageFileBasedEntity instead"*
- FBE has no named versioning, no SHOW VERSIONS, no git integration, no conflict resolution
- FBE is an abstract class (consumes single-inheritance slot); VStage is a composable Java interface
- Model is the last major holdout on FBE — no migration planned

**Tradeoffs / limitations:**
- VStage commits add ~200-300ms for directory table refresh (being optimized by FBE team)
- One mutating operation per VStage at a time (IN_PROGRESS_SLICE mutex) — acceptable for sequential deploys
- File manifest DPO capped at 2MB (overflows to stage file at ~65K files — not a concern for workflow bundles)
- HITL checkpoint-and-release requires a new SPCS cold start on resume (~30-90s latency)

**Key contacts:** Core App Objects team — Mo Eseifan, Ron Sun, Gary Ren, Defa Sun. Slack: `#file-based-entities`.

---

## Architecture: P67 Today vs GS-Managed

### P67 Today

```
User → Native App (controld service) → EXECUTE JOB SERVICE → p67-runner container
         │                                                        │
         ├─ Workflow storage: Postgres + local block volume        ├─ Reads workflow from @stage mount
         ├─ State: Postgres (WorkflowRun, WorkflowInterrupt)      ├─ Executes LangGraph StateGraph
         ├─ Secrets: Snowflake SECRET objects mounted via SPCS     ├─ Writes results to @stage
         └─ Spec construction: controld builds YAML inline        └─ Exits (ephemeral)
```

- **controld** is a long-running Fastify HTTP server that orchestrates everything
- **p67-runner** is already ephemeral (launched via `EXECUTE JOB SERVICE`)
- Workflows are ZIP bundles (TypeScript or Python)
- State lives in Postgres — no graph-level checkpointing
- HITL works via NDJSON IPC over stdin/stdout — not supported in SPCS mode

### GS-Managed (Target)

```
User → SQL DDL / CALL → GS (CortexAutomation entity) → SPCS ephemeral job → runner container
         │                                                                        │
         ├─ Workflow code: VStage (versioned, immutable commits)                  ├─ Reads from snow:// mount
         ├─ Execution state: Hybrid Tables (checkpoints + run history)            ├─ Executes LangGraph StateGraph
         ├─ Configuration: CortexAutomationDPO (compute, secrets, EAIs)           ├─ Checkpoints after each node
         ├─ Secrets: Snowflake SECRET objects (same mechanism)                    ├─ Writes results to Hybrid Table
         └─ Spec construction: GS builds SnowserviceSpec in Java                 └─ Exits (ephemeral)
```

---

## Key Architectural Decisions

### 1. VStage for Code Storage, DPO for Configuration

Workflow code and configuration are **separate concerns** with different change frequencies:

| Concern | Where It Lives | Changed By | Creates New Version? |
|---|---|---|---|
| Workflow code (graph.py, modules, data) | VStage versions | `cortex automation deploy` / `ALTER ADD VERSION` | Yes |
| automation.toml (entrypoint, runtime) | VStage versions (inside the bundle) | Redeploy | Yes |
| Compute pool, secrets, EAIs, execute_as | `CortexAutomationDPO` fields | `ALTER AUTOMATION SET ...` | No |
| Default version pointer | `vstageDefaultVersion` on stage DPO | `ALTER AUTOMATION SET DEFAULT_VERSION` | No |
| Git SHA / deploy tag | Version alias + custom metadata on VstageVersionDPO | Set at deploy time | No (metadata on existing version) |

### 2. New Entity on VStage (Not Piggyback on Model or Agent)

Cortex Automations is a **new schema-level entity** implementing `VstageFileBasedEntity`:

- `CortexAutomation` extends `BaseDictionaryEntity` directly (no `FileBasedEntity`)
- Implements `VstageFileBasedEntity` interface (~5 methods)
- Registered in `VstageFileBasedEntityRegistry` with capability flags
- Follows the **CortexAgent pattern** exactly — thin DPO, content in VStage

Why not reuse Model or Agent:
- Model uses the deprecated `FileBasedEntity` with `ModelVersion`/`BaseCommit` versioning — conflicts with VStage
- Agent stores a single YAML file; automations store multi-file bundles
- A clean entity avoids all legacy baggage

### 3. Ephemeral SPCS Jobs

Workflow execution uses `SnowserviceType.JOB` (run-to-completion), matching P67's current model. The SPCS job infrastructure provides lifecycle management, job history, and sync/async execution natively.

### 4. Execution Identity — `EXECUTE AS` Service Role

Per the TDD: automations run under an `EXECUTE AS '<service_role>'` clause specified at CREATE time. This is **definer's rights** — the service role governs all data access, Agent invocations, and tool calls. The caller's identity is used only for authorization to invoke the automation.

### 5. Compute Pool — Three-Level Override Chain

```
Platform default (CORTEX_AUTOMATIONS_DEFAULT_COMPUTE_POOL parameter)
  ↓ overridden by
Entity property (CREATE/ALTER AUTOMATION ... COMPUTE_POOL = '...')
  ↓ overridden by
Invocation parameter (CALL automation({..., 'compute_pool': '...'}))
```

The DPO stores the owner's default. The platform parameter provides the fallback. Invocation overrides for edge cases. This keeps compute out of the mandatory DDL while still allowing control.

### 6. State Management — Hybrid Tables

Per the TDD (decided 2026-04-01): all checkpoint state, run metadata, and run logs stored in **Snowflake Hybrid Tables**, per-account. This enables:
- Customer-owned, SQL-queryable execution state
- LangGraph `SnowflakeCheckpointer` (custom `BaseCheckpointSaver` impl)
- HITL suspend/resume with full state preservation
- No in-container Postgres dependency

### 7. HITL — Checkpoint and Release (per TDD)

Per the TDD: `ctx.human_action()` checkpoints full graph state to Hybrid Table, then **releases the container entirely**. Zero resources held during suspension. Resume spins up a new container, loads checkpoint, continues from exact node boundary. This avoids the idle SPCS cost problem.

---

## Deep Dive: VStage (Versioned Stage)

### What is VStage?

VStage is Snowflake's internal **git-like versioned file storage system**, implemented entirely in Global Services (Java/FDB). It is not a new stage type — it is a metadata wrapper backed by `VstageVersionDPO` in FDB that adds versioning semantics on top of a regular internal `StageDPO`. The underlying stage is attached to a parent entity via `NestedRelationshipType.VERSIONED_STAGE` (id 39).

**Design docs:**
- [Spec: FileBasedEntity V-Stage Integration](https://docs.google.com/document/d/1yZbWH38HW0Tx4zz4k77p0VhXyevpWQrZ2EVZmTqLyLg/edit)
- [Spec: Versioned Stage Metadata & APIs](https://docs.google.com/document/d/1Co1VuaHw3R1QiuaV7yWrs3kx6F8xI7yqtuZPHH8XY3k)
- Slack channel: `#file-based-entities` (C05NLCUTL23)

### Core Concepts

| Concept | Description |
|---|---|
| **Committed Version** | Immutable snapshot. Named `VERSION$1`, `VERSION$2`, etc. Cannot be modified after commit. |
| **Live Version** | Mutable working copy for iterative editing. Where PUT/RM operations happen. |
| **Checkpoint Version** | Zero-copy save point of a live version. TTL-managed (default 30 days). |
| **Version Shortcuts** | `FIRST`, `LAST`, `DEFAULT`, `LIVE`, `HEAD`, `GIT_HEAD` |
| **File Manifest** | JSON in FDB tracking every file's path, checksum, size. Eliminates cloud LIST for committed versions. |
| **putRank** | Counter per PUT/RM. Each PUT gets its own sub-folder — no overwrites in cloud storage. |

### VStage vs Plain Stages vs Deprecated FBE

| Dimension | Plain Stage | FileBasedEntity (deprecated) | VStage |
|---|---|---|---|
| **Versioning** | None | Ad-hoc checkout/commit | Named versions, aliases, FIRST/LAST/DEFAULT |
| **Immutability** | Overwritable | Overwritable | Committed versions immutable |
| **File enumeration** | Cloud LIST (slow) | Cloud LIST | FDB manifest (fast) for committed versions |
| **SHOW VERSIONS** | N/A | N/A | Built-in |
| **Git integration** | N/A | N/A | Full push/pull/merge/conflict resolution |
| **Multi-user** | Flat namespace | Single namespace | Per-user LIVE versions |
| **Framework status** | Active | `@Deprecated` | Active, recommended |
| **Adoption** | Universal | Model (last holdout) | 20 domains |

### How Cortex Agent Uses VStage (Our Pattern)

CortexAgent is the exact pattern we follow:
- Extends `BaseDictionaryEntity`, implements `VstageFileBasedEntity`
- Thin DPO (`CortexAgentDPO`) — only `profile` field. Spec lives in VStage as `agent_spec.yaml`.
- On CREATE: VStage created, VERSION$1 committed with the spec, LIVE version from LAST
- SHOW VERSIONS returns one row per version with `created_on`, `name`, `alias`, `is_default`
- Cortex Automations: same pattern but storing **multi-file bundles** instead of a single YAML

### VStage Domain Registration — Capability Flags

| Capability | Setting | Rationale |
|---|---|---|
| VStage enabled | `param(ENABLE_CORTEX_AUTOMATIONS)` | Feature gate |
| SHOW VERSIONS | `true` | Users need to see deployed versions |
| SHOW CHANGES | `false` | Not useful for whole-bundle deploys |
| Git ops (push/pull) | `false` V1, `param` later | Future: sync code from GitHub |
| Conflict resolution | `false` | No concurrent editing in V1 |
| Directory table | `param` | Needed for replication |
| DT replication | `param` | Cross-region support |
| LIVE version support | `param` (disabled V1) | V2: visual editor and vibe builder need iterative editing |

### VStage File Layout for Automations

```
<vstage-root>/
  versions/
    <versionId_1>/                ← VERSION$1 (committed)
      automation.toml
      automations/
        ticket_triage/
          graph.py
          requirements.txt
    <versionId_2>/                ← VERSION$2 (committed)
      automation.toml
      automations/
        ticket_triage/
          graph.py                ← updated code
          requirements.txt
```

The runner container sees files at `/mnt/workflow/` with the `versions/<id>/` prefix stripped. It reads `automation.toml` to find the entrypoint.

### `automation.toml` Schema

```toml
[automation]
name       = "ticket_triage"                          # required — must match entity name
entrypoint = "automations.ticket_triage.graph:app"    # required — Python module:attribute path
runtime    = "1.0"                                    # required — runtime version pin

# Optional: Git Integration for SHA capture (alternative to local `git rev-parse HEAD`)
# git_integration = "mydb.myschema.my_git_integration"

[secrets]
# key = "db.schema.secret_name" — key is what code sees via ctx.secret("key")
slack_token    = "mydb.myschema.slack_secret"
sendgrid_token = "mydb.myschema.sendgrid_secret"

[compute]
# Optional: pin to a named SPCS compute pool.
# Omit to use the platform default. Overridable at invocation time.
# pool = "my_regulated_pool"
```

| Field | Block | Required | Stored In | Changed By |
|---|---|---|---|---|
| `name` | `[automation]` | Yes | VStage (in bundle) | Redeploy |
| `entrypoint` | `[automation]` | Yes | VStage (in bundle) | Redeploy |
| `runtime` | `[automation]` | Yes | VStage (in bundle) | Redeploy |
| `git_integration` | `[automation]` | No | VStage (in bundle) | Redeploy |
| Secret bindings | `[secrets]` | No | DPO (parsed at deploy, also settable via `ALTER SET SECRETS`) | `ALTER` or redeploy |
| Compute pool | `[compute]` | No | DPO (parsed at deploy, also settable via `ALTER SET COMPUTE_POOL`) | `ALTER` or redeploy |

### Secrets Binding Flow

```
1. Developer writes automation.toml:
   [secrets]
   slack_token = "mydb.myschema.slack_secret"

2. CLI: `cortex automation deploy`
   → parses [secrets] block
   → stages files to @stage
   → calls CREATE/ALTER AUTOMATION ... SECRETS = (slack_token = mydb.myschema.slack_secret)

3. GS: ExecCreateAutomation
   → stores key→FQN mapping on CortexAutomationDPO.secrets field (JSON)
   → validates EXECUTE AS role has READ on each SECRET object
   → stores workflow files in VStage VERSION$N

4. GS: CALL automation(input)
   → AutomationJobSpecBuilder reads DPO.secrets
   → for each key→FQN: adds SPCS file-mount secret entry
       directoryPath: /opt/creds/<key>/      ← mounted by SPCS platform
   → container starts with secrets as files at /opt/creds/slack_token/secret_string

5. Runtime: ctx.secret("slack_token")
   → reads /opt/creds/slack_token/secret_string
   → returns plaintext value

Note: ctx.secret() must NOT persist the returned value to graph state.
      If it does, the secret leaks into checkpoint Hybrid Tables.
```

---

## CortexContext API Reference

The `ctx` object is injected into every node function as a keyword-only argument: `def my_node(state: MyState, *, ctx: CortexContext) -> dict`.

| Method | Signature | Returns | Notes |
|---|---|---|---|
| `ctx.query()` | `(sql: str, bindings: dict = {})` | `list[dict]` | Parameterized binding required for state-derived values |
| `ctx.query_df()` | `(sql: str, bindings: dict = {})` | `pandas.DataFrame` | Row limit enforced (default 100K); raises `ResultSetTooLargeError` |
| `ctx.complete()` | `(model: str, prompt: str, **kwargs)` | `str \| dict` | Cortex LLM inference |
| `ctx.search()` | `(service: str, query: str, limit: int = 10)` | `list[dict]` | Cortex Search |
| `ctx.analyst()` | `(semantic_view: str, question: str)` | `dict` | Cortex Analyst |
| `ctx.http()` | `(method: str, url: str, headers: dict = {}, body: dict = {})` | `dict` | Requires EAI; SPCS only until Apps Cluster EAI ships |
| `ctx.agent()` | `(agent_name: str, message: str, thread_id: str = None, timeout_seconds: int = 120)` | `str` | Requires `GRANT USAGE ON AGENT` to service role. Rate-limited. |
| `ctx.automation()` | `(automation_name: str, input: dict, await: bool = True)` | `str \| dict` | Sub-automation invocation |
| `ctx.human_action()` | `(prompt: str, payload: dict = {}, notify: dict = {}, timeout_hours: int = 24)` | `dict` | Checkpoints state, releases container. `notify` keys: `slack_channel`, `email`, `pagerduty_url` |
| `ctx.secret()` | `(name: str)` | `str` | Reads from /opt/creds/<name>/secret_string. Must NOT be persisted to state. |
| `ctx.emit()` | `(event: str, data: dict = {})` | `None` | Custom OTel span to customer event table |
| `ctx.output()` | `(value: dict)` | `None` | Declares the run's return value. Durably staged to `pending_output` immediately. |

---

## Checkpoint Schema (from TDD)

```sql
CREATE HYBRID TABLE automation_checkpoints (
    run_id          TEXT NOT NULL,
    checkpoint_ns   TEXT NOT NULL,        -- LangGraph namespace (empty for top-level)
    checkpoint_id   TEXT NOT NULL,        -- ULID, monotonically increasing
    parent_id       TEXT,                 -- Previous checkpoint (time-travel chain)
    state           VARIANT NOT NULL,     -- Full serialized graph state (JSON only, no pickle)
    metadata        VARIANT NOT NULL,     -- Node name, step number, timing
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (run_id, checkpoint_ns, checkpoint_id)
);

CREATE HYBRID TABLE automation_checkpoint_writes (
    run_id          TEXT NOT NULL,
    checkpoint_ns   TEXT NOT NULL,
    checkpoint_id   TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    idx             INTEGER NOT NULL,
    channel         TEXT NOT NULL,        -- State key being written
    type            TEXT,                 -- Serialization type tag
    blob            TEXT NOT NULL,        -- JSON-serialized value
    PRIMARY KEY (run_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
-- CRITICAL: Both tables must be written in a SINGLE Hybrid Table transaction.
-- A crash between inserts leaves pending writes without a committed checkpoint.

CREATE HYBRID TABLE automation_run_history (
    run_id              TEXT NOT NULL PRIMARY KEY,
    automation_name     TEXT NOT NULL,
    git_sha             TEXT,
    deployment_tag      TEXT,
    status              TEXT NOT NULL,     -- RUNNING, COMPLETED, FAILED, TIMED_OUT, SUSPENDED
    started_at          TIMESTAMPTZ NOT NULL,
    completed_at        TIMESTAMPTZ,
    duration_seconds    FLOAT,
    credits_used        FLOAT,
    metering_status     TEXT DEFAULT 'NOT_IMPLEMENTED',  -- NOT_IMPLEMENTED|PENDING|COMPLETE|ERROR
    error_message       TEXT,
    output              VARIANT,           -- from ctx.output() — promoted from pending_output on completion
    pending_output      VARIANT,           -- durably staged ctx.output() value (crash-safe)
    final_state         VARIANT,           -- last checkpoint state dict at END or crash
    pending_resume_payload VARIANT,        -- human's payload between CAS-win and container spin-up
    runner_image_version TEXT,
    logs_not_persisted  BOOLEAN DEFAULT FALSE,
    expires_at          TIMESTAMPTZ        -- checkpoint TTL; default NOW() + 30 days on completion
);
```

---

## What We Can Leverage

### From ML Model Serving

| Component | What We Reuse |
|---|---|
| SPCS spec builder pattern | `InferenceServiceFactory.generateServiceSpec()` — pattern for SnowserviceSpec with containers, volumes, env vars |
| ML job spec builder | `MLJobServiceSpecBuilder.java` — most directly reusable for building SPCS job specs |
| Stage mount V1/V2 | `MLJobServiceSpecBuilder.createStageVolume()` — VStage mount via `snow://` URL |
| Image resolution | `ExecuteMLJobFunctionOptions.resolveContainerImage()` — parameter-controlled image URLs |
| Sync job wait | `waitForJobCompletion()` — block SQL session until ephemeral job completes |
| Kaniko pipeline (V3) | `BuildModelContainer.java` — custom image builds with layer caching |
| `SpcsWorkloadType` enum | Add `CORTEX_AUTOMATION` — one line |

### From Existing GS Infrastructure

| Component | What We Reuse |
|---|---|
| SPCS job API | `IServiceContextOperation.createService()` with `isJob=true` |
| SPCS job lifecycle | Terminal state detection, job history via `SpcsJobHistoryDPO` |
| `snow://` URL mounting | `SnowserviceSpecVolumeItemInternal.getResolvedEmbeddedStage()` — handles VStage natively |
| VStage framework | `VstageFileBasedEntity` interface — versioning, manifests, cleanup for free |
| Entity framework | `BaseDictionaryEntity`, `BaseDictionaryDPO`, `DomainEnumInitializer` |
| Parameter framework | `ParameterBuilder`, auto-discovered at startup |
| DDL pipeline | `SqlCreate` → `QueryPlanNode` → `ExecNode` |
| Run tracking | `aimlopsrun/ObjectType` — add enum value, get run CRUD for free |
| Snowhouse export | `@SnowhouseExportable` annotation |

### What We Need to Build New

| Component | Complexity | Description |
|---|---|---|
| `cortex-automations-core` module | Low | GS module following `cortex-agent-core` pattern |
| `CortexAutomationDPO` | Low | Thin DPO: `executeAsRole`, `computePool`, `secrets`, `eais`, `runtimeVersion` |
| `CortexAutomation` entity | Low | `BaseDictionaryEntity` + `VstageFileBasedEntity`. Follow CortexAgent. |
| `CortexAutomationsParameters.java` | Low | Feature gate, default runner image, limits, compute pool default |
| `AutomationJobSpecBuilder` | Medium | Single-container SPCS job spec. VStage mount + Hybrid Table access. |
| Callable automation handler | Medium | `CALL automation(input)` dispatch — resolve entity, build spec, launch SPCS job |
| `SnowflakeCheckpointer` | High | LangGraph `BaseCheckpointSaver` backed by Hybrid Tables |
| HITL checkpoint-and-release | High | `ctx.human_action()` → checkpoint state → release container → resume on new container |
| DDL handlers | Medium | CREATE/ALTER/DROP/SHOW/DESCRIBE + parser integration |
| Hybrid Table schemas | Medium | `automation_checkpoints`, `automation_checkpoint_writes`, `automation_run_history` |
| `CortexContext` SDK | Medium | Python SDK in `snowflake-ml-python`: ctx.query(), ctx.complete(), ctx.human_action(), etc. |

---

## Pre-Phase-1 Validation Spike

These items are **load-bearing assumptions** that must be validated before Phase 1 begins. If any fails, the architecture needs rework.

| Spike | What to Validate | Pass Criteria | Named Reviewer |
|---|---|---|---|
| **`snow://` URL mount** | Register `CORTEX_AUTOMATION` domain, create a VStage, mount it in an SPCS job on local SUT | Container sees files at the mount path | Core App Objects + SPCS team |
| **DDL noun decision** | Confirm `AUTOMATION` vs `CORTEX AUTOMATION` with SQL Compiler team | Written confirmation on the keyword | SQL Compiler team |
| **EXECUTE AS role semantics** | Confirm with DBSec: creator must hold the named role, default behavior when omitted | DBSec sign-off on the identity model | DBSec |
| **Resume syntax** | Confirm feasibility of `CALL automation.resume(...)` dot-notation OR agree on alternative (`RESUME AUTOMATION ...`) | SQL Compiler written decision | SQL Compiler team |

---

## PrPr Security Gates

All must close before first internal deploy. Sourced from DBSec review feedback.

| Gate | Requirement | Risk If Skipped |
|---|---|---|
| **EXECUTE AS role constraint** | Creator must hold the named service role. Enforced in `ExecCreateAutomation`. | Privilege escalation: any CREATE AUTOMATION holder can impersonate sysadmin. |
| **EXECUTE AS default** | Explicit documented behavior when `EXECUTE AS` is omitted. | Undefined identity = unpredictable access. |
| **Secret file mounts only** | `AutomationJobSpecBuilder` uses `directoryPath` file mounts. `envVarName` path blocked. | Secrets leak via `/proc/self/environ`, exception tracebacks, log output. |
| **`ctx.query()` parameterized binding** | SDK API enforces parameterized binding. Raw SQL string interpolation blocked or linted. | SQL injection from graph state values. |
| **Resume payload validation** | Resume path validates payload structure before state injection. Unrecognized keys rejected. | Prompt injection, prototype pollution via crafted payloads. |
| **Resume caller scoping** | `run_id` validated to belong to the named automation in the named schema. | Cross-automation resume via guessed UUID. |
| **Checkpoint TTL** | Completed/failed run checkpoints purged after configurable retention (default 30 days). | Secrets/PII in checkpoint blobs persist indefinitely. |
| **Checkpoint access control** | MONITOR privilege does NOT grant access to checkpoint blob data. Blob access requires OWNERSHIP. | Secret/PII exposure to any MONITOR holder. |
| **No pickle in checkpoint path** | `SnowflakeCheckpointer.get_tuple()` deserialization uses JSON type registry only. Code-reviewed. | Arbitrary code execution via `pickle.loads`. |
| **VStage mount scope** | PoC verifies container cannot traverse above the version-scoped path to other versions. | Compromised container reads code from unintended versions. |
| **`ctx.secret()` design** | Full design required before implementation. Must include prohibition on persisting returned values to state. | Secret values flow into checkpoints and become durable. |

---

## HITL Design Constraints

### Atomicity: Checkpoint + Status Update

The HITL flow has a crash window:
1. `SnowflakeCheckpointer.put()` writes state to Hybrid Table ✓
2. `automation_run_history` updated to `status=SUSPENDED`
3. Container exits (exit code 0)

If the container crashes between steps 1 and 2, the checkpoint exists but the run is `status=RUNNING` forever. The watchdog won't know it's suspended. **Resolution required:** either atomic write covering both checkpoint and status, or a reconciliation task that detects orphaned `RUNNING` runs with existing checkpoints.

### Node Re-Execution on Resume

LangGraph does **not** resume from the middle of a Python function. On resume, the node that called `ctx.human_action()` **re-executes from the beginning**. All code before the `ctx.human_action()` call runs again.

```python
def approval_node(state, *, ctx):
    ctx.http("POST", "https://slack.com/...", ...)   # ← RUNS TWICE (original + resume)
    decision = ctx.human_action(prompt="Approve?")    # ← suspends here
    ctx.query("UPDATE ...", bindings=decision)         # ← runs once on resume
```

**Implication:** Side effects before `ctx.human_action()` must be idempotent. The SDK and documentation must make this extremely clear. Consider a `ctx.is_resuming()` check or automatic skip-on-resume for pre-HITL code.

### SPCS Exit Code Semantics

SPCS interprets exit code 0 as `DONE` (successful completion). A suspended automation exits with code 0 but is NOT done. This creates two SPCS job records for the same logical run (original job: `DONE`, resume job: separate entry). **Resolution:** either use a non-zero exit code convention for suspension, or annotate the SPCS job with suspension intent before exit.

### Concurrent HITL in a Single Graph

If a workflow has two sequential `ctx.human_action()` calls, the second suspend creates a new checkpoint on the same `run_id`. The resume path must handle: same run_id, different checkpoint_id, different interrupt payload. The current design assumes one HITL per run. **Must be explicitly designed for multi-HITL.**

### Watchdog Design Requirements

The "platform watchdog" is described in one sentence. It needs:
- **Substrate**: ATQ periodic task? GS BG service? Dedicated BG service type?
- **Scale model**: How does it handle 10,000 suspended runs across 10,000 accounts?
- **Failure modes**: At-least-once vs exactly-once semantics. Spurious timeout-resumes racing with legitimate resumes.
- **Monitoring**: Last scan time, runs scanned vs eligible vs fired, error count.
- **GS restart behavior**: Does it recover in-flight scans?

**Recommendation**: Design the watchdog as a pre-Phase-4 deliverable, not a Phase 4 sub-task.

---

## Hybrid Table Lifecycle

### Bootstrap: Who Creates the Tables?

Per-account Hybrid Tables (`automation_checkpoints`, `automation_checkpoint_writes`, `automation_run_history`) must be created before any automation can run. Options:

| Option | Pros | Cons |
|---|---|---|
| Lazy creation (first `CREATE AUTOMATION`) | Zero pre-provisioning | First CREATE is slower; error handling if DDL fails mid-create |
| Account bootstrap (GS parameter flip) | Tables exist before any user action | Requires a provisioning BG task for existing accounts |
| First `CALL` (just-in-time) | Tables created only when actually needed | Adds latency to first run; race condition on concurrent first calls |

**Recommendation:** Lazy creation at first `CREATE AUTOMATION` time, inside the `ExecCreateAutomation` transaction. If tables already exist, no-op. This matches how other per-account infrastructure is provisioned.

### Schema: Where Do Tables Live?

Options:
- **System schema** (e.g., `SNOWFLAKE.CORTEX_AUTOMATIONS`) — platform-owned, not in user's namespace
- **Per-automation schema** (alongside the entity) — user-visible, RBAC-scoped
- **Dedicated database** (e.g., `CORTEX_AUTOMATIONS_STATE`) — isolated

**Recommendation:** System schema. Checkpoint data is platform infrastructure, not user data. User observability comes via `INFORMATION_SCHEMA` table functions.

### Schema Evolution Post-GA

When we add a column or change a type in `automation_checkpoints`, per-account Hybrid Tables don't auto-migrate. **Required mechanism:** A GS startup task or BG service that runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` on first access after upgrade. Track schema version in a metadata field on the table comment or a separate `automation_schema_version` row.

---

## Operational Safety

### Kill Switch

```sql
-- Account-level emergency brake (GS parameter, account lineage)
ALTER ACCOUNT SET CORTEX_AUTOMATIONS_SUSPENDED = TRUE;
-- Effect: CALL returns error immediately, new SPCS jobs not launched
-- In-flight jobs: allowed to drain (complete current run, no new launches)

-- Per-automation disable without DROP
ALTER AUTOMATION <name> SUSPEND;
ALTER AUTOMATION <name> RESUME;
-- Effect: CALL on suspended automation returns error
-- In-flight runs: allowed to complete
```

Without a kill switch, incident response options for a runaway automation are: `DROP AUTOMATION` (destructive) or manually killing SPCS jobs one by one. Neither is acceptable for GA.

### Runner Image Rollback

The `CORTEX_AUTOMATIONS_DEFAULT_RUNNER_IMAGE` parameter controls the image URL. Rollback procedure:
1. Identify affected runs: `SELECT * FROM automation_run_history WHERE runner_image_version = '<bad>'` (requires `runner_image_version` recorded in run history)
2. Update parameter to known-good version: `ALTER ACCOUNT SET CORTEX_AUTOMATIONS_DEFAULT_RUNNER_IMAGE = '<good>'`
3. In-flight jobs on bad image: cannot be patched; must drain or force-terminate
4. Per-automation escape hatch: `ALTER AUTOMATION SET RUNNER_IMAGE = '<pinned_good>'`

**Requirement:** Record `runner_image_version` in `automation_run_history` at run creation time.

### Internal Monitoring (Non-Customer)

Minimum viable platform alerting before GA:

| Alert | Threshold | Severity |
|---|---|---|
| `automation_run_failure_rate` | > 5% over 5-min window | Page |
| `spcs_job_launch_p99` | > 120s | Page |
| `watchdog_last_scan_age` | > 2× scan interval | Page |
| `hybrid_table_write_error_rate` | > 0 | Page |
| `suspended_runs_past_timeout` | > 0 for > 10 min | Warn |
| `checkpoint_write_p99_latency` | > 500ms | Warn |

---

## Implementation Phases (Updated with Tests + Acceptance Criteria)

### Phase 0: Validation Spike (Pre-Phase-1)

1. Validate `snow://automation/` URL mount on local SUT with SPCS + VStage team
2. Get DDL noun decision from SQL Compiler team
3. Get EXECUTE AS semantics sign-off from DBSec
4. Get resume syntax decision from SQL Compiler team
5. **SubstrateAdapter interface design** — TDD/CTO gate: must be built at PrPr, not deferred. Define the `SubstrateAdapter` Protocol with `SPCSAdapter` impl and `AppsClusterAdapter` stub (raises `NotImplementedError`).
6. **MockCortexContext validated** — TDD/CTO gate: must be validated against 2+ real internal workflows (Casper or Frostsite) before external PrPr partners see the SDK.

**Done when:** All six spikes have written decisions. SubstrateAdapter Protocol defined. MockCortexContext passes against 2+ real workflows.

### Phase 1: Entity Foundation

1. Create `cortex-automations-core` GS module
2. Register `Component.AI_CORTEX_AUTOMATIONS` + `components.yaml`
3. Register `Domain.CORTEX_AUTOMATION` + `DomainEnumInitializer`
4. Create `CortexAutomationDPO` (thin — code in VStage, config on DPO)
5. Create `CortexAutomation` entity implementing `VstageFileBasedEntity`
6. Register in `VstageFileBasedEntityRegistry` (LIVE disabled, SHOW VERSIONS enabled)
7. Create `CortexAutomationsParameters.java`
8. Register module in root `BUILD.bazel`
9. **Tests:** `ComponentConsistencyTest` passes. VStage creation + version creation on local SUT.

**Done when:** `CREATE AUTOMATION ... AS '@stage/'` creates an entity with VERSION$1 on local SUT. `SHOW VERSIONS` returns the version. `ComponentConsistencyTest` passes.

### Phase 2: DDL Pipeline

1. Parser: `KW_AUTOMATION` case in `CreateParser.java`
2. `SqlCreateAutomation` parse tree node (supports `AS '@stage/path/'` and `FROM SPECIFICATION $$...$$`)
3. `QueryPlanNodeCreateAutomation` + `CodeGenerator` visitor
4. `ExecCreateAutomation` — creates entity + VStage with initial committed version
5. `ExecAlterAutomation` — SET COMPUTE_POOL, SET SECRETS, SET DEFAULT_VERSION, ADD VERSION, RENAME, SUSPEND/RESUME
6. SHOW/DESCRIBE: switch-case additions across resolver/exec files
7. `CortexAutomationDDLGenerator` for `GET_DDL()`
8. **Tests:** DDL unit tests, GSIT for all DDL operations, security privilege enforcement tests.

**Done when:** Full DDL lifecycle works on local SUT. `GET_DDL()` round-trips. Privilege matrix enforced.

**Note:** Callable dispatch (`CALL automation(input)`) moves to Phase 3 — it depends on SPCS job infrastructure.

### Phase 3: SPCS Job Integration + State Management

1. Add `CORTEX_AUTOMATION` to `SpcsWorkloadType` + `SnowserviceOrigin`
2. Create `AutomationJobSpecBuilder` (VStage mount, Hybrid Table access, secrets as file mounts, EAIs)
3. Implement callable dispatch: `CALL automation(input)` and `CALL automation(input) ASYNC`
4. Bootstrap Hybrid Table schemas on first `CREATE AUTOMATION`
5. Implement `SnowflakeCheckpointer` — LangGraph `BaseCheckpointSaver` backed by Hybrid Tables
6. Wire version resolution: entity → VStage DEFAULT version → `snow://` URL in SPCS spec
7. Add `CORTEX_AUTOMATION` to `aimlopsrun/ObjectType` for run tracking
8. Record `runner_image_version` in `automation_run_history`
9. Implement `INFORMATION_SCHEMA.AUTOMATION_RUN_HISTORY` and `INFORMATION_SCHEMA.AUTOMATION_CHECKPOINTS` table functions
10. **Tests:** Job spec builder unit tests, SnowflakeCheckpointer unit tests, E2E: CREATE → CALL → checkpoint → complete on SUT with SPCS.

**Done when:** `CALL automation(input)` launches an SPCS job, executes a LangGraph graph, checkpoints per-node, and returns a result.

### Phase 4: HITL + CortexContext SDK

1. Design watchdog subsystem (pre-implementation design doc)
2. Implement `ctx.human_action()` — checkpoint state, set status=SUSPENDED, exit container
3. Implement resume path — load checkpoint, spin new container, inject payload into state
4. Compare-and-swap on checkpoint table for exactly-once resume
5. Implement platform watchdog for timeout-based resume
6. Implement `CortexContext` Python SDK: ctx.query(), ctx.query_df(), ctx.complete(), ctx.search(), ctx.analyst(), ctx.agent(), ctx.automation(), ctx.http(), ctx.human_action(), ctx.secret(), ctx.emit(), ctx.output()
7. Implement typed exception hierarchy: `CortexAgentPermissionError`, `CortexAgentRateLimitError`, `AutomationAlreadyResumedError`, `ResultSetTooLargeError`, `CheckpointWriteFailedError`, `SecretNotFoundError`, etc.
8. Implement `cortex automation doctor` — 5 pre-flight checks (entity exists, service role exists, secrets resolve, checkpoint tables exist, compute pool status). Required before external PrPr.
9. Handle SPCS OAuth token refresh mid-execution (tokens expire after 1 hour)
10. **Tests:** HITL full cycle (execute → suspend → resume → complete). Multi-HITL test. Timeout test. CAS contention test. SDK method unit tests. Doctor command tests.

**Done when:** E2E: CALL → HITL suspend → container released → resume → new container → completes. Watchdog fires timeout correctly.

### Phase 5: Webhook Triggers + Dashboard

1. Table-stream triggered task pattern for event-driven execution
2. `TRIGGER_EVENT_LOG`-based automation triggers (extend event type allowlist)
3. Snowsight dashboard: automation list, version management, run monitoring, HITL interrupt UI
4. **Tests:** Trigger integration tests. Dashboard E2E.

**Done when:** An INSERT into a trigger table causes an automation to execute. Dashboard shows runs and HITL queue.

### Phase 6: Operational Readiness + Regression

1. Internal monitoring/alerting wired (see alerting table above)
2. Kill switch tested (account-level + per-automation SUSPEND/RESUME)
3. Runner image rollback procedure documented and tested
4. Snowfort regression suite: `t_cortex_automations/`
5. Load tests: concurrent runs, HITL polling at scale, VStage version cleanup
6. Security audit: all PrPr gates verified
7. Operational runbooks written

**Done when:** All PrPr security gates pass. Alerting fires on failure injection. Runbooks reviewed by oncall team.

### Future Work

- **LIVE version support** — enable VStage LIVE for visual editor and vibe builder (param flip)
- Custom image building via Kaniko (user-provided `requirements.txt`)
- Git integration for workflow source (VStage push/pull from GitHub)
- Multi-node parallel workflow execution
- Apps Cluster substrate support (full `AppsClusterAdapter` impl)
- `AutomationEvaluator` — evaluation framework for automation quality
- Non-LangGraph callable path with degraded checkpointing (GA scope)
- `INFORMATION_SCHEMA.AUTOMATION_LOGS` stable view

---

## Appendix: PRD/TDD Alignment Gaps

Items specified in the PRD or TDD that are not yet fully covered in this plan. Each needs resolution via this doc, a separate design doc, or an explicit deferral decision.

| # | Gap | Severity | Status | Resolution |
|---|---|---|---|---|
| 1 | `automation.toml` full schema | P0 | **Added** | ✅ In this doc |
| 2 | CortexContext full API signatures | P0 | **Added** | ✅ In this doc |
| 3 | Typed Python exception hierarchy (12 types) | P0 | **Added to Phase 4** | ✅ |
| 4 | Checkpoint schema full DDL | P0 | **Added** | ✅ In this doc |
| 5 | Two-table atomic checkpoint write | Critical | Noted in schema | Needs design doc |
| 6 | `entrypoint()` injection model (keyword-only `ctx`) | P0 | Not covered | SDK design doc |
| 7 | Git SHA capture flow (local git vs Git Integration) | P1 | Partial | CLI design doc |
| 8 | INFORMATION_SCHEMA table functions | P0 | **Added to Phase 3** | ✅ |
| 9 | Task integration semantics (retry, overlap, HITL async) | Critical | Not covered | Needs section |
| 10 | SubstrateAdapter abstraction | PrPr gate | **Promoted to Phase 0** | ✅ |
| 11 | OpenTelemetry span definitions (12 spans) | P1 | Not covered | SDK design doc |
| 12 | `ctx.agent()` rate limits | PrPr gate | Not covered | Cortex Agent team |
| 13 | Non-LangGraph path (degraded checkpointing) | GA | Not covered | GA scope decision |
| 14 | `ctx.output()` / `final_state` / `pending_output` | P0 | **Added** | ✅ In schema + API |
| 15 | stdout/stderr capture (fd-level, scrubbing, rate limit) | P1 | Not covered | Runner design doc |
| 16 | SPCS OAuth token expiry mid-execution | Critical | **Added to Phase 4** | ✅ |
| 17 | Watchdog full specification | P0 | Partial | Pre-Phase-4 design doc |
| 18 | CAS SQL pattern (UPDATE-WHERE, not TOCTOU) | P1 | Concept present | Needs specification |
| 19 | MockCortexContext (CTO gate) | PrPr gate | **Promoted to Phase 0** | ✅ |
| 20 | Resume payload durability (`pending_resume_payload`) | P1 | **Added** | ✅ In schema |
| 21 | Checkpoint retention mechanism (`expires_at`) | P2 | **Added** | ✅ In schema + security |
| 22 | Synchronous CALL return type (one-way door) | One-way door | Not covered | Phase 2 decision |
| 23 | `cortex automation doctor` command | P0 for PrPr | **Added to Phase 4** | ✅ |
| 24 | `INFORMATION_SCHEMA.AUTOMATION_LOGS` stable view | P1 | Not covered | Pre-PrPr decision |
| 25 | `requirements.txt` lock file / supply chain | P2 | Not covered | CLI design doc |
| 26 | `metering_status` column | One-way door | **Added** | ✅ In schema |
| 27 | Multi-HITL sequence numbering | P1 | Partial | Needs specification |

**Summary:** 16 of 27 gaps resolved (✅). 11 remaining need separate design docs or decisions.

---

## Key Files to Reference

| File | Purpose |
|---|---|
| `GS/modules/cortex/cortex-agent-core/.../CortexAgent.java` | Entity pattern (VstageFileBasedEntity) |
| `GS/modules/cortex/cortex-agent-core/.../CortexAgentDPO.java` | DPO pattern (thin, spec in VStage) |
| `GS/modules/apps/versionedstage-impl/.../VstageFileBasedEntityRegistry.java` | VStage consumer registration |
| `GS/modules/apps/versionedstage-api/.../VstageFileBasedEntity.java` | VStage interface to implement |
| `GS/src/.../semantic/functions/mlruntime/utils/MLJobServiceSpecBuilder.java` | SPCS job spec builder pattern |
| `GS/src/.../semantic/functions/model/InferenceServiceFactory.java` | SPCS service spec builder |
| `GS/src/.../semantic/functions/model/BuildModelContainer.java` | Kaniko image build (future) |
| `GS/modules/ml/platform/ml-platform-core/.../aimlopsrun/ObjectType.java` | Run tracking extension point |
| `GS/modules/platform/core/.../Component.java` | Component registration |
| `GS/modules/platform/core/.../Domain.java` | Domain registration |
| `GS/src/.../sql/execution/ExecCreateAgent.java` | DDL execution pattern |
| `GS/modules/snowservices/.../SnowserviceType.java` | SERVICE vs JOB distinction |
| `GS/modules/data-platform/task-impl/.../TriggeringEventTriggerServiceUtil.java` | Event-log trigger pattern |
