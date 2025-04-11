#!/bin/bash

echo "Starting docker"

#docker pull ghcr.io/capsize-games/airunner/airunner:linux

# Detect if running in GitHub Actions
if [ -n "$GITHUB_ACTIONS" ]; then
  # In GitHub Actions, don't use sudo
  USE_SUDO=""
  echo "Running in GitHub Actions - sudo disabled"
else
  # On regular systems, use sudo
  USE_SUDO="sudo"
  echo "Running on regular system - sudo enabled"
fi

# Export HOST_UID and HOST_GID for the current user
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export HOST_HOME=$HOME
export AIRUNNER_HOME_DIR=${HOST_HOME}/.local/share/airunner
TORCH_HUB_DIR=${HOME}/.local/share/airunner/torch/hub

# Set PYTHONUSERBASE to redirect pip installations to .local/share/airunner/python
export PYTHONUSERBASE=$AIRUNNER_HOME_DIR/python
export PYTHONPATH=$PYTHONUSERBASE/python/local/lib/python3.10/dist-packages:$PYTHONPATH

# Ensure the Python directory structure exists with proper permissions before mounting
PYTHON_DIRS=("$PYTHONUSERBASE/bin" "$PYTHONUSERBASE/lib" "$PYTHONUSERBASE/share" "$PYTHONUSERBASE/include")
for dir in "${PYTHON_DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    echo "Creating directory: $dir"
    mkdir -p "$dir"
  fi
  # Set proper permissions, use sudo conditionally
  chmod 775 "$dir"
  $USE_SUDO chown $HOST_UID:$HOST_GID "$dir"
done

# Ensure the target directory exists
if [ ! -d "$PYTHONUSERBASE" ]; then
  mkdir -p "$PYTHONUSERBASE"
fi

# Ensure the pip cache directory exists and has the correct permissions on the host
CACHE_DIR="$AIRUNNER_HOME_DIR/.cache/pip"
if [ ! -d "$CACHE_DIR" ]; then
  echo "Creating pip cache directory: $CACHE_DIR"
  mkdir -p "$CACHE_DIR"
fi
$USE_SUDO chmod -R 755 "$CACHE_DIR"
$USE_SUDO chown -R $HOST_UID:$HOST_GID "$CACHE_DIR"

# Ensure build and dist exist and have correct permissions
BUILD_DIR="/app/build"
if [ ! -d "$BUILD_DIR" ]; then
  echo "Creating directory: $BUILD_DIR"
  mkdir -p "$BUILD_DIR"
fi
$USE_SUDO chmod -R 755 "$BUILD_DIR"
$USE_SUDO chown -R $HOST_UID:$HOST_GID "$BUILD_DIR"

DIST_DIR="/app/dist"
if [ ! -d "$DIST_DIR" ]; then
  echo "Creating directory: $DIST_DIR"
  mkdir -p "$DIST_DIR"
fi
$USE_SUDO chmod -R 755 "$DIST_DIR"
$USE_SUDO chown -R $HOST_UID:$HOST_GID "$DIST_DIR"

# Ensure the log file exists and has the correct permissions
LOG_FILE="${HOME}/.local/share/airunner/airunner.log"
if [ ! -f "$LOG_FILE" ]; then
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"
fi
chmod 664 "$LOG_FILE"  # Allow read/write for owner and group
$USE_SUDO chown $HOST_UID:$HOST_GID "$LOG_FILE"  # Set ownership to the current user and group

# Ensure the parent directory has the correct permissions
PYTHON_DIR=$AIRUNNER_HOME_DIR/python
if [ -d "$PYTHON_DIR" ]; then
  if [ $(stat -c "%a" "$PYTHON_DIR") -ne 775 ]; then
    echo "Setting permissions for $PYTHON_DIR"
  fi
else
  mkdir -p "$PYTHON_DIR"
  mkdir -p "$PYTHON_DIR/bin"
  mkdir -p "$PYTHON_DIR/lib"
  mkdir -p "$PYTHON_DIR/include"
  mkdir -p "$PYTHON_DIR/share"
fi
$USE_SUDO chmod -R 775 "$PYTHON_DIR"
$USE_SUDO chown -R $HOST_UID:$HOST_GID "$PYTHON_DIR"

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
    $USE_SUDO chmod -R 775 "$AIRUNNER_HOME_DIR"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$AIRUNNER_HOME_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $AIRUNNER_HOME_DIR..."
    $USE_SUDO chmod g+s "$AIRUNNER_HOME_DIR"  # Set the group ID on new files and directories
  fi
  if [ $(stat -c "%a" "$AIRUNNER_HOME_DIR") -ne 775 ]; then
    echo "Updating permissions for $AIRUNNER_HOME_DIR..."
    $USE_SUDO chmod -R 775 "$AIRUNNER_HOME_DIR"  # Allow read/write/execute for owner and group
  fi
fi

if [ -d "$TORCH_HUB_DIR" ]; then
  echo "Adjusting permissions for $TORCH_HUB_DIR to allow access for all users..."
  # Check if permissions need to be updated
  if [ $(stat -c "%a" "$TORCH_HUB_DIR") -ne 775 ]; then
    echo "Updating permissions for $TORCH_HUB_DIR..."
    $USE_SUDO chmod -R 775 "$TORCH_HUB_DIR"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$TORCH_HUB_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $TORCH_HUB_DIR..."
    $USE_SUDO chmod g+s "$TORCH_HUB_DIR"  # Set the group ID on new files and directories
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
    -v $PWD/.local/share/airunner/python:/home/appuser/.local/share/airunner/python:rw \
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
    -e PYTHONPATH=/home/appuser/.local/share/airunner/python/local/lib/python3.10/dist-packages:/app \
    -e PYTHONUSERBASE=/home/appuser/.local/share/airunner/python \
    -e HF_CACHE_DIR=/home/appuser/.local/share/airunner/.cache/huggingface \
    -e HF_HOME=/home/appuser/.local/share/airunner/.cache/huggingface \
    -e HF_HUB_DISABLE_TELEMETRY=1 \
    -e XAUTHORITY=/home/appuser/.Xauthority \
    -e DEBIAN_FRONTEND=noninteractive \
    -e TZ=America/Denver \
    -e QT_LOGGING_RULES="*.debug=false;driver.usb.debug=true" \
    -e QT_DEBUG_PLUGINS=0 \
    -e PYTHONLOGLEVEL=WARNING \
    -e QT_QPA_PLATFORM_PLUGIN_PATH=/home/appuser/.local/share/airunner/python/local/lib/python3.10/dist-packages/PySide6/Qt/plugins/platforms \
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
    -e LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/python3.10:/usr/lib/x86_64-linux-gnu/:/usr/local/lib/:/usr/local/lib/python3.10:/home/appuser/.local/share/airunner/python/local/lib/python3.10/dist-packages \
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
