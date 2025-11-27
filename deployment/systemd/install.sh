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

SYSTEM_LOG=0
# Parse CLI options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --system-log)
            SYSTEM_LOG=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Copy service file
echo -e "${YELLOW}Installing systemd service file...${NC}"
cp "$AIRUNNER_DIR/deployment/systemd/airunner-headless.service" /etc/systemd/system/

# Update user in service file
echo -e "${YELLOW}Updating service file with correct user and paths...${NC}"
sed -i "s|User=joe|User=$ACTUAL_USER|g" /etc/systemd/system/airunner-headless.service
sed -i "s|Group=joe|Group=$ACTUAL_USER|g" /etc/systemd/system/airunner-headless.service
sed -i "s|WorkingDirectory=/home/joe/Projects/airunner|WorkingDirectory=$AIRUNNER_DIR|g" /etc/systemd/system/airunner-headless.service
sed -i "s|ExecStart=/home/joe/Projects/airunner/.venv/bin/python|ExecStart=$AIRUNNER_DIR/.venv/bin/python|g" /etc/systemd/system/airunner-headless.service
if [ "$SYSTEM_LOG" -eq 1 ]; then
    LOG_DIR="/var/log/airunner"
    LOG_FILE="$LOG_DIR/headless.log"
else
    LOG_DIR="/home/$ACTUAL_USER/.local/share/airunner"
    LOG_FILE="$LOG_DIR/headless.log"
fi
# Update service to use user's log path
sed -i "s|Environment=\"AIRUNNER_LOG_FILE=/home/joe/.local/share/airunner/headless.log\"|Environment=\"AIRUNNER_LOG_FILE=$LOG_FILE\"|g" /etc/systemd/system/airunner-headless.service
sed -i "s|StandardOutput=append:/home/joe/.local/share/airunner/headless.log|StandardOutput=append:$LOG_FILE|g" /etc/systemd/system/airunner-headless.service
sed -i "s|StandardError=append:/home/joe/.local/share/airunner/headless-error.log|StandardError=append:$LOG_DIR/headless-error.log|g" /etc/systemd/system/airunner-headless.service

# Ensure log directory exists and is owned by the service user
mkdir -p "$LOG_DIR"
if [ "$SYSTEM_LOG" -eq 1 ]; then
    # /var/log typically owned by root; ensure proper permissions for service user
    chown root:root "$LOG_DIR" || true
    chmod 755 "$LOG_DIR" || true
    # Create log file and set owner to service user so non-root service can write
    touch "$LOG_FILE"
    chown "$ACTUAL_USER":"$ACTUAL_USER" "$LOG_FILE"
    chmod 644 "$LOG_FILE"
else
    chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$LOG_DIR"
    touch "$LOG_FILE"
    chown "$ACTUAL_USER":"$ACTUAL_USER" "$LOG_FILE"
    chmod 644 "$LOG_FILE"
fi
touch "$LOG_FILE"
chown "$ACTUAL_USER":"$ACTUAL_USER" "$LOG_FILE"
chmod 644 "$LOG_FILE"
chmod 755 "$LOG_DIR"

# Ensure AIRUNNER_SAVE_LOG_TO_FILE and DEV_ENV set in the service for production
if ! grep -q "AIRUNNER_SAVE_LOG_TO_FILE" /etc/systemd/system/airunner-headless.service; then
    sed -i "/Environment=\"AIRUNNER_LOG_LEVEL/ a Environment=\"AIRUNNER_SAVE_LOG_TO_FILE=1\"" /etc/systemd/system/airunner-headless.service
fi
if ! grep -q "DEV_ENV" /etc/systemd/system/airunner-headless.service; then
    sed -i "/Environment=\"AIRUNNER_SAVE_LOG_TO_FILE/ a Environment=\"DEV_ENV=0\"" /etc/systemd/system/airunner-headless.service
fi

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
