#!/bin/bash
#
# setup.sh
#
# One-shot onboarding script for P67 CoCo profile.
# Configures a Snowhouse connection (or uses an existing one),
# then installs and activates the P67 skill profile.
#
# Usage:
#   ./setup.sh
#
set -euo pipefail

ACCOUNT="SFCOGSOPS-SNOWHOUSE_AWS_US_WEST_2"
PROFILE_NAME="p67"
CONNECTIONS_DIR="${HOME}/.snowflake"
CONNECTIONS_FILE="${CONNECTIONS_DIR}/connections.toml"

echo ""
echo "=========================================="
echo "        P67 CoCo Profile Setup"
echo "=========================================="
echo ""

if ! command -v cortex &>/dev/null; then
  echo "ERROR: 'cortex' CLI not found."
  echo ""
  echo "Install Cortex Code Desktop or CLI first, then re-run this script."
  echo "See: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-code"
  exit 1
fi

echo "How would you like to connect to Snowhouse?"
echo ""
echo "  1) Create a new snowhouse connection (recommended if first time)"
echo "  2) Use an existing connection"
echo ""
read -rp "Choose [1/2]: " choice

CONNECTION=""

case "${choice}" in
  1)
    echo ""
    read -rp "Enter your Snowflake username (e.g. VB): " SF_USER
    if [[ -z "${SF_USER}" ]]; then
      echo "ERROR: Username cannot be empty."
      exit 1
    fi
    SF_USER=$(echo "${SF_USER}" | tr '[:lower:]' '[:upper:]')

    mkdir -p "${CONNECTIONS_DIR}"

    if [[ -f "${CONNECTIONS_FILE}" ]] && grep -q '^\[snowhouse\]' "${CONNECTIONS_FILE}"; then
      echo ""
      echo "WARNING: A [snowhouse] connection already exists in ${CONNECTIONS_FILE}."
      read -rp "Overwrite it? [y/N]: " overwrite
      if [[ "${overwrite}" != "y" && "${overwrite}" != "Y" ]]; then
        echo "Keeping existing connection."
        CONNECTION="snowhouse"
      else
        sed -i.bak '/^\[snowhouse\]/,/^\[/{/^\[snowhouse\]/d;/^\[/!d;}' "${CONNECTIONS_FILE}"
        rm -f "${CONNECTIONS_FILE}.bak"
        echo "" >> "${CONNECTIONS_FILE}"
        cat >> "${CONNECTIONS_FILE}" <<EOF
[snowhouse]
account = "${ACCOUNT}"
user = "${SF_USER}"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
EOF
        echo "Updated [snowhouse] in ${CONNECTIONS_FILE}."
        CONNECTION="snowhouse"
      fi
    else
      if [[ ! -f "${CONNECTIONS_FILE}" ]]; then
        cat > "${CONNECTIONS_FILE}" <<EOF
[snowhouse]
account = "${ACCOUNT}"
user = "${SF_USER}"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
EOF
      else
        echo "" >> "${CONNECTIONS_FILE}"
        cat >> "${CONNECTIONS_FILE}" <<EOF
[snowhouse]
account = "${ACCOUNT}"
user = "${SF_USER}"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
EOF
      fi
      echo "Created [snowhouse] in ${CONNECTIONS_FILE}."
      CONNECTION="snowhouse"
    fi
    ;;

  2)
    read -rp "Connection name [snowhouse]: " CONNECTION
    CONNECTION="${CONNECTION:-snowhouse}"

    if [[ -f "${CONNECTIONS_FILE}" ]]; then
      if ! grep -q "^\[${CONNECTION}\]" "${CONNECTIONS_FILE}"; then
        echo "ERROR: Connection '${CONNECTION}' not found in ${CONNECTIONS_FILE}."
        echo ""
        echo "Available connections:"
        grep '^\[' "${CONNECTIONS_FILE}" | tr -d '[]' | sed 's/^/  /'
        echo ""
        echo "Re-run this script and choose option 1 to create a new connection."
        exit 1
      fi
    else
      echo "ERROR: ${CONNECTIONS_FILE} not found."
      echo "Re-run this script and choose option 1 to create a connection."
      exit 1
    fi
    echo "Using connection: ${CONNECTION}"
    ;;

  *)
    echo "Invalid choice. Run the script again and choose 1 or 2."
    exit 1
    ;;
esac

echo ""
echo "NOTE: A browser window may open for Snowflake authentication."
echo "      Approve the login to continue."
echo ""

echo "==> Installing P67 profile..."
cortex profile add "${PROFILE_NAME}" -c "${CONNECTION}"

echo ""
echo "==> Setting P67 as default profile..."
cortex profile set-default "${PROFILE_NAME}"

echo ""
echo "=========================================="
echo "        Setup complete!"
echo "=========================================="
echo ""
echo "The P67 skill is now active in every CoCo session."
echo ""
echo "  Start CoCo:        cortex -c ${CONNECTION}"
echo "  Verify skill:      /skill list"
echo "  Update later:      cortex profile sync ${PROFILE_NAME} -c ${CONNECTION}"
echo ""
