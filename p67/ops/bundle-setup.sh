#!/bin/sh
#
# setup.sh (bundled)
#
# Unified setup script included in every P67 user bundle.
# Part 1: Installs the p67 CLI binary from the bundle.
# Part 2: Optionally configures the CoCo profile for Cortex Code.
#
# Usage:
#   ./setup.sh            # Install CLI to ~/.local/bin, prompt for CoCo profile
#   ./setup.sh --global   # Install CLI to /usr/local/bin (may require sudo)
#   ./setup.sh --help     # Show help
#
set -eu

# ---------------------------------------------------------------------------
# Locate bundle directory (where this script lives)
# ---------------------------------------------------------------------------
BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ACCOUNT="SFCOGSOPS-SNOWHOUSE_AWS_US_WEST_2"
PROFILE_NAME="p67"
CONNECTIONS_DIR="${HOME}/.snowflake"
CONNECTIONS_FILE="${CONNECTIONS_DIR}/connections.toml"
CONFIG_FILE="${CONNECTIONS_DIR}/config.toml"
INSTALL_GLOBAL=false

# ---------------------------------------------------------------------------
# Colors (disabled if not a terminal)
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
	BOLD='\033[1m'
	GREEN='\033[0;32m'
	YELLOW='\033[0;33m'
	RED='\033[0;31m'
	RESET='\033[0m'
else
	BOLD=''
	GREEN=''
	YELLOW=''
	RED=''
	RESET=''
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { printf "${GREEN}info${RESET}  %s\n" "$*"; }
warn()  { printf "${YELLOW}warn${RESET}  %s\n" "$*"; }
error() { printf "${RED}error${RESET} %s\n" "$*" >&2; }
fatal() { error "$@"; exit 1; }

usage() {
	cat <<'EOF'
P67 Bundle Setup

Usage:
  ./setup.sh [OPTIONS]

Options:
  --global   Install p67 CLI to /usr/local/bin (may require sudo)
  --help     Show this help message

Without --global, the CLI is installed to ~/.local/bin.

This script:
  1. Installs the p67 CLI binary from this bundle
  2. Optionally sets up the CoCo (Cortex Code) profile for P67
EOF
	exit 0
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [ $# -gt 0 ]; do
	case "$1" in
		--global)
			INSTALL_GLOBAL=true
			shift
			;;
		--help|-h)
			usage
			;;
		*)
			fatal "Unknown option: $1 (see --help)"
			;;
	esac
done

# ===========================================================================
# Part 1 — Install CLI binary
# ===========================================================================

install_cli() {
	echo ""
	printf "${BOLD}Part 1: Install p67 CLI${RESET}\n"
	echo ""

	CLI_SRC="${BUNDLE_DIR}/bin/p67"

	if [ ! -f "${CLI_SRC}" ]; then
		warn "CLI binary not found at ${CLI_SRC}."
		warn "This bundle may not include a binary for your platform."
		echo "  You can build from source or obtain the correct bundle."
		echo ""
		return 1
	fi

	# Determine install directory
	if [ "${INSTALL_GLOBAL}" = true ]; then
		TARGET_DIR="/usr/local/bin"
	else
		TARGET_DIR="${HOME}/.local/bin"
	fi

	# Create directory if needed
	if [ ! -d "${TARGET_DIR}" ]; then
		info "Creating ${TARGET_DIR}..."
		mkdir -p "${TARGET_DIR}" 2>/dev/null || {
			fatal "Cannot create ${TARGET_DIR}. Try with --global or create it manually."
		}
	fi

	# macOS: clear quarantine attribute on unsigned binary
	OS="$(uname -s)"
	if [ "${OS}" = "Darwin" ]; then
		info "Clearing macOS quarantine flag..."
		xattr -cr "${CLI_SRC}" 2>/dev/null || true
	fi

	chmod +x "${CLI_SRC}"

	# Copy binary (use sudo for global installs if directory is not writable)
	if [ "${INSTALL_GLOBAL}" = true ]; then
		info "Installing to ${TARGET_DIR} (may require sudo)..."
		if [ -w "${TARGET_DIR}" ]; then
			cp "${CLI_SRC}" "${TARGET_DIR}/p67"
		else
			sudo cp "${CLI_SRC}" "${TARGET_DIR}/p67"
		fi
	else
		cp "${CLI_SRC}" "${TARGET_DIR}/p67"
	fi

	INSTALLED_PATH="${TARGET_DIR}/p67"
	info "Installed p67 to ${INSTALLED_PATH}"

	# Check if target dir is in PATH
	case ":${PATH}:" in
		*":${TARGET_DIR}:"*)
			;;
		*)
			warn "${TARGET_DIR} is not in your PATH."
			echo ""
			echo "  Add it by appending to your shell profile:"
			echo ""

			SHELL_NAME="$(basename "${SHELL:-/bin/sh}")"
			case "${SHELL_NAME}" in
				zsh)
					echo "    echo 'export PATH=\"${TARGET_DIR}:\$PATH\"' >> ~/.zshrc"
					echo "    source ~/.zshrc"
					;;
				bash)
					echo "    echo 'export PATH=\"${TARGET_DIR}:\$PATH\"' >> ~/.bashrc"
					echo "    source ~/.bashrc"
					;;
				fish)
					echo "    fish_add_path ${TARGET_DIR}"
					;;
				*)
					echo "    export PATH=\"${TARGET_DIR}:\$PATH\""
					;;
			esac
			echo ""
			;;
	esac

	return 0
}

