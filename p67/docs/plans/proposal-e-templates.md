# Proposal E: Add Workflow Templates to `p67 init`

## Overview

Adds a `--template` flag to `p67 init` that scaffolds from pre-built workflow examples instead of a blank project. Ships with two built-in templates: `hello-world` (simple 3-node graph) and `hitl` (human-in-the-loop with interrupt).

## What it does

1. **Template source files** — Each template lives under `tools/p67-cli/src/workspace/templates/<name>/` with `.src` extension files that get embedded into the compiled binary via Bun's `with { type: 'file' }` import pattern.

2. **`--template <name>` flag** (`-t` short form) — When passed to `p67 init`, scaffolds the project using the template's `src/index.ts` and `manifest.yaml` instead of the default boilerplate. Common files (`.gitignore`, `package.json`, `tsconfig.json`, `LEARN_WORKFLOW.md`, `conf/workflow_graph_schema.json`, `sdk.ts`) are still copied from the existing boilerplate.

3. **Unknown template handling** — If the template name is unrecognized, an error message lists available templates.

4. **`listTemplates()` function** — Exported from `Workspace.ts`, returns the list of available template names. Used by both the CLI help text and the validation logic.

## Templates

| Name | Source | Description |
|------|--------|-------------|
| `hello-world` | `example_workflows/number_one` | Simple 3-node LangGraph workflow (Initialize → Process → Finalize) |
| `hitl` | `example_workflows/with_interrupt` | Human-in-the-loop workflow using `sdk.interrupt()` for approval gates |

## Usage

```bash
# Scaffold with a specific template
p67 init --template hello-world
p67 init -t hitl

# With language and project name
p67 init my-project --template hitl --language typescript
```

## Files changed

- `tools/p67-cli/src/workspace/templates/hello-world/src/index.ts.src` — new
- `tools/p67-cli/src/workspace/templates/hello-world/manifest.yaml.src` — new
- `tools/p67-cli/src/workspace/templates/hitl/src/index.ts.src` — new
- `tools/p67-cli/src/workspace/templates/hitl/manifest.yaml.src` — new
- `tools/p67-cli/src/workspace/Workspace.ts` — added template imports, `templateFiles` map, `bootstrapTemplate()` method, `listTemplates()` export
- `tools/p67-cli/src/commands/init.ts` — added `--template` option, template validation, conditional bootstrap call
- `tools/p67-cli/src/workspace/Workspace.templates.test.ts` — new test file

## Adding new templates

1. Create `tools/p67-cli/src/workspace/templates/<name>/src/index.ts.src` and `manifest.yaml.src`
2. Add `with { type: 'file' }` imports in `Workspace.ts`
3. Add an entry to the `templateFiles` map
