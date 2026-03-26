# Proposal B — Auto-Discover Controld Endpoint

## What was implemented

Added a `--discover` flag to `p67 connection add` that auto-discovers the controld endpoint URL by calling `CALL P67.V1.APP_URL()` via the `snow` CLI.

### New files

- **`tools/p67-cli/src/utils/snow-cli.ts`** — Utility module with:
  - `isSnowInstalled()` — checks if the `snow` CLI is available in PATH
  - `discoverEndpoint(snowConnection?)` — shells out to `snow sql` to call `P67.V1.APP_URL()` and parses the endpoint URL from the JSON output
  - `parseEndpointFromOutput(output)` — parses the endpoint URL from `snow sql --format json` output (exported for testability)

- **`tools/p67-cli/src/utils/snow-cli.test.ts`** — Unit tests covering URL parsing, error handling, and mock-based tests for `isSnowInstalled` and `discoverEndpoint`.

### Modified files

- **`tools/p67-cli/src/commands/connection/add.ts`** — Added two new options:
  - `--discover` — triggers auto-discovery of the endpoint URL
  - `--snow-connection <name>` — specifies which Snowflake connection to use with the `snow` CLI

## How it works

1. When `--discover` is passed, the CLI calls `snow sql -q "CALL P67.V1.APP_URL()" --format json` (optionally with `-c <connection>` if `--snow-connection` is provided).
2. The JSON output is parsed to extract the URL from the first row's first column value.
3. The discovered URL is used as the **default** for the interactive endpoint prompt — the user can accept it by pressing Enter or type a different URL to override.
4. If discovery fails (snow not installed, query error, parse error), an error is printed and the prompt falls back to the standard hardcoded default.

## How to test manually

```bash
# Build the CLI
cd tools/p67-cli && bun build ./src/index.ts --compile --outfile ./bin/p67

# Test with --discover (uses default snow connection)
./bin/p67 connection add test-conn --discover

# Test with --discover and a specific snow connection
./bin/p67 connection add test-conn --discover --snow-connection my-sf-conn

# Test without --discover (original behavior, unchanged)
./bin/p67 connection add test-conn

# Run unit tests
bun test src/utils/snow-cli.test.ts
```
