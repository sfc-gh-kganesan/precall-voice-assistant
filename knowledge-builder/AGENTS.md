# AGENTS.MD

## Setup commands

- Install dependencies: `uv sync`
- Add a dependency: `uv add`

## General guideliness

- Use root level README.md for all documentation additions or editing. Keep this README very succinct and logical. Do not use emojis or frivilous language. Do not create additional documentation/markdown files unless explicitly asked.
- Do not run any Git commands without asking for explicit permission.
- schemachange scripts cannot end with a comment
- If authoritative Snowflake documentation is required, and Context7 is installed, use the library ID /websites/snowflake_en.

## Project structure

- schemachange is used to deploy versioned (V), always (A) and repeatable (R - when hash changes) SQL or Jinja SQL scripts to create objects in a target Snowflake account. Versioned scripts will not run again if already present in the change history table.
- dev prod separation is maintained using GitHub Actions environments.
- The SQL scripts create a knowledge processing pipeline, ending in the creation of a Cortex Search service.
