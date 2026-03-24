#!/usr/bin/env bash
# upload_skills.sh -- Package and upload pattern-iq skills to a Snowflake stage.
#
# Usage:
#     ./scripts/upload_skills.sh [--connection <name>]
#
# Requires: uv and a Snowflake connection configured in ~/.snowflake/connections.toml
# Uses the root pyproject.toml's snowflake-connector-python dependency via uv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$PROJECT_ROOT/.cortex/skills"
TARBALL="/tmp/pattern-iq-skills.tar.gz"
CONNECTION="${1:-default}"

# Strip --connection flag if provided
if [ "$CONNECTION" = "--connection" ]; then
    CONNECTION="${2:-default}"
fi

if [ ! -d "$SKILLS_DIR" ]; then
    echo "Error: Skills directory not found at $SKILLS_DIR" >&2
    exit 1
fi

echo "Packaging skills from $SKILLS_DIR..."
tar -czf "$TARBALL" -C "$PROJECT_ROOT" \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='uv.lock' \
    .cortex/skills

echo "Tarball created: $TARBALL ($(du -h "$TARBALL" | cut -f1))"

echo "Uploading to @PATTERN_IQ.PUBLIC.SKILLS_STAGE..."

uv run --project "$PROJECT_ROOT" python -c "
import snowflake.connector
conn = snowflake.connector.connect(connection_name='$CONNECTION')
cur = conn.cursor()
cur.execute(\"CREATE STAGE IF NOT EXISTS PATTERN_IQ.PUBLIC.SKILLS_STAGE COMMENT = 'Stores pattern-extract skill tarballs for CI distribution'\")
cur.execute(\"PUT file://$TARBALL @PATTERN_IQ.PUBLIC.SKILLS_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE\")
result = cur.fetchall()
print(f'Upload result: {result}')
cur.execute('LIST @PATTERN_IQ.PUBLIC.SKILLS_STAGE')
for row in cur.fetchall():
    print(f'  {row[0]}  ({row[1]} bytes)')
cur.close()
conn.close()
"

echo "Done. Skills uploaded to @PATTERN_IQ.PUBLIC.SKILLS_STAGE"
