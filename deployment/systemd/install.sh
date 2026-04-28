#!/bin/bash
# Quick setup script for AI Runner headless service
# Run as: sudo bash deployment/systemd/install.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AI Runner Headless Service Installation${NC}"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}Error: Please run as root (use sudo)${NC}"
   exit 1
fi

# Get the actual user (not root when using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_GROUP=$(id -gn "$ACTUAL_USER")
AIRUNNER_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"

find_bundle_python() {
    local candidates=(
        "${AIRUNNER_PYTHON:-}"
        "$AIRUNNER_DIR/venv/bin/python"
        "$AIRUNNER_DIR/.venv/bin/python"
        "$AIRUNNER_DIR/bin/python"
    )
    local candidate

    for candidate in "${candidates[@]}"; do
        if [ -n "$candidate" ] && [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

escape_sed_replacement() {
    printf '%s' "$1" | sed 's/[&]/\\&/g'
}

echo -e "${YELLOW}Configuration:${NC}"
echo "  User: $ACTUAL_USER"
echo "  AI Runner Directory: $AIRUNNER_DIR"
echo ""

# Check if AI Runner directory exists
if [ ! -d "$AIRUNNER_DIR" ]; then
    echo -e "${RED}Error: AI Runner directory not found: $AIRUNNER_DIR${NC}"
    exit 1
fi

# Check if bundle Python exists
if ! BUNDLE_PYTHON=$(find_bundle_python); then
    echo -e "${RED}Error: No bundle Python found under $AIRUNNER_DIR${NC}"
    echo "Expected one of:"
    echo "  $AIRUNNER_DIR/venv/bin/python"
    echo "  $AIRUNNER_DIR/.venv/bin/python"
    echo "  $AIRUNNER_DIR/bin/python"
    exit 1
fi

BUNDLE_ROOT="${AIRUNNER_BUNDLE_ROOT:-$AIRUNNER_DIR}"
BUNDLE_BIN_DIR="$(dirname "$BUNDLE_PYTHON")"

DATA_DIR="${AIRUNNER_DATA_DIR:-/home/$ACTUAL_USER/.local/share/airunner}"
RUNTIME_DIR="$DATA_DIR/runtime"
RUNTIME_CONFIG_DIR="$RUNTIME_DIR/configs"
RUNTIME_LOG_DIR="$RUNTIME_DIR/logs"
RUNTIME_SOCKET_DIR="$RUNTIME_DIR/sockets"
CACHE_DIR="$DATA_DIR/cache"
MODEL_DIR="$DATA_DIR/models"
DAEMON_CONFIG="$RUNTIME_CONFIG_DIR/daemon.yaml"

# Copy service file
echo -e "${YELLOW}Installing systemd service file...${NC}"
cp "$AIRUNNER_DIR/deployment/systemd/airunner-headless.service" /etc/systemd/system/

# Render the relocatable service template
echo -e "${YELLOW}Rendering service file with bundle paths...${NC}"
sed -i \
    -e "s|__AIRUNNER_USER__|$(escape_sed_replacement "$ACTUAL_USER")|g" \
    -e "s|__AIRUNNER_GROUP__|$(escape_sed_replacement "$ACTUAL_GROUP")|g" \
    -e "s|__AIRUNNER_BUNDLE_ROOT__|$(escape_sed_replacement "$BUNDLE_ROOT")|g" \
    -e "s|__AIRUNNER_BIN_DIR__|$(escape_sed_replacement "$BUNDLE_BIN_DIR")|g" \
    -e "s|__AIRUNNER_PYTHON__|$(escape_sed_replacement "$BUNDLE_PYTHON")|g" \
    -e "s|__AIRUNNER_DATA_DIR__|$(escape_sed_replacement "$DATA_DIR")|g" \
    -e "s|__AIRUNNER_RUNTIME_ROOT__|$(escape_sed_replacement "$RUNTIME_DIR")|g" \
    -e "s|__AIRUNNER_RUNTIME_CONFIG_DIR__|$(escape_sed_replacement "$RUNTIME_CONFIG_DIR")|g" \
    -e "s|__AIRUNNER_RUNTIME_LOG_DIR__|$(escape_sed_replacement "$RUNTIME_LOG_DIR")|g" \
    -e "s|__AIRUNNER_RUNTIME_SOCKET_DIR__|$(escape_sed_replacement "$RUNTIME_SOCKET_DIR")|g" \
    -e "s|__AIRUNNER_CACHE_DIR__|$(escape_sed_replacement "$CACHE_DIR")|g" \
    -e "s|__AIRUNNER_MODEL_DIR__|$(escape_sed_replacement "$MODEL_DIR")|g" \
    -e "s|__AIRUNNER_DAEMON_CONFIG__|$(escape_sed_replacement "$DAEMON_CONFIG")|g" \
    /etc/systemd/system/airunner-headless.service

# Ensure runtime directories exist and are owned by the service user
mkdir -p "$DATA_DIR" "$RUNTIME_DIR" "$RUNTIME_CONFIG_DIR"
mkdir -p "$RUNTIME_LOG_DIR" "$RUNTIME_SOCKET_DIR"
mkdir -p "$CACHE_DIR" "$MODEL_DIR"
chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$DATA_DIR"
chmod 700 "$RUNTIME_DIR" "$RUNTIME_CONFIG_DIR" "$RUNTIME_LOG_DIR"
chmod 700 "$RUNTIME_SOCKET_DIR" "$CACHE_DIR" "$MODEL_DIR"

# Reload systemd
echo -e "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload

# Enable service
echo -e "${YELLOW}Enabling service to start at boot...${NC}"
systemctl enable airunner-headless

echo ""
echo -e "${GREEN}✓ Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Start the service:"
echo "     ${YELLOW}sudo systemctl start airunner-headless${NC}"
echo ""
echo "  2. Check status:"
echo "     ${YELLOW}sudo systemctl status airunner-headless${NC}"
echo ""
echo "  3. View logs:"
echo "     ${YELLOW}sudo journalctl -u airunner-headless -f${NC}"
echo ""
echo "  4. Test the server:"
echo "     ${YELLOW}curl http://localhost:8080/health${NC}"
echo ""
