# Snowflake Secrets Migration Plan

## Status: Phase 1 Complete (validated end-to-end 2026-03-23)

### Validation Results

- **Test secret:** `VB.SECRETS.MY_TEST_API_KEY` (value: `hello-from-snowflake-secret`)
- **Workflow:** `wf-730266fd-2376-4603-a2d3-aeeaf3d50fba` (`secret_config_test`)
- **Run ID:** `346fe6de-386a-4157-834c-671100acb6b3`
- **Manifest path:** `config.parameters.MY_SECRET` (secret accessed via `sdk.getParameter()`)
- **Result:** `{ success: true, secretResolved: true, secretLength: 27, secretPrefix: "hello-from" }`
- **CoCo CLI:** `{ installed: true, version: "1.0.39+183749.d046a8122126" }`
- **Controld log confirmed:** `Snowflake secrets mode: collected 1 secret(s) for SPCS mounting`
- **Controld never saw the plaintext** — SPCS mounted the secret directly into the job container
- **Secrets are config-only** — top-level `params` do not support Snowflake secret resolution

## Overview

Migrate P67's user/workflow secret storage from a self-managed Postgres + AES-256-GCM
encryption system to Snowflake-native SECRET objects, resolved via SPCS job spec mounting.

## What Was Done (Phase 1)

### Code Changes

| File | Change |
|------|--------|
| `services/controld/src/config.ts` | Added `SecretBackend` type and `secretBackend` field to `ServerConfig`. Defaults to `postgres`. Logs deprecation warning when using Postgres backend. |
| `services/controld/src/lib/runtime/schema.ts` | Added optional `secretEnvMappings` field to `SerializedP67Config` for IPC between controld and the runner host. Backward compatible. |
| `services/controld/src/lib/runtime/adapter.ts` | Added optional `secrets` parameter to `SPCSAdapter.buildJobServiceSQL()`. Injects a `secrets:` YAML block into the SPCS job spec for SPCS-native secret mounting. |
| `services/controld/src/lib/runner.ts` | Added `collectSnowflakeSecrets()` — walks manifest config fields and parameters, collects FQN secretRefs, generates env var mappings. Added conditional hydration: FQN refs get placeholders (resolved by host), non-FQN refs go through Postgres as before. Added `secretBackend` to Runner constructor. Updated `serializeConfig()` to include `secretEnvMappings`. |
| `services/controld/src/lib/runtime/host.ts` | Added env var resolution step before SDK creation. Reads SPCS-mounted secret values from `process.env` and injects into the config map. Handles both direct config fields (`config.snowflake.token`) and nested parameters (`config.snowflake.parameters.MY_KEY`). |
| `services/controld/src/lib/SecretService.ts` | Added `@deprecated` JSDoc. No functional changes. |
| `services/controld/src/lib/value-manager.ts` | Added `@deprecated` JSDoc to `getSecret()` and `decryptSecret()`. No functional changes. |
| `services/controld/src/lib/crypto.ts` | Added `@deprecated` JSDoc to `initCrypto()`, `encrypt()`, `decrypt()`. No functional changes. |
| `services/controld/src/lib/sdk-impl.ts` | Replaced Nathan's TODO on `hydrateConfig()` with implementation note referencing this migration. |
| `services/controld/src/routes/workflow/run.ts` | Passes `secretBackend` to Runner constructor. |
| `services/controld/src/routes/workflow/byName.ts` | Passes `secretBackend` to Runner constructor. |
| `services/controld/src/routes/webhook/snowflake.ts` | Passes `secretBackend` to Runner constructor. |
| `services/controld/src/routes/webhook/slack.ts` | Passes `secretBackend` to CommandDependencies. |
| `services/controld/src/lib/slack-commands.ts` | Added `secretBackend` to `CommandDependencies` interface. Passes to Runner constructor. |
| `services/controld/src/lib/slack-socket-mode.ts` | Added `secretBackend` to `SlackSocketModeService` constructor. Passes to CommandDependencies. |
| `services/controld/src/index.ts` | Passes `secretBackend` to `SlackSocketModeService`. |
| `containers/runner/Dockerfile` | Replaced CoCo CLI install script with direct download-and-extract. Avoids executing the amd64 binary during build under QEMU/Rosetta emulation on arm64 Macs. Extracts S3 URL from the official install script so it stays in sync if URLs change. |
| `native-app/controld_service_spec.yml` | No permanent changes. `SECRET_BACKEND` can be added to env section when ready to enable. |

### Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `src/lib/snowflake-secrets.test.ts` | 13 | FQN collection, non-FQN skipping, oauthRef skipping, inline values, multiple secrets, config entry parameters, mixed FQN/non-FQN, SQL injection rejection, two-part name rejection, empty manifests, dollar-sign identifiers |
| `src/lib/runtime/adapter.test.ts` | 5 | No secrets (unchanged), empty array, single secret, multiple secrets, secrets alongside other spec elements |
| `src/lib/runtime/schema.test.ts` | +4 new | secretEnvMappings absent (backward compat), present with values, empty object, non-string values rejected |

### Documentation

| File | Purpose |
|------|---------|
| `services/controld/SNOWFLAKE_SECRETS_MIGRATION.md` | This file. Internal migration plan, architecture, implementation details, Phase 2 cleanup checklist, build notes, test instructions. |
| `docs/snowflake-secrets-guide.md` | Customer-facing guide. Setup steps, manifest examples, rotation, access control, troubleshooting, migration from legacy secrets. |

### Design Decisions

1. **SPCS-native mounting over stored procedure factory** — Secrets are mounted directly into SPCS job containers as env vars. Controld never sees the plaintext. Simpler and more secure than the alternative (dynamic stored procedure that reads secrets at runtime).

2. **Config-only, not params** — Snowflake secrets are supported in `config` fields and `config.parameters`, not top-level `params`. Config values can't be overridden at runtime via the POST body, preventing accidental secret bypass.

3. **FQN regex for routing** — Three-part names (`DB.SCHEMA.NAME`) route to Snowflake SECRETs. Simple names route to legacy Postgres. Allows incremental migration without breaking existing workflows.

4. **Dual-path coexistence** — A single manifest can mix Snowflake and Postgres secrets. Customers migrate one secret at a time.

5. **No schema changes** — The manifest `secretRef` field is unchanged. The only difference is the value format (FQN vs simple name). No new manifest fields required.

6. **CoCo CLI direct download** — The runner Dockerfile installs CoCo via direct tarball download instead of the install script, which fails under amd64 emulation on arm64 Macs (SIGILL exit code 132). The S3 URL is extracted from the official install script to stay in sync.

### What Was NOT Changed

- No Prisma schema changes
- No Postgres table changes
- No legacy code logic modified (only `@deprecated` annotations)
- No CLI command changes
- No manifest schema changes
- Default behavior unchanged (`SECRET_BACKEND=postgres`)
- `oauthRef` path unchanged (stays on Postgres + IPC)

## Ground Rules

- **No changes to legacy code** other than `@deprecated` markers
- **New code path gated** behind `SECRET_BACKEND=snowflake` (defaults to `postgres`)
- **No Prisma/Postgres/database changes** in this phase
- **Phase 2** handles actual legacy removal

## Architecture

### Current (Postgres path — `SECRET_BACKEND=postgres` or unset)

```
Runner.start()
  → new ValueManager(db, userId)
  → hydrateConfig(manifest, valueManager)
    → ValueManager.getSecret(secretRef)
      → Prisma query (Postgres)
      → decrypt(AES-256-GCM)
      → plaintext
  → serialize into P67_RUN_MESSAGE_B64 (base64 env var)
  → EXECUTE JOB SERVICE (no secrets in spec)
  → Host deserializes → SDK uses plaintext
```

### New (Snowflake path — `SECRET_BACKEND=snowflake`)

Supports **dual-path resolution** in a single workflow:

- **FQN secretRef** (e.g., `DB.SCHEMA.NAME`) → SPCS-native mounting (Snowflake SECRET)
- **Non-FQN secretRef** (e.g., `my_key`) → falls back to Postgres (legacy ValueManager)

The FQN regex `^[A-Za-z_][A-Za-z0-9_$]*\.[A-Za-z_][A-Za-z0-9_$]*\.[A-Za-z_][A-Za-z0-9_$]*$`
determines which path each secretRef takes.

```
Runner.start()
  → collectSnowflakeSecrets(manifest)
    → walk config fields + parameters for FQN secretRefs
    → replace matched secretRefs with placeholder values
    → build SPCS spec secrets list + env var mappings
  → hydrateConfig(manifest, valueManager)
    → FQN refs: already replaced with placeholder, passed through
    → Non-FQN refs: resolved from Postgres as before
  → serialize config + secretEnvMappings into P67_RUN_MESSAGE_B64
  → EXECUTE JOB SERVICE (FQN secrets in spec, SPCS mounts as env vars)
  → Host resolves secretEnvMappings from process.env → injects into config
  → Non-FQN values already resolved as plaintext in the message
  → SDK uses all values as plaintext
```

