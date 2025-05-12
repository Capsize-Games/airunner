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

if [ "$1" == "--ci" ]; then
  CI_MODE=1
  shift
  echo "Running in CI mode - local volume mounts disabled for Python userbase/cache"
fi

RTX50XX=0
if [ "$1" == "--50xx" ]; then
  RTX50XX=1
  shift
  echo "Using nightly torch version"
fi

# New: Check for --fast-package-test flag
if [ "$1" == "--fast-package-test" ]; then
  if [ "$CI_MODE" -eq 1 ]; then
    FAST_PACKAGE_TEST=1
    echo "Fast package test mode enabled: PyInstaller will use local code and skip rebuilding dependency images."
  else
    echo "Warning: --fast-package-test is intended for --ci mode."
  fi
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

# Export Wayland-specific variables
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

# Set PYTHONUSERBASE to redirect pip installations to .local/share/airunner/python
export PYTHONUSERBASE=$AIRUNNER_HOME_DIR/python

# Only create local directories if not in CI mode
if [ "$CI_MODE" -eq 0 ]; then
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
fi  # End of CI_MODE=0 block

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
  chmod 644 .env
  echo "Created .env file with HOST_HOME=$HOME, HOST_UID=$HOST_UID, HOST_GID=$HOST_GID"
  echo "Added Wayland environment variables: XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR, WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
fi

# Set Docker Compose commands based on CI mode
if [ "$CI_MODE" -eq 1 ]; then
  # CI mode - Use docker-compose files that don't mount local directories
  DOCKER_COMPOSE_BUILD_BASE="docker compose --env-file .env -f ./package/prod/docker-compose-ci.yml"
  DOCKER_COMPOSE_BUILD_RUNTIME="docker compose --env-file .env -f ./package/prod/docker-compose-ci-runtime.yml"
  DOCKER_COMPOSE_RTX50XX_BUILD_RUNTIME="docker compose --env-file .env -f ./package/prod/50xx/docker-compose-ci-runtime-50xx.yml"
  DOCKER_COMPOSE_BUILD_PACKAGE="docker compose --env-file .env -f ./package/prod/docker-compose-ci-package.yml"
  DOCKER_COMPOSE_BUILD_50XX_PACKAGE="docker compose --env-file .env -f ./package/prod/50xx/docker-compose-ci-package-50xx.yml"
  DOCKER_COMPOSE_BUILD_DEV_RUNTIME="docker compose --env-file .env -f ./package/prod/docker-compose-ci.yml"
  
  # Ensure dist directory exists and has correct permissions for CI mode
  echo "Creating dist directory for CI mode outputs..."
  mkdir -p ./dist
  chmod 777 ./dist
else
  # Regular mode with local volume mounts
  DOCKER_COMPOSE_BUILD_BASE="docker compose --env-file .env -f ./package/prod/docker-compose.yml"
  DOCKER_COMPOSE_BUILD_RUNTIME="docker compose --env-file .env -f ./package/prod/docker-compose-linux_build_runtime.yml"
  DOCKER_COMPOSE_BUILD_PACKAGE="docker compose --env-file .env -f ./package/prod/docker-compose-linux_package.yml"
  DOCKER_COMPOSE_BUILD_DEV_RUNTIME="docker compose --env-file .env -f ./package/dev/docker-compose.yml"
  DOCKER_COMPOSE_BUILD_DEV_PACKAGE="docker compose --env-file .env -f ./package/dev/docker-compose-linux_dev_package.yml"
fi

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
  if [ "$RTX50XX" -eq 1 ]; then
    echo "Building with nightly torch version..."
    $DOCKER_COMPOSE_RTX50XX_BUILD_RUNTIME build
  else
    echo "Building with stable torch version..."
    $DOCKER_COMPOSE_BUILD_RUNTIME build
  fi
  exit 0
fi

if [ "$1" == "build_package" ]; then
  echo "Building for Linux production..."
  ACTION_PARAMS="run --build --rm" # Default Docker Compose action parameters
  ENV_PARAMS="" # Default environment parameters

  if [ "$CI_MODE" -eq 1 ] && [ "$FAST_PACKAGE_TEST" -eq 1 ]; then
    ACTION_PARAMS="run --rm" # Remove --build to use existing images
    echo "Executing PyInstaller with local code changes (no dependency image rebuild)."
  fi

  if [ "$CI_MODE" -eq 1 ]; then
    if [ "$RTX50XX" -eq 1 ]; then
      echo "Building with nightly torch version..."
      $DOCKER_COMPOSE_BUILD_50XX_PACKAGE $ACTION_PARAMS $ENV_PARAMS linux_package_50xx_ci /app/package/pyinstaller/build_50xx.sh
    else
      echo "Building with stable torch version..."
      $DOCKER_COMPOSE_BUILD_PACKAGE $ACTION_PARAMS $ENV_PARAMS airunner_package_ci /app/package/pyinstaller/build.sh
    fi
  else
    # Non-CI mode always rebuilds as per original logic
    $DOCKER_COMPOSE_BUILD_PACKAGE run --build --rm airunner_package /app/package/pyinstaller/build.sh
  fi
  exit 0
fi

if [ "$1" == "build_dev_runtime" ]; then
  echo "Building the Docker Compose services for Linux dev packaging..."
  $DOCKER_COMPOSE_BUILD_DEV_RUNTIME build
  exit 0
fi

if [ "$1" == "build_dev_package" ]; then
  echo "Building for Linux production..."
  if [ "$CI_MODE" -eq 1 ]; then
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run --build --rm airunner_prod_ci /app/package/pyinstaller/build_dev.sh
  else
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run --build --rm airunner_dev /app/package/pyinstaller/build_dev.sh
  fi
  exit 0
fi

# Special handling for run_dev command
if [ "$1" == "run_dev" ]; then
  echo "Running airunner in development mode..."
  shift  # Remove 'run_dev' from the arguments
  if [ "$CI_MODE" -eq 1 ]; then
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run --build --rm airunner_prod_ci airunner "$@"
  else
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run --build --rm airunner_dev airunner "$@"
  fi
  exit 0
fi

# Get user command
IMAGE_NAME="airunner:linux"
DISPLAY_SERVER="wayland"
  
# Configure for Wayland with necessary fixes
# CRITICAL: Uses identical configuration to our successful test script
GUI_ARGS="--rm \
  -e QT_QPA_PLATFORM=wayland \
  -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
  -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
  -v $XDG_RUNTIME_DIR:$XDG_RUNTIME_DIR \
  -e GDK_BACKEND=wayland \
  -e XDG_SESSION_TYPE=wayland \
  -e QT_QPA_PLATFORMTHEME=gnome \
  -v /etc/machine-id:/etc/machine-id:ro"

COMMON_ARGS="--rm \
             -v /etc/machine-id:/etc/machine-id:ro \
             -u $(id -u):$(id -g) \
             -w /app"

if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  if [ "$CI_MODE" -eq 1 ]; then
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run $COMMON_ARGS $GUI_ARGS --build --rm airunner_prod_ci bash
  else
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run $COMMON_ARGS $GUI_ARGS --build --rm airunner_dev bash
  fi
else
  if [ "$CI_MODE" -eq 1 ]; then
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run $COMMON_ARGS $GUI_ARGS --build --rm airunner_prod_ci "$@"
  else
    $DOCKER_COMPOSE_BUILD_DEV_RUNTIME run $COMMON_ARGS $GUI_ARGS --build --rm airunner_dev "$@"
  fi
fi
