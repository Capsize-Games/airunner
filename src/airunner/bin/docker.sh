#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
  echo "Creating .env file and setting HOST_HOME..."
  echo HOST_HOME=$HOME > .env
  echo AIRUNNER_HOME_DIR=$HOME/.local/share/airunner >> .env
else
  echo ".env file exists. Checking for HOST_HOME..."
  if ! grep -q "^HOST_HOME=" .env; then
    echo "HOST_HOME not set. Adding HOST_HOME to .env..."
    echo HOST_HOME=$HOME >> .env
    echo AIRUNNER_HOME_DIR=$HOME/.local/share/airunner >> .env
  else
    echo "HOST_HOME is already set in .env."
  fi
fi

# Replace any $HOST_HOME variables in .env with the actual value
if [ -f .env ]; then
  echo "Replacing \$HOST_HOME in .env with actual value..."
  sed -i "s|\$HOST_HOME|$HOME|g" .env
else
  echo ".env file not found. Skipping replacement."
fi

# Get user command
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  docker-compose --env-file .env -f ./package/docker-compose-dev.yml up -d && docker exec -it airunner_dev bash
else
  echo "Executing command: $@"
  docker-compose --env-file .env -f ./package/docker-compose-dev.yml up -d && docker exec -it airunner_dev "$@"
fi
