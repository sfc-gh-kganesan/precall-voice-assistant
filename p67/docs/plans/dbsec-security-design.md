# Cortex Automations — Security Design for DBSec Review

**Author**: Vara B (AI FDE)
**Date**: 2026-04-10
**Status**: Draft — requesting PR-level review from DBSec
**Slack**: `#db-security-eng` / `@db-security-iam-oncall`

---

## 1. Overview

Cortex Automations is a new schema-level entity (`CORTEX_AUTOMATION`, Domain ID 286) that lets users deploy Python-based LangGraph workflow code to Snowflake. On invocation via `CALL`, GS launches an ephemeral SPCS job that executes the user's code with Snowflake connectivity.

**Security-relevant characteristics:**
- VStage-backed entity (code stored in versioned internal stage)
- Runs user-supplied Python code in an SPCS container
- Connects to Snowflake via OAuth token (SPCS auto-provisioned)
- Accesses Snowflake secrets via SPCS file mounts
- Supports HITL (Human-in-the-Loop) pause/resume via checkpoint
- Can call other Snowflake services (Cortex AI, Search, Analyst, Agents)

---

## 2. Privilege Model

### 2.1 Schema-Level Privilege

| Privilege | SQL Name | Code | Securable | Description |
|-----------|----------|------|-----------|-------------|
| `CREATECORTEXAUTOMATION` | `CREATE CORTEX AUTOMATION` | `CCAU` | SCHEMA | Required to create automations in a schema |

**Reference**: Follows `CREATEAGENT` pattern at `Privilege.java`. Implemented in PR 422682:
```java
public static final Privilege CREATECORTEXAUTOMATION =
    builder()
        .code("CCAU")
        .flags(Flag.CREATE_PRIVILEGE)
        .description("Privilege to create a new Cortex Automation object inside a schema")
        .securableTypes(SecurableType.SCHEMA)
        .sqlName("CREATE CORTEX AUTOMATION")
        .isUserAccountVisible(true)
        .visibilitySupplier(REQUIRES_VISIBILITY_INJECTION)
        .granteablePredicate(REQUIRES_GRANTEABLE_INJECTION)
        .build();
```

### 2.2 Object-Level Privileges

| Privilege | Operations Enabled | Description |
|-----------|-------------------|-------------|
| OWNERSHIP | All (DDL + execute + grant) | Full control. Auto-granted to creator. |
| USAGE | CALL (execute), DESCRIBE | Run the automation; view metadata |
| MODIFY | ALTER, DROP, deploy new version | Change code or properties |
| MONITOR | View run history, logs | Operational visibility without execution |

### 2.3 SecurableType Registration

```java
// In SecurableType.java:
CORTEX_AUTOMATION("CAU"),
```

### 2.4 Security Model

Following `CortexAgentServerSecurityModel` pattern:

| Operation | Required Privilege |
|-----------|--------------------|
| RESOLVE | ANY (any privilege suffices) |
| STAGE$LS, STAGE$GET | OWNERSHIP or USAGE or MODIFY |
| DESCRIBE | USAGE or MODIFY |
| ALTER, DROP | MODIFY |
| CALL (execute) | USAGE |
| RESUME (HITL) | USAGE |

```java
public class CortexAutomationSecurityModel implements IEntitySecurityModel {
    @Override
    public ImmutableSet<Domain> getSupportedDomains() {
        return ImmutableSet.of(Domain.CORTEX_AUTOMATION);
    }

    @Override
    public AuthzExpression<Permission> resolveEntityPermissions(
            Domain domain, long id, EnumSet<DbObjectOperation> ops, AuthzReq azReq) {
        AuthzAndExpression<Permission> expression = and();
        if (ops.remove(RESOLVE)) {
            expression.add(new Permission(CORTEX_AUTOMATION, id, Privilege.ANY));
        }
        if (ops.removeAll(EnumSet.of(STAGE$LS, STAGE$GET))) {
            expression.add(or(
                new Permission(CORTEX_AUTOMATION, id, Privilege.OWNERSHIP),
                new Permission(CORTEX_AUTOMATION, id, Privilege.USAGE),
                new Permission(CORTEX_AUTOMATION, id, Privilege.MODIFY)));
        }
        if (ops.remove(DESCRIBE)) {
            expression.add(or(
                new Permission(CORTEX_AUTOMATION, id, Privilege.USAGE),
                new Permission(CORTEX_AUTOMATION, id, Privilege.MODIFY)));
        }
        if (ops.removeAll(EnumSet.of(ALTER, DROP))) {
            expression.add(new Permission(CORTEX_AUTOMATION, id, Privilege.MODIFY));
        }
        return expression;
    }
}
```

