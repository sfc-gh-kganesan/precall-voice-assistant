# Proposal G — `p67 doctor` Command

## What was implemented

A diagnostic command (`p67 doctor`) that checks the health of the P67 environment. It runs five checks in order and reports pass/fail status for each:

1. **CLI version** — Reads and displays the version from `package.json`
2. **Connection** — Checks if any connections are configured and which is default
3. **Endpoint reachable** — HTTP GET to `<endpoint>/api/health`, verifies 200 response
4. **Controld healthy** — Parses the health response JSON for `{"status":"ok"}`
5. **Snow CLI available** — Checks if `snow` is in PATH via `which`

Each check prints a checkmark (✓) on pass or cross (✗) on failure. Failed checks include a one-line remediation hint. The command exits with code 0 if all checks pass, 1 if any fail.

### Files changed

- `tools/p67-cli/src/commands/doctor.ts` — Command implementation with exported check functions
- `tools/p67-cli/src/program.ts` — Registered `doctorCommand`
- `tools/p67-cli/src/commands/doctor.test.ts` — Unit tests
- `p67/docs/plans/proposal-g-doctor.md` — This document

## Example output

### Healthy state

```
P67 Doctor

  ✓ CLI version: v0.1.0
  ✓ Connection: 2 connection(s), default: my-conn
  ✓ Endpoint reachable: https://example.snowflakecomputing.app
  ✓ Controld healthy: status: ok
  ✓ Snow CLI available: /usr/local/bin/snow

All checks passed!
```

### Unhealthy state

```
P67 Doctor

  ✓ CLI version: v0.1.0
  ✗ Connection: No connections configured
    Run "p67 connection add" to add a connection.
  ✗ Endpoint reachable: No default connection configured
    Run "p67 connection add --set-default" to set a default connection.
  ✗ Controld healthy: No default connection configured
    Run "p67 connection add --set-default" to set a default connection.
  ✗ Snow CLI available: Not found in PATH
    Install the Snowflake CLI: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation

Some checks failed. See hints above for remediation.
```

## How to test

```bash
# Build the CLI
cd tools/p67-cli && bun build ./src/index.ts --compile --outfile ./bin/p67

# Run the doctor command
./bin/p67 doctor

# Run unit tests
cd tools/p67-cli && bun test src/commands/doctor.test.ts

# Run linter
cd tools/p67-cli && pnpm exec biome check --error-on-warnings
```
