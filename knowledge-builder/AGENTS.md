# AGENTS.MD

## Setup commands

- Install dependencies: `uv sync`
- Add a dependency: `uv add`
- Run migrations: `just migrate` or `uv run schemachange deploy -C "$SNOW_CONNECTION"`

## General guidelines

- Use root level README.md for all documentation additions or editing. Keep this README very succinct and logical. Do not use emojis or frivolous language. Do not create additional documentation/markdown files unless explicitly asked.
- Do not run any Git commands without asking for explicit permission.
- SQL scripts use Jinja templating (e.g., `{{ KB_DATABASE_NAME }}`) with variables defined in `schemachange-config.yml`.
- schemachange scripts cannot end with a comment
- If authoritative Snowflake documentation is required, and Context7 is installed, use the library ID /websites/snowflake_en.

## Project structure

- SQL scripts in `database/migrations/` follow [schemachange](https://github.com/Snowflake-Labs/schemachange) naming conventions:
  - Versioned scripts (`V<version>__<description>.sql`): Run once, tracked in change history
  - Repeatable scripts (`R__<description>.sql`): Re-run when content changes
- The `justfile` orchestrates deployment: schemachange migrations, Docker image build/push, and Streamlit app deployment.
- Change history is tracked in `KNOWLEDGE_BUILDER.SCHEMACHANGE.CHANGE_HISTORY`.
- The SQL scripts create a knowledge processing pipeline, ending in the creation of a Cortex Search service.