---

## 3. Execution Model: EXECUTE AS Service Role (Definer's Rights)

### 3.1 Design

When a user calls `CALL my_db.my_schema.my_automation('{"key": "value"}')`:

1. **Caller context** (GS session): Caller must hold USAGE privilege on the automation.
2. **SPCS job creation**: GS creates the job with `SnowservicesCreateServiceOptions`:
   - `executeAsCurrentUser = false` (NOT the caller's identity)
   - The SPCS job's OAuth token is scoped to the **owner role** of the automation entity
3. **Inside the container**: The Python code (CortexContext) connects using the auto-provisioned OAuth token, which carries the **automation owner's role** — not the caller's role.

### 3.2 Security Implications

| Property | Value | Justification |
|----------|-------|---------------|
| Identity | Automation owner (definer) | Same as stored procedures with EXECUTE AS OWNER |
| Role | Owner role of the automation entity | Token scoped to owner role at SPCS job creation |
| Privilege scope | Everything the owner role can access | By design — owner publishes the automation |
| Caller visibility | Caller identity NOT available inside container | Prevents privilege confusion |

### 3.3 Why Definer's Rights (Not Caller's Rights)

- **Encapsulation**: Automation authors control what data the automation accesses. Callers don't need direct grants on underlying tables.
- **Consistency**: Matches stored procedures (EXECUTE AS OWNER) and the TDD's explicit decision.
- **Simplicity**: One OAuth token per job (the owner's). No need to manage caller credential delegation.

### 3.4 Risk: Privilege Escalation via Automation

**Scenario**: Owner creates automation that reads sensitive data. Grants USAGE to a less-privileged role. That role can now indirectly access data via the automation.

**Mitigation**: This is the **intended behavior** — identical to stored procedures with EXECUTE AS OWNER. The owner is responsible for what the automation code does. USAGE grant is an explicit delegation.

---

## 4. Secret Access Model

### 4.1 Design

Secrets are defined in `automation.toml`:
```toml
[secrets]
slack_token = "mydb.myschema.slack_secret"
jira_creds  = "mydb.myschema.jira_secret"
```

At **CREATE AUTOMATION** time:
1. GS validates that each secret FQN resolves to an existing Snowflake Secret object
2. GS validates that the **automation owner** has USAGE privilege on each secret
3. Secret FQNs are stored in the DPO runtime config (not the secret values)

At **CALL** (execution) time:
1. GS resolves each secret FQN and mounts the secret value as a file in the SPCS container
2. Mount path: `/snowflake/secrets/<key_name>` (e.g., `/snowflake/secrets/slack_token`)
3. The Python SDK reads: `ctx.secret("slack_token")` → reads file at mount path

### 4.2 Security Properties

| Property | Value |
|----------|-------|
| Secret storage | Snowflake Secret Manager (encrypted at rest) |
| Secret transport | SPCS file mount (never in env vars, never in logs) |
| Secret validation | At CREATE time (owner must have USAGE on each secret) |
| Secret re-validation | At CALL time (re-resolved to catch revoked access) |
| Secret in DPO | NO — only FQN references stored, never values |
| Secret in VStage | NO — only key names in automation.toml |
| Secret in container env | NO — file mounts only (per SPCS security best practice) |

### 4.3 Risk: Stale Secret References

**Scenario**: Owner creates automation referencing a secret. Secret is later dropped or owner's USAGE is revoked.

**Mitigation**: Secrets are re-resolved at each CALL. If the secret is missing or access is revoked, the SPCS job fails at startup with a clear error.

---

## 5. OAuth Token Lifecycle

### 5.1 Token Provisioning

| Phase | Mechanism |
|-------|-----------|
| Initial token | Created by GS at SPCS job launch, scoped to owner role |
| Token location | `/snowflake/session/token` inside container |
| Token TTL | 1 hour (JWT) |
| Token refresh | GS `ResourceSetReconcilerBG` regenerates every 5 minutes |
| Kubelet sync | ~1 minute delay to update projected volume |
| SDK behavior | Re-reads file on every new connection (no caching) |

### 5.2 Token Scope

The OAuth token carries:
- **Account**: The automation's home account
- **User**: System user for SPCS (not the caller's user)
- **Role**: The owner role of the automation entity
- **Warehouse**: Not set (automation code must specify if needed)

### 5.3 Risk: Token Leak from Container

**Scenario**: Malicious automation code reads the token file and exfiltrates it.

**Mitigation**:
- Token has 1-hour TTL (limits blast radius)
- External network access requires explicit External Access Integration (EAI)
- Without EAI, container has no outbound network access
- Token is scoped to the owner's role (same privilege as the owner already has)
- This is the same trust model as stored procedures and UDFs

---

## 6. Data Access via CortexContext SDK

### 6.1 Accessible Services

| Method | Underlying Access | Privilege Required |
|--------|------------------|-------------------|
| `ctx.query(sql)` | Direct SQL execution | Owner role's grants |
| `ctx.query_df(sql)` | Direct SQL execution | Owner role's grants |
| `ctx.complete(model, prompt)` | `SNOWFLAKE.CORTEX.COMPLETE()` | Cortex AI access |
| `ctx.search(service, query)` | Cortex Search service | USAGE on search service |
| `ctx.analyst(view, question)` | Cortex Analyst | USAGE on semantic view |
| `ctx.http(method, url)` | External network via EAI | EAI must be configured |
| `ctx.agent(name, message)` | Cortex Agent API | USAGE on agent |
| `ctx.automation(name, input)` | Calls another automation | USAGE on target automation |
| `ctx.secret(name)` | File mount read | Pre-validated at CREATE |

### 6.2 SQL Injection Risk

**Risk**: `ctx.query()` accepts arbitrary SQL strings. If the automation code concatenates user input into SQL, it's vulnerable to injection.

**Mitigation**:
- `ctx.query()` supports parameterized bindings: `ctx.query("SELECT * FROM t WHERE id = :1", {"1": user_input})`
- Documentation will strongly recommend parameterized queries
- This is the same trust model as stored procedures — the author is responsible for safe SQL
- The SQL runs as the owner's role (not elevated)

### 6.3 Cross-Automation Calls

**Risk**: `ctx.automation("other_auto", input)` — can one automation escalate privilege by calling another?

**Mitigation**: The call to the other automation goes through the standard `CALL` path. The calling automation's owner role must have USAGE on the target automation. The target automation then runs as **its own owner's role** (not the calling automation's role). No transitive privilege escalation.

---

## 7. HITL (Human-in-the-Loop) Security

### 7.1 Pause/Resume Flow

1. **Pause**: `ctx.human_action(prompt)` → checkpoint state to Hybrid Tables → SPCS job exits
2. **Resume**: User or system calls `SYSTEM$RESUME_CORTEX_AUTOMATION(run_id, payload)` → new SPCS job loads checkpoint → continues execution

### 7.2 Resume Authorization

| Question | Answer |
|----------|--------|
| Who can resume? | Any role with USAGE on the automation |
| Can anyone inject arbitrary payload? | Only USAGE grantees can call RESUME |
| Is the payload validated? | The automation code receives the payload; author is responsible for validation |
| Does resume run as caller or owner? | Owner (same as initial CALL) |
| Is the checkpoint tamper-proof? | Stored in system-managed Hybrid Tables in the owner's account; only GS writes to them |

### 7.3 Checkpoint Data Security

| Property | Value |
|----------|-------|
| Storage | Hybrid Tables (system-managed, `_cortex_automation_*` prefix) |
| Access | Only the SPCS runner (via owner role) and GS system session |
| Encryption | Snowflake standard encryption at rest |
| Lifetime | Tied to run lifecycle; expired runs are cleaned up |
| User access | Users cannot directly query checkpoint tables (hidden/system-managed) |

---

## 8. External Access

### 8.1 Network Isolation

By default, SPCS containers have **no outbound network access**. External access requires:
1. An External Access Integration (EAI) configured by an admin
2. The EAI explicitly listed in `automation.toml [external_access]`
3. The automation owner must have USAGE on the EAI

### 8.2 `ctx.http()` Method

Only works if an EAI is configured. Without it, all HTTP requests fail.

---

## 9. Summary of Trust Boundaries

```
┌─────────────────────────────────────────────────────┐
│  CALLER SESSION                                     │
│  • Must have USAGE on automation                    │
│  • Caller identity NOT propagated into container    │
│  • Sees only: run_id, status, output                │
└──────────────────────┬──────────────────────────────┘
                       │ CALL my_automation(input)
                       ▼
┌─────────────────────────────────────────────────────┐
│  GS (Global Services)                               │
│  • Validates USAGE privilege                        │
│  • Resolves secrets (re-validates owner access)     │
│  • Creates SPCS job with owner role token           │
│  • Mounts VStage code + secrets as files            │
│  • Waits for job completion                         │
└──────────────────────┬──────────────────────────────┘
                       │ SPCS Job
                       ▼
┌─────────────────────────────────────────────────────┐
│  SPCS CONTAINER (ephemeral)                         │
│  • Runs as OWNER ROLE (definer's rights)            │
│  • OAuth token at /snowflake/session/token          │
│  • Secrets at /snowflake/secrets/<key>              │
│  • Code from VStage mount (read-only)               │
│  • No outbound network (unless EAI configured)      │
│  • Checkpoint data → Hybrid Tables (system-managed) │
│  • Output → returned to GS → returned to caller    │
└─────────────────────────────────────────────────────┘
```

---

## 10. Open Questions for DBSec

1. **SecurableType code**: PR 422682 uses `"CAU"` for CORTEX_AUTOMATION. Any conflicts?
2. **Privilege code**: PR 422682 uses `"CCAU"` for CREATECORTEXAUTOMATION. Any conflicts?
3. **EXECUTE AS semantics**: We're using the SPCS `executeAsCurrentUser=false` path (owner role). Is there anything additional needed vs stored procedure EXECUTE AS OWNER?
4. **Checkpoint table access**: System-managed Hybrid Tables created by GS system session. Should these have explicit access policies, or is the system-managed pattern sufficient?
5. **Cross-automation privilege chain**: Automation A (owned by role R1) calls Automation B (owned by role R2). B runs as R2. Is this the correct isolation model, or should we restrict cross-automation calls?
6. **HITL resume payload injection**: The human response payload is passed into the LangGraph state. Should we size-limit or sanitize it at the GS layer?

---

## 11. Comparison to Existing Patterns

| Aspect | Stored Procedure | Cortex Agent | Cortex Automation |
|--------|-----------------|--------------|-------------------|
| Execution model | EXECUTE AS OWNER/CALLER | In-process (no SPCS) | EXECUTE AS OWNER via SPCS |
| Code storage | Inline / stage | VStage (agent_spec.yaml) | VStage (Python files) |
| Secret access | Via bindings | N/A | File mount in SPCS |
| Network | Via EAI | None (GS-side only) | Via EAI on SPCS |
| Privilege | USAGE to call | USAGE to call | USAGE to call |
| Schema privilege | CREATE PROCEDURE | CREATE AGENT | CREATE CORTEX AUTOMATION |
| Runs user code? | Yes (SQL/JS/Python) | No (config only) | Yes (Python/LangGraph) |