This allows customers to migrate secrets one at a time without breaking existing
workflows. A single manifest can mix Snowflake SECRETs and Postgres-backed secrets.

## Implementation Steps

### Step 1: Config (`config.ts`)

Add to `ServerConfig`:
```typescript
secretBackend: 'postgres' | 'snowflake';
```

Read from `process.env.SECRET_BACKEND || 'postgres'`.

**File:** `services/controld/src/config.ts`

### Step 2: IPC Schema (`schema.ts`)

Add optional field to `SerializedP67ConfigSchema`:
```typescript
secretEnvMappings: z.record(z.string(), z.string()).optional()
```

Maps config field paths to env var names. Backward compatible (optional field).

**File:** `services/controld/src/lib/runtime/schema.ts`

### Step 3: SPCS Adapter (`adapter.ts`)

Add optional `secrets` parameter to `buildJobServiceSQL()`:
```typescript
secrets?: Array<{ objectName: string; envVarName: string }>
```

When provided, inject into YAML spec under the container:
```yaml
    secrets:
    - snowflakeSecret:
        objectName: mydb.myschema.my_api_key
      secretKeyRef: secret_string
      envVarName: P67_SECRET_0
```

**File:** `services/controld/src/lib/runtime/adapter.ts`

### Step 4: Secret Collection (`runner.ts`)

New method `collectSnowflakeSecrets(manifest)`:
1. Walk manifest config entries (fields + nested parameters)
2. For each `secretRef`, generate env var name `P67_SECRET_<index>`
3. Return:
   - `specSecrets`: array for the SPCS spec
   - `envMappings`: record for the IPC message

**File:** `services/controld/src/lib/runner.ts`

### Step 5: Conditional Hydration (`runner.ts`)

In `Runner.start()` around line 498:
- If `secretBackend === 'postgres'`: existing path (ValueManager, unchanged)
- If `secretBackend === 'snowflake'`: call `collectSnowflakeSecrets()`,
  use ValueManager only for `oauthRef`/`value`/`valueRef` types

**File:** `services/controld/src/lib/runner.ts`

### Step 6: Wire Up in startSPCS (`runner.ts`)

Pass collected secrets to `adapter.buildJobServiceSQL()` when in Snowflake mode.

**File:** `services/controld/src/lib/runner.ts`

### Step 7: Host Resolution (`host.ts`)

After `deserializeConfig()` (line 224), before SDK creation:
- If `data.config.secretEnvMappings` exists, resolve each from `process.env`
- Inject resolved values into the config Map

**File:** `services/controld/src/lib/runtime/host.ts`

### Step 8: Deprecation Markers

Add `@deprecated` JSDoc to:
- `SecretService` class (`lib/SecretService.ts`)
- `ValueManager.getSecret()` and `ValueManager.decryptSecret()` (`lib/value-manager.ts`)
- `encrypt`, `decrypt`, `initCrypto` in `crypto.ts`
- `config.encryption` type field

Add startup warning log when `SECRET_BACKEND=postgres`.

### Step 9: This File

Track progress here.

### Step 10: CI Verification

Run `pnpm ci` — biome check + type check must pass.

## Phase 2: Legacy Removal (Future)

**Prerequisite:** All customers have migrated their secrets from Postgres to Snowflake
SECRET objects. Verify by checking the Postgres `Secret` table is empty or all
remaining entries have corresponding Snowflake SECRETs.

### Cleanup Checklist

1. **Remove dual-path resolution in `runner.ts`:**
   - Remove `collectSnowflakeSecrets()` function and `CollectedSecrets` type
   - Remove `SF_SECRET_FQN_RE` regex
   - Remove the `if (this.secretBackend === 'snowflake')` conditional block
   - Remove `collectedSecrets` field from `Runner`
   - Remove `secretBackend` from `Runner` constructor (and all call sites: `run.ts`, `byName.ts`, `snowflake.ts`, `slack-commands.ts`, `slack-socket-mode.ts`, `slack.ts`, `index.ts`)
   - All `secretRef` values should go through SPCS mounting unconditionally

2. **Remove `ValueManager` secret resolution:**
   - Remove `getSecret()` method
   - Remove `decryptSecret()` method
   - Remove `PrismaClient` dependency (if only used for secrets)
   - Keep `getOAuthToken()` and `getOAuthTokenData()` until oauthRef is migrated

3. **Remove `SecretService`:**
   - Delete `services/controld/src/lib/SecretService.ts`
   - Remove `server.secretService` decoration from `server.ts`

