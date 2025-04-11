#!/bin/bash

echo "Starting docker"

# Export HOST_UID and HOST_GID for the current user
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export HOST_HOME=$HOME
export AIRUNNER_HOME_DIR=${HOST_HOME}/.local/share/airunner
TORCH_HUB_DIR=${HOME}/.local/share/airunner/torch/hub

# Ensure the log file exists and has the correct permissions
LOG_FILE="${HOME}/.local/share/airunner/airunner.log"
if [ ! -f "$LOG_FILE" ]; then
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"
fi
chmod 664 "$LOG_FILE"  # Allow read/write for owner and group
chown $HOST_UID:$HOST_GID "$LOG_FILE"  # Set ownership to the current user and group

# Ensure the parent directory has the correct permissions
# recursively set permissions, but skip site-packages
PYTHON_DIR=$AIRUNNER_HOME_DIR/python
if [ -d "$PYTHON_DIR" ]; then
  if [ $(stat -c "%a" "$PYTHON_DIR") -ne 775 ]; then
    echo "Setting permissions for $PYTHON_DIR"
    sudo chmod -R 775 "$PYTHON_DIR"
    sudo chown $HOST_UID:$HOST_GID "$PYTHON_DIR"
  fi
else
  mkdir -p "$PYTHON_DIR"
  mkdir -p "$PYTHON_DIR/site-packages"
  mkdir -p "$PYTHON_DIR/bin"
  mkdir -p "$PYTHON_DIR/lib"
  mkdir -p "$PYTHON_DIR/include"
  mkdir -p "$PYTHON_DIR/share"
  chmod -R 775 "$PYTHON_DIR"
  chown -R $HOST_UID:$HOST_GID "$PYTHON_DIR"
fi

if [ "$DEV_ENV" == "1" ]; then
  DEFAULT_DB_NAME=airunner.dev.db
else
  DEFAULT_DB_NAME=airunner.db
fi

DB_FILE="$HOME/.local/share/airunner/data/$DEFAULT_DB_NAME"
if [ ! -f "$DB_FILE" ]; then
  mkdir -p "$(dirname "$DB_FILE")"
  touch "$DB_FILE"
fi

if [ -d "$AIRUNNER_HOME_DIR" ]; then
  echo "Adjusting permissions for $AIRUNNER_HOME_DIR to allow access for all users..."
  # Check if permissions need to be updated
  if [ $(stat -c "%a" "$AIRUNNER_HOME_DIR") -ne 775 ]; then
    echo "Updating permissions for $AIRUNNER_HOME_DIR..."
    sudo chmod -R 775 "$AIRUNNER_HOME_DIR"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$AIRUNNER_HOME_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $AIRUNNER_HOME_DIR..."
    sudo chmod g+s "$AIRUNNER_HOME_DIR"  # Set the group ID on new files and directories
  fi
  if [ $(stat -c "%a" "$AIRUNNER_HOME_DIR") -ne 775 ]; then
    echo "Updating permissions for $AIRUNNER_HOME_DIR..."
    sudo chmod -R 775 "$AIRUNNER_HOME_DIR"  # Allow read/write/execute for owner and group
  fi
fi

if [ -d "$TORCH_HUB_DIR" ]; then
  echo "Adjusting permissions for $TORCH_HUB_DIR to allow access for all users..."
  # Check if permissions need to be updated
  if [ $(stat -c "%a" "$TORCH_HUB_DIR") -ne 775 ]; then
    echo "Updating permissions for $TORCH_HUB_DIR..."
    sudo chmod -R 775 "$TORCH_HUB_DIR"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$TORCH_HUB_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $TORCH_HUB_DIR..."
    sudo chmod g+s "$TORCH_HUB_DIR"  # Set the group ID on new files and directories
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
  COMPOSE_BAKE=1 $DOCKER_COMPOSE build
  exit 0
fi

if [ "$1" == "linuxbuild-dev" ]; then
  echo "Building for linux..."
  $DOCKER_COMPOSE run --rm airunner_dev sh ./package/pyinstaller/build.sh
  exit 0
fi

