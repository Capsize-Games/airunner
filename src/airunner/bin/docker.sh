#!/bin/bash

echo "Starting docker"

# Export HOST_UID and HOST_GID for the current user
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)

# Ensure the log file exists and has the correct permissions
LOG_FILE="${HOME}/.local/share/airunner/airunner.log"
if [ ! -f "$LOG_FILE" ]; then
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"
fi
chmod 664 "$LOG_FILE"  # Allow read/write for owner and group
chown $HOST_UID:$HOST_GID "$LOG_FILE"  # Set ownership to the current user and group

# Ensure the parent directory has the correct permissions
chmod -R 775 "${HOME}/.local/share/airunner"

DB_FILE="${HOME}/.local/share/airunner/data/airunner.db"
if [ ! -f "$DB_FILE" ]; then
  mkdir -p "$(dirname "$DB_FILE")"
  touch "$DB_FILE"
fi

if [ -d "$AIRUNNER_DIR" ]; then
  echo "Adjusting permissions for $AIRUNNER_DIR to allow access for all users..."
  # Check if permissions need to be updated
  if [ $(stat -c "%a" "$AIRUNNER_DIR") -ne 775 ]; then
    echo "Updating permissions for $AIRUNNER_DIR..."
    sudo chmod -R 775 "$AIRUNNER_DIR"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$AIRUNNER_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $AIRUNNER_DIR..."
    sudo chmod g+s "$AIRUNNER_DIR"  # Set the group ID on new files and directories
  fi
fi

# Dynamically generate asound.conf with all available devices
cat <<EOL > package/asound.conf
pcm.!default {
    type plug
    slave.pcm "dmix:1,0"
    slave.channels 2
}

ctl.!default {
    type hw
    card 1
}

# Add all available recording devices dynamically
$(arecord -l | awk '/card/ {print "pcm.card" NR " {\n    type plug\n    slave.pcm \"hw:" $2 "\"\n}"}')

# Add all available playback devices dynamically
$(aplay -l | awk '/card/ {print "pcm.playback_card" NR " {\n    type plug\n    slave.pcm \"hw:" $2 "\"\n}"}')
EOL

# Check if .env file exists
if [ ! -f .env ]; then
  echo "Creating .env file and setting HOST_HOME..."
  echo HOST_HOME=$HOME > .env
  echo AIRUNNER_HOME_DIR=/home/appuser/.local/share/airunner >> .env
else
  if ! grep -q "^HOST_HOME=" .env; then
    echo "HOST_HOME not set. Adding HOST_HOME to .env..."
    echo HOST_HOME=$HOME >> .env
    echo AIRUNNER_HOME_DIR=/home/appuser/.local/share/airunner >> .env
  fi
fi

# Replace any $HOST_HOME variables in .env with the actual value
if [ -f .env ]; then
  sed -i "s|\$HOST_HOME|$HOME|g" .env
else
  echo ".env file not found. Skipping replacement."
fi

DOCKER_COMPOSE="docker compose --env-file .env -f ./package/docker-compose.yml"
DOCKER_EXEC="docker exec -it airunner_dev"

if [ "$1" == "down" ]; then
  echo "Bringing down the Docker Compose services..."
  $DOCKER_COMPOSE down
  exit 0
fi

if [ "$1" == "up" ]; then
  echo "Bringing down the Docker Compose services..."
  $DOCKER_COMPOSE up
  exit 0
fi

if [ "$1" == "build" ]; then
  echo "Building the Docker Compose services..."
  $DOCKER_COMPOSE build
  exit 0
fi

# Get user command
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  $DOCKER_COMPOSE up -d && $DOCKER_EXEC bash
else
  $DOCKER_COMPOSE up -d && echo "Executing command: $@"
  $DOCKER_EXEC "$@"
fi
