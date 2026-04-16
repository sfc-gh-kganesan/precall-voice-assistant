# Cortex Automations — Product Considerations

> **Status**: Draft — Companion to `gs-integration-plan.md`  
> **Last Updated**: 2026-04-10  
> **Audience**: PM, PM Director, VP Eng, Sales, Field, Design Partners  
> **Source**: Feedback from a 10-persona review panel (PM Director, VP Eng, Engineering Director, Senior IC, EM, Security, SRE, DevRel, SE, Non-Technical PM)

This document captures product-level concerns that surfaced during review of the GS Integration Plan. These items are **not** implementation details — they are positioning, scoping, and go-to-market decisions that need resolution alongside the technical work.

---

## 1. What is Cortex Automations?

**This statement does not exist in the technical plan and needs to be written.**

Draft:

> Cortex Automations is a managed runtime for stateful, AI-powered background processes on Snowflake. Write a Python workflow, deploy it with one command, and Snowflake handles execution, checkpointing, human-in-the-loop approvals, and versioning — all inside your security perimeter with the same RBAC that governs your data.

**The core value proposition in one sentence:**

> Your AI workflow runs where your data lives — no data leaves Snowflake, no external orchestrator to manage, no connection strings to configure.

**What it is NOT:**
- A chatbot framework (that's Cortex Agents)
- A replacement for Snowflake Tasks (Tasks schedule; Automations execute)
- A general-purpose container platform (that's SPCS)
- A visual drag-and-drop builder (that's additive, post-launch)

---

## 2. Cortex Agent vs Cortex Automation — Positioning

This distinction is the most common question from every reviewer. The PRD has this table — it should be prominently referenced.

| Dimension | Cortex Agent | Cortex Automation |
|---|---|---|
| **Invoked by** | A human sending a message | A schedule, event, API call, or Agent tool call |
| **Who is waiting** | A human, right now | Nobody — notify when done |
| **Latency contract** | First token in milliseconds | Minutes or hours is acceptable |
| **Output** | Streaming tokens in a chat UI | Structured result, action taken, notification sent |
| **State** | Conversation thread (7-day TTL) | Execution checkpoint (durable until complete) |
| **Authoring** | System prompt + tool config (no code) | Python LangGraph graph (code required) |
| **HITL** | The entire interaction is human-driven | Explicit `ctx.human_action()` suspension point |

**The practical test:** If a human is on the other end expecting a streaming response, it's an Agent. If a process fires it and checks back later for a result, it's an Automation.

**They compose freely.** An Agent can invoke an Automation as a tool. An Automation can call an Agent as a reasoning node.

---

## 3. Target Persona

**Not yet defined.** The technical plan is persona-agnostic. Product needs to decide:

| Persona | Use Case | Sophistication |
|---|---|---|
| **AI Engineer** | Custom multi-step AI pipelines with branching, tool use, HITL | High — writes LangGraph graphs |
| **Data Engineer** | Orchestrated data + AI workflows triggered by data changes | Medium — familiar with SQL, basic Python |
| **Platform Engineer** | Internal tooling: ticket triage, customer onboarding, alert routing | Medium-High — deploys and manages services |
| **IT Ops / Business Analyst** | Simple approval workflows, report generation | Low — needs visual builder (Future Work) |

**Recommendation:** V1 targets AI Engineers and Platform Engineers. Data Engineers join at scheduling GA. Business Analysts join at visual builder.

---

## 4. Competitive Positioning

**Entirely absent from the technical plan.** Reviewers flagged this as a hard requirement for any exec review.

| Competitor | Where They Win | Where We Win |
|---|---|---|
| **Temporal** | Industry-standard durable execution. Mature SDKs. Rich visual debugger. Used by Stripe, Netflix. | Data leaves Snowflake's security perimeter. Separate infra to manage. No native Snowflake RBAC. |
| **AWS Step Functions** | Visual editor day one. 200+ AWS integrations. Mature HITL via `.waitForTaskToken`. | AWS-only. Data must be accessible from Lambda. No Snowflake-native identity. |
| **Prefect / Dagster** | Purpose-built for data pipelines. Better scheduling, retry, observability. | External orchestrator. Data access requires credentials. Not Snowflake-native. |
| **n8n / Make / Zapier** | No-code. Visual. Instant Slack/email integrations. | No code execution capability. Shallow AI integration. Not enterprise-grade. |

**Our moat (must be articulated clearly):**
> Your workflow runs inside Snowflake's security perimeter. The same RBAC that governs your tables governs your automations. No data crosses a trust boundary to reach the orchestrator. Checkpointing, versioning, and HITL are zero-config — they come with the platform.

---

## 5. V1 Scope / PrPr Entry Criteria

**Not defined in the technical plan.** The six phases don't map to a release milestone.

**Proposed PrPr scope:** Phases 1-4 complete (Entity + DDL + SPCS + HITL + SDK). Specifically:
- CREATE/ALTER/DROP/SHOW/DESCRIBE AUTOMATION works
- CALL automation(input) executes a workflow on SPCS
- Checkpointing via Hybrid Tables
- ctx.human_action() with checkpoint-and-release
- CortexContext SDK (ctx.query, ctx.complete, ctx.search, ctx.analyst, ctx.agent, ctx.http, ctx.secret, ctx.emit)

**NOT in PrPr:** Snowsight dashboard, webhook triggers, visual editor, custom images, scheduling integration.

**Proposed PrPr criteria:**
- 3+ design partners with deployed automations
- Security review complete (all PrPr gates pass)
- E2E: CREATE → deploy → execute → HITL suspend → resume → complete

---

## 6. Scheduling — V1 or Not?

**This is the most impactful product scoping decision.**

The technical plan defers scheduling to "Future Work." The SE reviewer flagged it as blocking 80% of field use cases. The PRD shows Task integration as a primary invocation pattern.

**The question:** Is `CREATE TASK ... AS CALL automation(input)` sufficient for V1, or do we need deeper integration?

**Analysis:**
- Tasks already exist and can call any SQL/stored procedure
- If `CALL automation(input)` works, Tasks can invoke it today — no new integration needed
- The only gap: HITL automations called from Tasks block the Task for the full timeout duration (the PRD explicitly documents this and says to use ASYNC)

**Recommendation:** Scheduling is already covered by Tasks if `CALL automation(input)` is synchronous-capable. Document the Task integration pattern prominently. No new scheduling infrastructure needed for V1.

---

## 7. TypeScript Decision

**Current state:** P67 supports TypeScript workflows. GS-managed plan is Python-only.

**Impact:** Unknown — needs quantification. How many P67 deployments use TypeScript?

**Options:**
| Option | Effort | Risk |
|---|---|---|
| Python-only V1, TypeScript V2 | Low | Blocks TypeScript customers from migrating |
| Python-only, TypeScript via transpilation guide | Low | Fragile, unsupported |
| Python + TypeScript V1 | High | Two SDKs, two runner images, two test matrices |

**Recommendation:** Ship Python-only V1. Quantify TypeScript usage. If >30% of P67 deployments are TypeScript, commit to a TypeScript timeline. If <10%, document the Python porting guide and move on.

---

## 8. Pricing and Cost Transparency

**Current state:** "SPCS credits, no separate SKU." One sentence.

**What customers need to understand:**
- A simple 5-node automation running for 30 seconds costs approximately X credits
- HITL suspension costs zero (container released)
- VStage storage is negligible for typical workflow bundles
- Cortex AI calls (LLM, Analyst, Search) are billed separately at standard rates
- Compute pool costs are separate from automation credits

**Recommendation:** Create a pricing FAQ with 3-4 representative scenarios and estimated costs. Even rough order-of-magnitude ("cents per run for simple workflows, dollars per run for complex multi-LLM workflows") is better than silence.

---

## 9. UX Decisions

### Auto-generate run_id
The technical plan requires callers to supply `run_id` in the invocation JSON. This is an implementation detail leaking into the UX. 

**Recommendation:** Auto-generate `run_id` in GS. Return it from `CALL`. If the user wants to supply their own for idempotency, make it optional.

### Creation syntax: pick one for V1
The DDL supports both `AS '@stage/path/'` and `FROM SPECIFICATION $$...$$`. Two creation paths with no guidance will confuse onboarding.

**Recommendation:** V1 ships with `AS '@stage/path/'` (CLI deploys to stage first). `FROM SPECIFICATION` is for Snowsight/vibe-builder integration (can be added later).

### Resume syntax
`CALL automation.resume(run_id, payload)` uses dot-notation that doesn't exist in Snowflake SQL. Multiple reviewers flagged this.

**Options:**
- `RESUME AUTOMATION <name> RUN '<run_id>' WITH (...)` — new DDL verb
- `CALL SYSTEM$RESUME_AUTOMATION(run_id, payload)` — system function
- `CALL automation.resume(...)` — new SQL semantics (requires SQL Compiler buy-in)

**Recommendation:** The DDL verb (`RESUME AUTOMATION`) is most consistent with Snowflake SQL conventions. Decision requires SQL Compiler team input.

---

## 10. Design Partner Validation

**Not addressed in the technical plan.** Required before PrPr.

**Questions to answer:**
- Who are the 3-5 design partners?
- What specific workflows will they deploy?
- What is their current solution (P67 native app, custom, nothing)?
- What is their definition of success?
- What is their timeline expectation?

---

## 11. P67 Deprecation Timeline (Business Side)

| Phase | State | Customer Impact |
|---|---|---|
| PrPr launch | P67 native app continues. GS path available as opt-in. | No disruption. |
| GA | New customers directed to GS path. P67 enters maintenance. | New customers get GS. Existing P67 customers unaffected. |
| Deprecation | P67 native app deprecated. Migration tooling provided. | Existing customers must plan migration. |
| Sunset | P67 native app removed. | All customers on GS. |

**Key commitment:** No forced migration without feature parity + migration tooling + 6-month notice.

---

## 12. Success Metrics

| Metric | PrPr Target (90 days) | GA Target (6 months) |
|---|---|---|
| Automations created | 50+ across design partners | 500+ across all accounts |
| Active accounts | 5+ design partners | 50+ |
| HITL interactions / week | 10+ | 100+ |
| Runs / day | 100+ | 10,000+ |
| P67 migration rate | N/A | 50% of P67 customers migrated |

---

## 13. Open Product Decisions

| Decision | Options | Owner | Deadline |
|---|---|---|---|
| DDL noun: `AUTOMATION` vs `CORTEX AUTOMATION` | Single word vs prefixed | PM + SQL Compiler | Before Phase 2 |
| TypeScript support timeline | V1 / V2 / never | PM | Before PrPr |
| Scheduling: explicit V1 scope or defer? | Tasks integration docs vs new scheduling DDL | PM | Before PrPr |
| Billing SKU: SPCS credits vs dedicated | Simple (V1) vs dedicated (GA) | PM + Finance | Before GA |
| LangGraph coupling: strategic bet or risk? | Commit vs abstract | PM + VP Eng | Before PrPr |
| Resume syntax: DDL verb vs dot-notation vs system function | See §9 | PM + SQL Compiler | Before Phase 2 |
| Visual builder: V1 or post-GA? | Snowsight scope | PM + Snowsight | Before GA |