if [ "$1" == "linuxbuild-prod" ]; then
  echo "Building for Linux production..."
  docker run --rm \
    --user 1000:1000 \
    -v $PWD:/app:rw \
    -v $PWD/package/entrypoint.sh:/app/package/entrypoint.sh:ro \
    -v $PWD/.local/share/airunner:/home/appuser/.local/share/airunner:rw \
    -v $PWD/.local/share/airunner/data:/home/appuser/.local/share/airunner/data:rw \
    -v $PWD/.local/share/airunner/torch/hub:/home/appuser/.cache/torch/hub:rw \
    -v $PWD/.local/share/airunner/python:/home/appuser/.local:rw \
    -v $PWD/build:/app/build:rw \
    -v $PWD/dist:/app/dist:rw \
    -e HOST_UID=$(id -u) \
    -e HOST_GID=$(id -g) \
    -e UID=$(id -u) \
    -e GID=$(id -g) \
    -e DEV_ENV=0 \
    -e AIRUNNER_ENABLE_OPEN_VOICE=0 \
    -e PYTHONOPTIMIZE=0 \
    -e AIRUNNER_ENVIRONMENT=prod \
    -e AIRUNNER_OS=linux \
    -e PYTORCH_CUDA_ALLOC_CONF=garbage_collection_threshold:0.9,max_split_size_mb:512,expandable_segments:True \
    -e NUMBA_CACHE_DIR=/tmp/numba_cache \
    -e DISABLE_TELEMETRY=1 \
    -e AIRUNNER_LLM_USE_LOCAL=1 \
    -e AIRUNNER_SAVE_LOG_TO_FILE=0 \
    -e AIRUNNER_LOG_LEVEL=WARNING \
    -e AIRUNNER_DISABLE_FACEHUGGERSHIELD=1 \
    -e AIRUNNER_LLM_USE_OPENROUTER=0 \
    -e OPENROUTER_API_KEY="" \
    -e TCL_LIBDIR_PATH=/usr/lib/x86_64-linux-gnu/ \
    -e TK_LIBDIR_PATH=/usr/lib/x86_64-linux-gnu/ \
    -e PYTHONPATH=/home/appuser/.local/lib/python3.10/site-packages:/app \
    -e PIP_USER=1 \
    -e HF_CACHE_DIR=/home/appuser/.local/share/airunner/.cache/huggingface \
    -e HF_HOME=/home/appuser/.local/share/airunner/.cache/huggingface \
    -e HF_HUB_DISABLE_TELEMETRY=1 \
    -e XAUTHORITY=/home/appuser/.Xauthority \
    -e DEBIAN_FRONTEND=noninteractive \
    -e TZ=America/Denver \
    -e QT_LOGGING_RULES="*.debug=false;driver.usb.debug=true" \
    -e QT_DEBUG_PLUGINS=0 \
    -e PYTHONLOGLEVEL=WARNING \
    -e QT_QPA_PLATFORM_PLUGIN_PATH=/home/appuser/.local/lib/python3.10/site-packages/PySide6/Qt/plugins/platforms \
    -e QT_QPA_PLATFORM=xcb \
    -e PYTHONUNBUFFERED=1 \
    -e NO_AT_BRIDGE=1 \
    -e TORCH_USE_CUDA_DSA=1 \
    -e CUDA_LAUNCH_BLOCKING=1 \
    -e TORCH_HOME=/home/appuser/.local/share/airunner/torch/hub \
    -e XDG_CACHE_HOME=/home/appuser/.local/share/airunner/.cache \
    -e TF_ENABLE_ONEDNN_OPTS=0 \
    -e BUTLER_API_KEY="${BUTLER_API_KEY}" \
    -e CR_PAT="${CR_PAT}" \
    -e LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/python3.10:/usr/lib/x86_64-linux-gnu/:/usr/local/lib/:/usr/local/lib/python3.10:/usr/local/lib/python3.10/dist-packages \
    -w /app \
    $DOCKER_IMAGE \
    bash -c "bash /app/package/entrypoint.sh && bash /app/package/pyinstaller/build.sh"
  exit 0
fi

# Get user command
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  echo "$DOCKER_COMPOSE up -d && $DOCKER_EXEC bash"
  $DOCKER_COMPOSE run --rm airunner_dev bash
else
  $DOCKER_COMPOSE run --rm airunner_dev "$@"
fi
