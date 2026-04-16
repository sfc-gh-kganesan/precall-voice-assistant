# Cortex Automations — DDL Syntax Proposal for SQL Compiler Review

**Author**: Vara B (AI FDE)
**Date**: 2026-04-10
**Channel**: `#compiler-discuss` / `#sql-parser-help`

---

## 1. Summary

Cortex Automations is a new schema-level entity for deploying Python/LangGraph
workflow code. We need DDL support for CRUD operations plus an invocation
function. This doc proposes the exact SQL grammar and lists open questions for
the compiler team.

**Pattern followed**: CORTEX AGENT (two-word noun, VStage-backed, ANTLR-gated).

---

## 2. Proposed DDL Grammar

### CREATE
```sql
CREATE [ OR REPLACE ] CORTEX AUTOMATION [ IF NOT EXISTS ] <name>
  [ EXECUTE AS '<role_name>' ]
  [ ENTRYPOINT = '<module:attribute>' ]
  [ COMPUTE_POOL = <pool_name> ]
  [ EXTERNAL_ACCESS_INTEGRATIONS = ( <eai_name> [, ...] ) ]
  [ SECRETS = ( '<json_bindings>' ) ]
  [ RUNTIME VERSION = '<version>' ]
  [ AS '<stage_path>' ]
  [ FROM <source_location> ]
  [ WITH ... ]
```

### ALTER
```sql
ALTER CORTEX AUTOMATION [ IF EXISTS ] <name> SET
  { EXECUTE AS '<role_name>'
  | ENTRYPOINT = '<module:attribute>'
  | COMPUTE_POOL = <pool_name>
  | EXTERNAL_ACCESS_INTEGRATIONS = ( <eai_name> [, ...] )
  | SECRETS = ( '<json_bindings>' )
  | RUNTIME VERSION = '<version>'
  | COMMENT = '<comment>' }

ALTER CORTEX AUTOMATION <name> UNSET { COMMENT }
```

### DROP
```sql
DROP CORTEX AUTOMATION [ IF EXISTS ] <name>
```

### DESCRIBE
```sql
DESCRIBE CORTEX AUTOMATION <name>
```

### SHOW
```sql
SHOW CORTEX AUTOMATIONS [ LIKE '<pattern>' ] [ IN { SCHEMA <schema> | DATABASE <db> | ACCOUNT } ]
SHOW VERSIONS IN CORTEX AUTOMATION <name>
```

### Invocation (SYSTEM$ function)
```sql
SELECT SYSTEM$RUN_CORTEX_AUTOMATION('<fqn>', '<json_input>')
```

### HITL Resume
```sql
-- Preferred (Option B from design):
SELECT SYSTEM$RESUME_CORTEX_AUTOMATION('<fqn>', '<run_id>', '<json_payload>')
```

---

## 3. ANTLR Grammar (already implemented in PR 422682)

```antlr
createCortexAutomationStatement :
    orReplace? KW_CORTEX KW_AUTOMATION ifNotExists? name=objectName
    (KW_EXECUTE KW_AS executeAsRole=stringLiteralOrBind)?
    (KW_SECRETS EQUAL LPAREN secretsList=stringLiteralOrBind RPAREN)?
    (KW_RUNTIME KW_VERSION EQUAL runtimeVersion=stringLiteralOrBind)?
    (KW_AS stagePath=stringLiteralOrBind)?
    fbeSourceLocation?
    (withClause=withProvision)?
    ;
```

New tokens: `TOK_CORTEX_AUTOMATION`, `TOK_CORTEX_AUTOMATION_EXECUTE_AS`,
`TOK_CORTEX_AUTOMATION_SECRETS`, `TOK_CORTEX_AUTOMATION_RUNTIME_VERSION`,
`TOK_CORTEX_AUTOMATION_STAGE_PATH`

Gated by: `AntlrBoss.Options.ENABLE_CORTEX_AUTOMATION_SYNTAX`

---

## 4. Parse Tree -> Execution Mapping

| Parse Tree Node | Execution Node | Handler |
|----------------|---------------|---------|
| `SqlCreateCortexAutomation` | `ExecCreateCortexAutomation` | Creates entity + VStage, copies code from source stage |
| `SqlAlterCortexAutomation` | (via ExecAlter dispatch) | Updates DPO properties |
| SqlDrop (domain dispatch) | `ExecDrop` | Drops entity + nested VStage |
| SqlDescribe (domain dispatch) | `ExecDescribe` | Returns entity metadata |
| SqlShow (domain dispatch) | `ExecShowCortexAutomations` | Lists automations |

---

## 5. Open Questions for Compiler Team

| # | Question | Context |
|---|----------|---------|
| 1 | **DDL noun**: Is `CORTEX AUTOMATION` the right two-word noun? Follows `CORTEX AGENT` precedent. | Domain friendly name is "Cortex Automation" |
| 2 | **SYSTEM$ vs CALL**: We use `SYSTEM$RUN_CORTEX_AUTOMATION` for invocation (not CALL). Is this the right pattern for a non-procedure entity? | Agent uses `SYSTEM$CORTEX_AGENT_RUN` |
| 3 | **FROM clause**: We support both `AS '<stage_path>'` and `FROM <fbeSourceLocation>`. Is this consistent with other VStage entities? | Streamlit uses FROM, Notebooks use FROM |
| 4 | **ALTER grammar**: Is the current SET pattern (individual properties) the right approach? | Matches Agent pattern |
| 5 | **SHOW VERSIONS**: Should this follow the exact same grammar as other VStage entities? | DCM Project, Agent, Notebook all have SHOW VERSIONS |
| 6 | **Parser ownership**: We've written the ANTLR grammar in PR 422682. Does the compiler team prefer to own/review these changes? | Some teams write their own, others defer |

---

## 6. Privilege Integration

| Privilege | Code | SQL Name | Securable |
|-----------|------|----------|-----------|
| `CREATECORTEXAUTOMATION` | `CCAU` | `CREATE CORTEX AUTOMATION` | SCHEMA |
| `OWNERSHIP` | (standard) | (standard) | CORTEX_AUTOMATION |
| `USAGE` | (standard) | (standard) | CORTEX_AUTOMATION |
| `MONITOR` | (standard) | (standard) | CORTEX_AUTOMATION |

SecurableType: `CORTEX_AUTOMATION("CAU")`

---

## 7. Reference: How CORTEX AGENT Did It

For context, here's the CORTEX AGENT pattern we're following:

- Domain: `CORTEX_AGENT(206, SCHEMA, Namespace.NOTSHARED, "Agent")`
- SecurableType: `AGENT("AG")`
- Create privilege: `CREATEAGENT` / code `"CA"` / SQL `"CREATE AGENT"`
- ANTLR gate: `ENABLE_CORTEX_AGENT_SYNTAX`
- Invocation: `SYSTEM$CORTEX_AGENT_RUN` (not CALL)
- VStage-backed: Yes (agent_spec.yaml stored in VStage)
