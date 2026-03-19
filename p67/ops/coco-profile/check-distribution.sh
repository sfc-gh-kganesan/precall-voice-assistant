#!/bin/bash
#
# check-distribution.sh
#
# Shows current P67 CoCo profile distribution status: who has P67_USER_RL
# and onboarding instructions to send them.
#
# To add new users, file a RITM/Lift ticket requesting:
#   GRANT ROLE P67_USER_RL TO USER <username>;
#
# Usage:
#   ./check-distribution.sh
#
set -euo pipefail

CONNECTION="snowhouse"
WAREHOUSE="P67_WH"
ROLE="P67_ADMIN_RL"
TARGET_ROLE="P67_USER_RL"

echo "==> Fetching users with ${TARGET_ROLE}..."
EXISTING_USERS=$(snow sql -q "
  USE ROLE ${ROLE};
  USE WAREHOUSE ${WAREHOUSE};
  SHOW GRANTS OF ROLE ${TARGET_ROLE};
" -c "${CONNECTION}" --format json 2>/dev/null | python3 -c "
import sys, json
for stmt in json.load(sys.stdin):
    for row in stmt:
        if row.get('granted_to') == 'USER':
            print(row['grantee_name'])
" || true)

if [[ -z "${EXISTING_USERS}" ]]; then
  USER_COUNT=0
else
  USER_COUNT=$(echo "${EXISTING_USERS}" | wc -l | tr -d ' ')
fi
echo "    ${USER_COUNT} users currently have ${TARGET_ROLE}:"
echo "${EXISTING_USERS}" | sed 's/^/      /'

echo ""
echo "To add a new user, file a Lift ticket:"
echo "  https://lift.snowflake.com/lift?id=sc_cat_item_guide&table=sc_cat_item&sys_id=949d1acf1b880110cef3419ead4bcbf1"
echo ""
echo "Request:"
echo "    GRANT ROLE ${TARGET_ROLE} TO USER <username>;"
echo ""
echo "============================================================"
echo "  Onboarding instructions to send to users"
echo "============================================================"
echo ""
cat <<'INSTRUCTIONS'
Run the setup script from the P67 repo:

  ./p67/ops/coco-profile/setup.sh

Or manually:

  cortex profile add p67 -c snowhouse
  cortex profile set-default p67

To verify:

  /skill list
INSTRUCTIONS

echo ""
echo "============================================================"