4. **Remove `crypto.ts`:**
   - Delete `services/controld/src/lib/crypto.ts`
   - Remove all imports of `encrypt`/`decrypt`/`initCrypto` (in `server.ts`, `value-manager.ts`, `routes/secret/get.ts`, `routes/secret/oauth-refresh.ts`)

5. **Remove encryption key infrastructure:**
   - Remove `ENCRYPTION_KEY` from: `config.ts`, `.env`, `.env.example`, `compose.yaml`
   - Remove `encryption_key` SPCS secret mount from `native-app/controld_service_spec.yml`
   - Remove `encryption_key` reference from `native-app/manifest.yml`
   - Remove `spcs-data-secret` target from `Makefile`
   - Remove `config.encryption` from `ServerConfig` type

6. **Remove `SECRET_BACKEND` config:**
   - Remove from `config.ts` (type, env var reading, deprecation warning)
   - Remove `SecretBackend` type export
   - Remove from all files that import it

7. **Remove or rewrite secret REST routes:**
   - `routes/secret/save.ts` — remove (customers use `CREATE SECRET` SQL)
   - `routes/secret/get.ts` — remove (customers use `DESCRIBE SECRET` for metadata)
   - `routes/secret/list.ts` — remove (customers use `SHOW SECRETS`)
   - `routes/secret/delete.ts` — remove (customers use `DROP SECRET`)
   - `routes/secret/oauth-refresh.ts` — keep until oauthRef migration
   - `routes/secret/index.ts` — update registrations

8. **Remove Prisma `Secret` model:**
   - Remove from `packages/db/prisma/schema.prisma`
   - Run Prisma migration
   - Drop Postgres `Secret` table (after confirming safe)

9. **Remove dead code:**
   - `isCryptoInitialized()` in `crypto.ts` (already never called)
   - `createWorkflowSDK()` in `sdk-impl.ts` (never imported)
   - `secrets/1password.ts` in CLI (orphaned)

10. **Remove `secretEnvMappings` conditional in `host.ts`:**
    - Once all secrets go through SPCS mounting, the env var resolution
      becomes the only path — remove the `if (data.config.secretEnvMappings)`
      check and make it unconditional

11. **Update CLI:**
    - Remove `p67 secret save/list/delete` commands (or rewrite as wrappers
      around Snowflake SQL: `CREATE SECRET`, `SHOW SECRETS`, `DROP SECRET`)
    - Remove `ControldClient` secret methods (`saveSecret`, `listSecrets`,
      `getSecret`, `deleteSecret`)

12. **Migrate `oauthRef`:**
    - Investigate Snowflake `TYPE = OAUTH2` secrets with built-in refresh
    - Or use stored procedure factory approach for OAuth token refresh
    - Remove `RequestOAuthToken`/`OAuthTokenResponse` IPC messages once migrated

13. **Update tests:**
    - Remove Postgres-path test cases
    - Update `snowflake-secrets.test.ts` to remove FQN regex tests (all refs
      would be FQN)
    - Add tests for error cases (missing grant, wrong FQN, etc.)

14. **Update documentation:**
    - Remove references to `SECRET_BACKEND` flag from all docs
    - Remove Postgres secret mentions from customer guide
    - Archive this migration plan

## Key Files

| File | Purpose |
|------|---------|
| `services/controld/src/config.ts` | Config: add secretBackend |
| `services/controld/src/lib/runtime/schema.ts` | IPC: add secretEnvMappings |
| `services/controld/src/lib/runtime/adapter.ts` | SPCS spec: add secrets section |
| `services/controld/src/lib/runner.ts` | Secret collection + conditional hydration |
| `services/controld/src/lib/runtime/host.ts` | Env var resolution |
| `services/controld/src/lib/SecretService.ts` | Deprecate |
| `services/controld/src/lib/value-manager.ts` | Deprecate getSecret/decryptSecret |
| `services/controld/src/lib/crypto.ts` | Deprecate all exports |

## oauthRef Note

`oauthRef` stays on the existing Postgres + IPC path. It requires runtime
token refresh (decrypt → check expiry → HTTP refresh → re-encrypt → save),
which SPCS mounting can't provide. Phase 2 will investigate Snowflake's
native `TYPE = OAUTH2` secret with built-in refresh.

## Testing

### Unit Tests (implemented)

Run with `npx tsc --noCheck && npx tsc-alias && npx vitest run` from `services/controld`.

