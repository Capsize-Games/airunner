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
AIRUNNER_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"

echo -e "${YELLOW}Configuration:${NC}"
echo "  User: $ACTUAL_USER"
echo "  AI Runner Directory: $AIRUNNER_DIR"
echo ""

# Check if AI Runner directory exists
if [ ! -d "$AIRUNNER_DIR" ]; then
    echo -e "${RED}Error: AI Runner directory not found: $AIRUNNER_DIR${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "$AIRUNNER_DIR/.venv/bin/python" ]; then
    echo -e "${RED}Error: Virtual environment not found at $AIRUNNER_DIR/.venv${NC}"
    echo "Please create a virtual environment first:"
    echo "  cd $AIRUNNER_DIR"
    echo "  python -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

DATA_DIR="/home/$ACTUAL_USER/.local/share/airunner"
RUNTIME_DIR="$DATA_DIR/runtime"
RUNTIME_CONFIG_DIR="$RUNTIME_DIR/configs"
RUNTIME_LOG_DIR="$RUNTIME_DIR/logs"
RUNTIME_SOCKET_DIR="$RUNTIME_DIR/sockets"
CACHE_DIR="$DATA_DIR/cache"
MODEL_DIR="$DATA_DIR/models"

# Copy service file
echo -e "${YELLOW}Installing systemd service file...${NC}"
cp "$AIRUNNER_DIR/deployment/systemd/airunner-headless.service" /etc/systemd/system/

# Update user in service file
echo -e "${YELLOW}Updating service file with correct user and paths...${NC}"
sed -i "s|User=airunner|User=$ACTUAL_USER|g" /etc/systemd/system/airunner-headless.service
sed -i "s|Group=airunner|Group=$ACTUAL_USER|g" /etc/systemd/system/airunner-headless.service
sed -i "s|WorkingDirectory=/opt/airunner|WorkingDirectory=$AIRUNNER_DIR|g" /etc/systemd/system/airunner-headless.service
sed -i "s|ExecStart=/opt/airunner/.venv/bin/python|ExecStart=$AIRUNNER_DIR/.venv/bin/python|g" /etc/systemd/system/airunner-headless.service

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
