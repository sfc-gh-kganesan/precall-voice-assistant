# coco-profile — Example Workflow

Demonstrates `sdk.cortexCode()` with a bundled skill and a named CoCo profile.

## What it tests

1. Calls `sdk.cortexCode({ prompt: '$secret-code What is the secret code?', profile: 'p67-test' })`
2. The SDK writes `config.toml` + `connections.toml` to a temp `$SNOWFLAKE_HOME`
3. Fetches the `p67-test` profile from `CORTEX_CODE.CONFIG.PROFILE_REGISTRY` via `cortex profile add`, falling back to a direct SQL query if that fails
4. Copies `skills/secret-code/SKILL.md` to `$SNOWFLAKE_HOME/cortex/skills/`
5. Writes `skills.json` and runs `cortex -p "..." --profile p67-test --skills skills.json`
6. Checks that the response contains `AURORA-BOREALIS-42` (from the bundled skill)

## Bundled skill

`skills/secret-code/SKILL.md` — instructs CoCo to respond with a known passphrase when asked for the secret code. Verifies that the skill is discovered from disk, not a Snowflake stage.

## Running

```bash
p67 build
p67 workflow deploy --overwrite
p67 workflow run --name coco_profile_test
```

## Key limitations

- `skills/` must be at the workflow root — `p67 build` copies it into the zip automatically.
- `skillRepos` in the profile registry is intentionally empty. CoCo's SQL driver cannot authenticate via PAT in SPCS, so stage downloads are not used.
- Each `sdk.cortexCode()` call gets its own temp `$SNOWFLAKE_HOME` — no state leaks between calls.

## Further reading

- Runtime flow: [`docs/plans/coco-profile-lifecycle.md`](../../../docs/plans/coco-profile-lifecycle.md)
- SDK interface: [`packages/workflow-sdk/src/index.ts`](../../../packages/workflow-sdk/src/index.ts) (`CortexCodeOptions`)
- Implementation: [`services/controld/src/lib/sdk-impl.ts`](../../../services/controld/src/lib/sdk-impl.ts) (`cortexCode` method)