# ===========================================================================
# Part 2 — CoCo profile setup (conditional)
# ===========================================================================

# Check if a connection exists in either connections.toml or config.toml.
connection_exists() {
	name="$1"
	if [ -f "${CONNECTIONS_FILE}" ] && grep -q "^\[${name}\]" "${CONNECTIONS_FILE}"; then
		return 0
	fi
	if [ -f "${CONFIG_FILE}" ] && grep -q "^\[connections\.${name}\]" "${CONFIG_FILE}"; then
		return 0
	fi
	return 1
}

# List available connections from both files.
list_connections() {
	if [ -f "${CONNECTIONS_FILE}" ]; then
		grep '^\[' "${CONNECTIONS_FILE}" | tr -d '[]' | sed 's/^/  /'
	fi
	if [ -f "${CONFIG_FILE}" ]; then
		grep '^\[connections\.' "${CONFIG_FILE}" | sed 's/\[connections\.\(.*\)\]/  \1/'
	fi
}

install_commands_locally() {
	COMMANDS_SRC="${BUNDLE_DIR}/commands"
	COMMANDS_DEST="${HOME}/.snowflake/cortex/commands"

	if [ -d "${COMMANDS_SRC}" ]; then
		info "Copying CoCo commands to ${COMMANDS_DEST}..."
		mkdir -p "${COMMANDS_DEST}"
		cp "${COMMANDS_SRC}"/*.md "${COMMANDS_DEST}/"
		info "Commands installed. They'll be available when Cortex Code is installed."
	fi
}

setup_coco_profile() {
	echo ""
	printf "${BOLD}Part 2: CoCo Profile Setup${RESET}\n"
	echo ""

	PROFILE_CONFIGURED=false

	# Check if cortex CLI exists
	if ! command -v cortex >/dev/null 2>&1; then
		warn "'cortex' CLI not found. Skipping profile setup."
		echo "  Install Cortex Code later: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-code"
		echo ""
		install_commands_locally
		return
	fi

	# Skip if non-interactive
	if [ ! -t 0 ]; then
		info "Non-interactive session detected. Skipping CoCo profile prompt."
		install_commands_locally
		return
	fi

	printf "  Set up the P67 CoCo profile? [Y/n] "
	read -r answer </dev/tty
	case "${answer}" in
		[nN]|[nN][oO])
			info "Skipping CoCo profile setup."
			install_commands_locally
			return
			;;
	esac

	# --- Connection setup (adapted from ops/coco-profile/setup.sh) ---

	echo ""
	echo "  How would you like to connect to Snowhouse?"
	echo ""
	echo "    1) Create a new snowhouse connection (recommended if first time)"
	echo "    2) Use an existing connection"
	echo ""
	printf "  Choose [1/2]: "
	read -r choice </dev/tty

	CONNECTION=""

	case "${choice}" in
		1)
			echo ""
			printf "  Enter your Snowflake username (e.g. VB): "
			read -r SF_USER </dev/tty
			if [ -z "${SF_USER}" ]; then
				error "Username cannot be empty."
				install_commands_locally
				return
			fi
			SF_USER=$(echo "${SF_USER}" | tr '[:lower:]' '[:upper:]')

			mkdir -p "${CONNECTIONS_DIR}"

			if connection_exists "snowhouse"; then
				echo ""
				warn "A 'snowhouse' connection already exists."
				printf "  Overwrite it? [y/N]: "
				read -r overwrite </dev/tty
				if [ "${overwrite}" != "y" ] && [ "${overwrite}" != "Y" ]; then
					info "Keeping existing connection."
					CONNECTION="snowhouse"
				else
					# Remove existing snowhouse block and re-create
					sed -i.bak '/^\[snowhouse\]/,/^\[/{/^\[snowhouse\]/d;/^\[/!d;}' "${CONNECTIONS_FILE}"
					rm -f "${CONNECTIONS_FILE}.bak"
					echo "" >> "${CONNECTIONS_FILE}"
					cat >> "${CONNECTIONS_FILE}" <<CONNEOF
[snowhouse]
account = "${ACCOUNT}"
user = "${SF_USER}"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
CONNEOF
					info "Updated [snowhouse] in ${CONNECTIONS_FILE}."
					CONNECTION="snowhouse"
				fi
			else
				if [ ! -f "${CONNECTIONS_FILE}" ]; then
					cat > "${CONNECTIONS_FILE}" <<CONNEOF
[snowhouse]
account = "${ACCOUNT}"
user = "${SF_USER}"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
CONNEOF
				else
					echo "" >> "${CONNECTIONS_FILE}"
					cat >> "${CONNECTIONS_FILE}" <<CONNEOF
[snowhouse]
account = "${ACCOUNT}"
user = "${SF_USER}"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
CONNEOF
				fi
				info "Created [snowhouse] in ${CONNECTIONS_FILE}."
				CONNECTION="snowhouse"
			fi
			;;

		2)
			printf "  Connection name [snowhouse]: "
			read -r CONNECTION </dev/tty
			CONNECTION="${CONNECTION:-snowhouse}"

			if ! connection_exists "${CONNECTION}"; then
				error "Connection '${CONNECTION}' not found."
				echo ""
				echo "  Available connections:"
				list_connections
				echo ""
				echo "  Re-run this script and choose option 1 to create a new connection."
				install_commands_locally
				return
			fi
			info "Using connection: ${CONNECTION}"
			;;

		*)
			error "Invalid choice. Skipping CoCo profile setup."
			install_commands_locally
			return
			;;
	esac

	echo ""
	echo "  NOTE: A browser window may open for Snowflake authentication."
	echo "        Approve the login to continue."
	echo ""

	info "Running: cortex profile add ${PROFILE_NAME} -c ${CONNECTION}"
	if cortex profile add "${PROFILE_NAME}" -c "${CONNECTION}"; then
		info "CoCo profile '${PROFILE_NAME}' installed."
	else
		warn "Profile setup failed. You can do it later:"
		echo "    cortex profile add ${PROFILE_NAME} -c ${CONNECTION}"
		install_commands_locally
		return
	fi

	info "Setting ${PROFILE_NAME} as default profile..."
	cortex profile set-default "${PROFILE_NAME}"

	PROFILE_CONFIGURED=true
}

# ===========================================================================
# Part 3 — Summary
# ===========================================================================

print_summary() {
	echo ""
	printf "${BOLD}==========================================${RESET}\n"
	printf "${BOLD}    P67 Setup Complete!${RESET}\n"
	printf "${BOLD}==========================================${RESET}\n"
	echo ""

	if [ -n "${INSTALLED_PATH:-}" ]; then
		echo "  CLI:     ${INSTALLED_PATH}"
	else
		echo "  CLI:     not installed (binary not found in bundle)"
	fi

	if [ "${PROFILE_CONFIGURED:-false}" = true ]; then
		echo "  Profile: ${PROFILE_NAME} (active)"
	else
		echo "  Profile: not configured"
	fi

	echo ""
	echo "  Next steps:"
	echo "    1. p67 connection add prod --endpoint <url> --set-default"
	echo "    2. p67 init my-workflow --template hello-world"
	echo "    3. p67 build && p67 workflow deploy"
	echo ""
}

# ===========================================================================
# Main
# ===========================================================================

main() {
	echo ""
	printf "${BOLD}==========================================${RESET}\n"
	printf "${BOLD}    P67 Bundle Setup${RESET}\n"
	printf "${BOLD}==========================================${RESET}\n"

	install_cli || true
	setup_coco_profile
	print_summary
}

main
