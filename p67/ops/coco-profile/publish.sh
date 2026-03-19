#!/bin/bash
#
# publish-coco-profile.sh
#
# Publishes the P67 CoCo skill as a profile to Snowhouse.
# Run this from a machine with `cortex` CLI and `snow` CLI installed,
# connected to Snowhouse with P67_ADMIN_RL + CORTEX_CODE_MODELING_RL roles.
#
# Prerequisites:
#   - snow CLI authenticated to Snowhouse
#   - cortex CLI installed
#   - SKILL.md exists at ops/coco-profile/skills/p67-cli/SKILL.md
#
# Usage:
#   ./publish-coco-profile.sh
#
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
CONNECTION="snowhouse"
WAREHOUSE="P67_WH"
STAGE_ROLE="P67_ADMIN_RL"               # role for stage/schema operations
REGISTRY_ROLE="CORTEX_CODE_MODELING_RL"  # role for profile registry writes
PROFILE_NAME="p67"
OWNER_TEAM="P67"
DESCRIPTION="P67 agentic workflow platform — CLI usage, workflow authoring, and deployment skills"

# Stage where skills are stored (created below if missing)
# Uses P67_SRC with a dedicated schema — P67_USER_RL gets USAGE on this
# schema only (not the rest of P67_SRC), plus READ on the stage.
SKILL_STAGE_DB="P67"
SKILL_STAGE_SCHEMA="P67.COCO_SKILLS"
SKILL_STAGE="P67.COCO_SKILLS.P67_CLI"
SKILL_STAGE_PATH="@${SKILL_STAGE}/skills/p67-cli/"

# Local skill directory to upload
SKILL_DIR="$(dirname "$0")/skills/p67-cli"

# Allowed roles (comma-separated)
ALLOWED_ROLES="P67_USER_RL"

# Registry table (default — don't change unless you know what you're doing)
REGISTRY_TABLE="CORTEX_CODE.CONFIG.PROFILE_REGISTRY"

# Profile JSON (committed in repo for reproducibility)
PROFILE_JSON="$(dirname "$0")/profile.json"

PROFILE_VERSION=$(python3 -c "import json; print(json.load(open('${PROFILE_JSON}'))['version'])")
echo "==> Version: ${PROFILE_VERSION}"

# ── Step 1: Create schema + stage if they don't exist ────────────────────────
echo "==> Creating schema ${SKILL_STAGE_SCHEMA} and stage ${SKILL_STAGE} (if not exists)..."
snow sql -q "
  USE ROLE ${STAGE_ROLE};
  USE WAREHOUSE ${WAREHOUSE};
  CREATE SCHEMA IF NOT EXISTS ${SKILL_STAGE_SCHEMA}
    COMMENT = 'CoCo skill distribution — minimal access for P67_USER_RL';
  CREATE STAGE IF NOT EXISTS ${SKILL_STAGE}
    COMMENT = 'P67 CoCo skill files';
" -c "${CONNECTION}"

# ── Step 2: Upload skill files to stage ──────────────────────────────────────
echo "==> Uploading skill files from ${SKILL_DIR} to ${SKILL_STAGE_PATH}..."
if [ ! -f "${SKILL_DIR}/SKILL.md" ]; then
  echo "ERROR: ${SKILL_DIR}/SKILL.md not found. Create the skill first."
  exit 1
fi

snow sql -q "
  USE ROLE ${STAGE_ROLE};
  USE WAREHOUSE ${WAREHOUSE};
  PUT 'file://${SKILL_DIR}/SKILL.md' '${SKILL_STAGE_PATH}' AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
" -c "${CONNECTION}"

# Upload any additional files (templates, references, etc.)
for f in "${SKILL_DIR}"/templates/* "${SKILL_DIR}"/references/*; do
  [ -f "$f" ] || continue
  subdir=$(basename "$(dirname "$f")")
  echo "    Uploading ${f} -> ${SKILL_STAGE_PATH}${subdir}/"
  snow sql -q "
    USE ROLE ${STAGE_ROLE};
    USE WAREHOUSE ${WAREHOUSE};
    PUT 'file://${f}' '${SKILL_STAGE_PATH}${subdir}/' AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
  " -c "${CONNECTION}"
done

# ── Step 3: Verify profile JSON exists ────────────────────────────────────────
echo "==> Using profile JSON: ${PROFILE_JSON}"
if [ ! -f "${PROFILE_JSON}" ]; then
  echo "ERROR: ${PROFILE_JSON} not found."
  exit 1
fi
cat "${PROFILE_JSON}"

# ── Step 4: Publish profile ──────────────────────────────────────────────────
echo ""
echo "==> Publishing profile '${PROFILE_NAME}' to ${REGISTRY_TABLE}..."
cortex profile publish "${PROFILE_NAME}" \
  --from-file "${PROFILE_JSON}" \
  --connection "${CONNECTION}" \
  --version "${PROFILE_VERSION}" \
  --registry-table "${REGISTRY_TABLE}"

# ── Step 4b: Set ALLOWED_ROLES (cortex profile publish doesn't support this) ──
echo "==> Setting ALLOWED_ROLES to [${ALLOWED_ROLES}]..."
snow sql -q "
  USE ROLE ${REGISTRY_ROLE};
  USE WAREHOUSE ${WAREHOUSE};
  UPDATE ${REGISTRY_TABLE}
  SET ALLOWED_ROLES = PARSE_JSON('[\"${ALLOWED_ROLES}\"]')
  WHERE CONFIG_NAME = '${PROFILE_NAME}';
" -c "${CONNECTION}"

# ── Step 5: Grant least-privilege access to target role ──────────────────────
# P67_USER_RL gets:
#   - USAGE on database (enter building)
#   - USAGE on COCO_SKILLS schema only (enter one room — not other schemas)
#   - READ on the stage (read skill files)
# They CANNOT see/access any other schema, table, or object in P67_SRC.
echo "==> Granting least-privilege stage access to ${ALLOWED_ROLES}..."
snow sql -q "
  USE ROLE ${STAGE_ROLE};
  USE WAREHOUSE ${WAREHOUSE};
  GRANT USAGE ON DATABASE ${SKILL_STAGE_DB} TO ROLE ${ALLOWED_ROLES};
  GRANT USAGE ON SCHEMA ${SKILL_STAGE_SCHEMA} TO ROLE ${ALLOWED_ROLES};
  GRANT READ ON STAGE ${SKILL_STAGE} TO ROLE ${ALLOWED_ROLES};
" -c "${CONNECTION}"

# ── Step 6: Verify ──────────────────────────────────────────────────────────
echo ""
echo "==> Verifying profile is visible..."
snow sql -q "
  USE ROLE ${STAGE_ROLE};
  USE WAREHOUSE ${WAREHOUSE};
  SELECT CONFIG_NAME, VERSION, ACTIVE, ALLOWED_ROLES
  FROM ${REGISTRY_TABLE}
  WHERE CONFIG_NAME = '${PROFILE_NAME}';
" -c "${CONNECTION}"

echo ""
echo "==> Done! Profile '${PROFILE_NAME}' published."
echo ""
echo "Users can now add it with:"
echo "  cortex profile add ${PROFILE_NAME} -c ${CONNECTION}"
echo ""
echo "Or set it as default:"
echo "  cortex profile add ${PROFILE_NAME} -c ${CONNECTION}"
echo "  cortex profile set-default ${PROFILE_NAME}"
