#!/bin/bash

echo "Starting docker"

# Detect if running in GitHub Actions
if [ -n "$GITHUB_ACTIONS" ]; then
  echo "Running in GitHub Actions"
else
  echo "Running on regular system"
fi

# Check for CI mode flag
CI_MODE=0
FAST_PACKAGE_TEST=0 # New flag for fast testing PyInstaller changes

# New: Check for --fast-package-test flag
if [ "$1" == "--fast-package-test" ]; then
  echo "Warning: --fast-package-test is intended for --ci mode."
  shift
fi

# Function to safely set permissions and handle errors gracefully
safe_set_permissions() {
  local dir="$1"
  local perms="$2"
  local operation="$3" # chmod, chown, or chmod g+s
  
  if [ ! -e "$dir" ]; then
    echo "Directory $dir does not exist, skipping $operation"
    return 0
  fi
  
  # Check if we have write permissions to the directory
  if [ -w "$dir" ]; then
    echo "Setting $operation on $dir..."
    if [ "$operation" == "chmod" ]; then
      chmod $perms "$dir" 2>/dev/null || echo "Warning: Unable to change permissions of $dir (continuing anyway)"
    elif [ "$operation" == "chown" ]; then
      chown $perms "$dir" 2>/dev/null || echo "Warning: Unable to change ownership of $dir (continuing anyway)"
    elif [ "$operation" == "chmod g+s" ]; then
      chmod g+s "$dir" 2>/dev/null || echo "Warning: Unable to set group ID bit on $dir (continuing anyway)"
    fi
  else
    echo "Warning: No write permission for $dir, skipping $operation"
  fi
}

# Export HOST_UID and HOST_GID for the current user
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export HOST_HOME=$HOME
export AIRUNNER_HOME_DIR=${HOST_HOME}/.local/share/airunner
TORCH_HUB_DIR=${HOME}/.local/share/airunner/torch/hub

