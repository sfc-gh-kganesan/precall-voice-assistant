# Proposal F: Unique Image Tags per Build

## Problem

SPCS aggressively caches the `:latest` image tag. Pushing a new image with the same `:latest` tag does not guarantee SPCS pulls the updated version, causing stale deployments.

## What was implemented

1. **Unique tag generation** -- Each `make build-controld` or `make build-dash` invocation generates a tag of the form `<git-short-sha>-<unix-timestamp>` (e.g., `a1b2c3d-1711234567`). This tag is written to `.build-tag` so push targets can read it.

2. **Dual-tag push** -- `make push-controld` and `make push-dash` read the tag from `.build-tag`, then push the image under both the unique tag and `:latest`. This ensures SPCS sees a new tag while keeping `:latest` available as a fallback.

3. **Auto-update service specs** -- After pushing, the Makefile uses `sed` to rewrite the image tag in `native-app/controld_service_spec.yml` and `native-app/dashboard_service_spec.yml` to the unique tag. This is a local-only change (the committed version stays at `:latest`).

4. **`.build-tag` in `.gitignore`** -- The tag file is ephemeral and should not be committed.

## How the build/push/deploy cycle works now

```
make build-controld
  -> generates tag (e.g., a1b2c3d-1711234567)
  -> writes tag to .build-tag
  -> builds docker image as controld:<tag>

make push-controld
  -> reads tag from .build-tag
  -> tags image for registry as controld:<tag> and controld:latest
  -> pushes both tags
  -> updates controld_service_spec.yml with the unique tag (local only)

snow app run -c aifde
  -> deploys with the spec pointing to the unique tag
  -> SPCS pulls the new image (cache busted by the new tag)
```

## Example workflow

```bash
# Build, push, and deploy controld
make build-controld SNOW_CONNECTION=aifde
make login push-controld SNOW_CONNECTION=aifde
snow app run -c aifde

# Full deploy (build + push + deploy all services)
make deploy SNOW_CONNECTION=aifde
```

## Files changed

- `Makefile` -- Added `TAG_FILE` variable; modified `build-controld`, `build-dash`, `push-controld`, `push-dash` targets
- `.gitignore` -- Added `.build-tag`
- `native-app/controld_service_spec.yml` -- No change (stays at `:latest` in git; modified locally by push)
- `native-app/dashboard_service_spec.yml` -- No change (stays at `:latest` in git; modified locally by push)
