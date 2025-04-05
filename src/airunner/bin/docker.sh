#!/bin/bash

echo "HOST_HOME=$HOME" > .env

# Get user command
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  docker-compose --env-file .env -f ./package/docker-compose-dev.yml up -d && docker exec -it airunner_dev bash
else
  echo "Executing command: $@"
    docker-compose --env-file .env -f ./package/docker-compose-dev.yml up -d && docker exec -it airunner_dev "$@"
fi
