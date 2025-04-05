#!/bin/bash

# Get user command
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  docker-compose -f ./package/docker-compose-dev.yml up -d && docker exec -it airunner_dev bash
else
  echo "Executing command: $@"
    docker-compose -f ./package/docker-compose-dev.yml up -d && docker exec -it airunner_dev "$@"
fi