105 tests across 6 files (85 pre-existing + 42 new):

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `src/lib/snowflake-secrets.test.ts` | 13 | `collectSnowflakeSecrets()` — FQN collection, non-FQN skipping, oauthRef skipping, inline values, multiple secrets, config entry parameters, mixed FQN/non-FQN, SQL injection rejection, two-part name rejection, empty manifests, dollar-sign identifiers |
| `src/lib/runtime/adapter.test.ts` | 5 | `SPCSAdapter.buildJobServiceSQL()` — no secrets (unchanged behavior), empty array, single secret, multiple secrets, secrets alongside other spec elements |
| `src/lib/runtime/schema.test.ts` | +4 new | `SerializedP67Config.secretEnvMappings` — absent (backward compat), present with values, empty object, non-string values rejected |
| `src/lib/runtime/host-resolution.test.ts` | 10 | Host env var resolution — direct config fields, nested parameters, create parameters object, multiple secrets, missing env var, missing config entry, non-config paths, short paths, mixed fields+parameters, empty mappings |
| `src/lib/runner-serialization.test.ts` | 10 | `serializeConfig` with secretEnvMappings (null, empty, populated, multiple). Placeholder replacement — FQN replaced, non-FQN untouched, inline values untouched, config parameters, mixed FQN/non-FQN, end-to-end with collectSnowflakeSecrets |

### Build Notes

The `p67-runner` image (`containers/runner/Dockerfile`) must also be rebuilt and pushed
when `host.ts` changes — the runner bundles the compiled host at `/app/host.js`.

**Stale Docker cache issue:** If the runner build fails with
`ENOENT: no such file or directory, mkdir '/deployed/node_modules/.pnpm/...'`,
clear the Docker BuildKit cache mounts before retrying:

```bash
docker builder prune --filter type=exec.cachemount -f
```

This happens when pnpm cache from a previous arm64 build is reused in an amd64
emulated build. Both controld and runner images must target `--platform linux/amd64`
for SPCS.

**Build and push commands:**

```bash
# Controld (from repo root)
make build-controld
make push-controld

# Runner (from repo root)
docker build --platform linux/amd64 -f containers/runner/Dockerfile -t p67-runner .
docker tag p67-runner sfengineering-aifde.registry.snowflakecomputing.com/p67_src/core/img_repo/p67-runner
docker push sfengineering-aifde.registry.snowflakecomputing.com/p67_src/core/img_repo/p67-runner

# Redeploy
snow app run -c aifde
CALL P67.V1.INIT();
```

### Integration Tests (manual, requires SPCS)

#### Completed

- [x] **Full SPCS round-trip with config.parameters:**
  Secret `VB.SECRETS.MY_TEST_API_KEY` resolved via `config.parameters.MY_SECRET`,
  verified `sdk.getParameter('MY_SECRET')` returned correct value.
  Run ID: `346fe6de-386a-4157-834c-671100acb6b3`

- [x] **CoCo CLI in runner container:**
  Verified `cortex versions` runs inside the p67-runner SPCS job container.
  Version: `1.0.39+183749.d046a8122126`

#### Outstanding

- [ ] **Secret rotation:**
  `ALTER SECRET VB.SECRETS.MY_TEST_API_KEY SET SECRET_STRING = 'rotated-value'`,
  re-run workflow, verify new value is picked up without redeployment.

- [ ] **Regression with `SECRET_BACKEND=postgres` (default):**
  Remove `SECRET_BACKEND` from service spec (or set to `postgres`), redeploy,
  run existing workflows with simple-name `secretRef` pointing to Postgres secrets.
  Verify identical behavior and deprecation warning in startup logs.

- [ ] **Dual-path in a single manifest:**
  Deploy a workflow with both a FQN `secretRef` (Snowflake) and a simple-name
  `secretRef` (Postgres) in the same manifest. Verify both resolve correctly.

- [ ] **Direct config field (not parameters):**
  Deploy a workflow with `secretRef` on a top-level config field like `token`
  (not inside `parameters`). Verify the `parts.length === 3` branch in host.ts
  resolves correctly.

- [ ] **Invalid/missing FQN:**
  Deploy a workflow with `secretRef: "DB.SCHEMA.NONEXISTENT_SECRET"`. Verify
  the SPCS job fails with a clear error about the secret not existing or not
  being authorized.

- [ ] **Missing GRANT:**
  Create a secret but don't grant READ to the P67 app. Verify the SPCS job
  fails with an authorization error, not a cryptic crash.

- [ ] **Docker mode + Snowflake backend:**
  Set `SECRET_BACKEND=snowflake`, run in Docker mode (no SPCS). Verify the
  host warns about missing env vars but doesn't crash.