# Detect available display server (Wayland or X11)
DISPLAY_SERVER="x11"  # Default to X11
if [ -n "$WAYLAND_DISPLAY" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
  echo "Wayland detected: $WAYLAND_DISPLAY"
  DISPLAY_SERVER="wayland"
elif [ -n "$DISPLAY" ]; then
  echo "X11 detected: $DISPLAY"
  DISPLAY_SERVER="x11"
else
  echo "No display server detected, defaulting to X11"
fi

# Export Wayland-specific variables
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

# Set PYTHONUSERBASE to redirect pip installations to .local/share/airunner/python
export PYTHONUSERBASE=$AIRUNNER_HOME_DIR/python

# Only create local directories if not in CI mode
# Ensure the Python directory structure exists with proper permissions before mounting
PYTHON_DIRS=("$PYTHONUSERBASE/bin" "$PYTHONUSERBASE/lib" "$PYTHONUSERBASE/share" "$PYTHONUSERBASE/include")
for dir in "${PYTHON_DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    echo "Creating directory: $dir"
    mkdir -p "$dir"
  fi
  # Set proper permissions
  safe_set_permissions "$dir" "775" "chmod"
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
safe_set_permissions "$CACHE_DIR" "755" "chmod"

# Ensure build and dist exist and have correct permissions
BUILD_DIR="$PWD/build"
if [ ! -d "$BUILD_DIR" ]; then
  echo "Creating directory: $BUILD_DIR"
  mkdir -p "$BUILD_DIR"
fi
safe_set_permissions "$BUILD_DIR" "755" "chmod"

DIST_DIR="$PWD/dist"
if [ ! -d "$DIST_DIR" ]; then
  echo "Creating directory: $DIST_DIR"
  mkdir -p "$DIST_DIR"
fi
safe_set_permissions "$DIST_DIR" "755" "chmod"

# Ensure the log file exists and has the correct permissions
LOG_FILE="${HOME}/.local/share/airunner/airunner.log"
if [ ! -f "$LOG_FILE" ]; then
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"
fi
safe_set_permissions "$LOG_FILE" "664" "chmod"  # Allow read/write for owner and group

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
safe_set_permissions "$PYTHON_DIR" "775" "chmod"

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
    safe_set_permissions "$AIRUNNER_HOME_DIR" "775" "chmod"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$AIRUNNER_HOME_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $AIRUNNER_HOME_DIR..."
    safe_set_permissions "$AIRUNNER_HOME_DIR" "" "chmod g+s"  # Set the group ID on new files and directories
  fi
  if [ $(stat -c "%a" "$AIRUNNER_HOME_DIR") -ne 775 ]; then
    echo "Updating permissions for $AIRUNNER_HOME_DIR..."
    safe_set_permissions "$AIRUNNER_HOME_DIR" "775" "chmod"  # Allow read/write/execute for owner and group
  fi
fi

if [ -d "$TORCH_HUB_DIR" ]; then
  echo "Adjusting permissions for $TORCH_HUB_DIR to allow access for all users..."
  # Check if permissions need to be updated
  if [ $(stat -c "%a" "$TORCH_HUB_DIR") -ne 775 ]; then
    echo "Updating permissions for $TORCH_HUB_DIR..."
    safe_set_permissions "$TORCH_HUB_DIR" "775" "chmod"  # Allow read/write/execute for owner and group
  fi
  # Check if the group ID bit is already set
  if [ $(stat -c "%A" "$TORCH_HUB_DIR" | cut -c 6) != "s" ]; then
    echo "Setting group ID bit on $TORCH_HUB_DIR..."
    safe_set_permissions "$TORCH_HUB_DIR" "" "chmod g+s"  # Set the group ID on new files and directories
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
  # create env file
  echo "HOST_HOME=$HOME" > .env
  echo "HOST_UID=$HOST_UID" >> .env
  echo "HOST_GID=$HOST_GID" >> .env
  # Add Wayland variables
  echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" >> .env
  echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY" >> .env
  echo "DISPLAY=$DISPLAY" >> .env
  chmod 644 .env
  echo "Created .env file with HOST_HOME=$HOME, HOST_UID=$HOST_UID, HOST_GID=$HOST_GID"
  echo "Added display environment variables: DISPLAY=$DISPLAY, XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR, WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
fi

# Set Docker Compose commands based on CI mode
DOCKER_COMPOSE_BUILD_BASE="docker compose --env-file .env -f ./package/prod/docker-compose.yml"
DOCKER_COMPOSE_BUILD_RUNTIME="docker compose --env-file .env -f ./package/prod/docker-compose-linux_build_runtime.yml"
DOCKER_COMPOSE_BUILD_PACKAGE="docker compose --env-file .env -f ./package/prod/docker-compose-linux_package.yml"
DOCKER_COMPOSE_BUILD_DEV_RUNTIME="docker compose --env-file .env -f ./package/dev/docker-compose.yml"
DOCKER_COMPOSE_BUILD_DEV_PACKAGE="docker compose --env-file .env -f ./package/dev/docker-compose-linux_dev_package.yml"

# Add DOCKER_COMPOSE_BUILD_LINUX variable as specified in instructions
DOCKER_COMPOSE_BUILD_LINUX=$DOCKER_COMPOSE_BUILD_DEV_RUNTIME

DOCKER_EXEC="docker exec -it airunner_dev"

if [ "$1" == "build_base" ]; then
  echo "Building the base Docker image..."
  COMPOSE_BAKE=1 $DOCKER_COMPOSE_BUILD_BASE build
  exit 0
fi

if [ "$1" == "build_runtime" ]; then
  echo "Building the Docker Compose services for Linux packaging..."
  $DOCKER_COMPOSE_BUILD_RUNTIME build
  exit 0
fi

if [ "$1" == "build_package" ]; then
  echo "Building for Linux production..."
  $DOCKER_COMPOSE_BUILD_PACKAGE run --build --rm airunner_package /app/package/pyinstaller/build.sh
  exit 0
fi

if [ "$1" == "build_dev_runtime" ]; then
  echo "Building the Docker Compose services for Linux dev packaging..."
  $DOCKER_COMPOSE_BUILD_DEV_RUNTIME build
  exit 0
fi

$DOCKER_COMPOSE_BUILD_DEV_RUNTIME run --build --rm airunner_dev /app/package/pyinstaller/build_dev.sh

# Special handling for run_dev command
$DOCKER_COMPOSE_BUILD_DEV_RUNTIME run --build --rm airunner_dev airunner "$@"

# Get user command
IMAGE_NAME="airunner:linux"
  
echo "Using Wayland display server configuration"
# Configure for Wayland with necessary fixes and X11 fallback
GUI_ARGS="--rm \
  -e QT_QPA_PLATFORM=xcb;wayland \
  -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
  -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
  -v $XDG_RUNTIME_DIR:$XDG_RUNTIME_DIR \
  -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:/tmp/$WAYLAND_DISPLAY \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e GDK_BACKEND=x11,wayland \
  -e XDG_SESSION_TYPE=wayland \
  -e QT_QPA_PLATFORMTHEME=gnome \
  -e QT_DEBUG_PLUGINS=1 \
  -v /etc/machine-id:/etc/machine-id:ro"

COMMON_ARGS="--rm \
             -v /etc/machine-id:/etc/machine-id:ro \
             -u $(id -u):$(id -g) \
             -w /app"

if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run $COMMON_ARGS $GUI_ARGS --build --rm airunner_dev bash
else
  $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run $COMMON_ARGS $GUI_ARGS --build --rm airunner_dev "$@"
fi
