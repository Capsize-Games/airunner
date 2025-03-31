#!/bin/bash
set -e

# Configure display settings for GUI apps
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Check if we need to set up NVIDIA-related environment
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected, configuring environment..."
    # Set CUDA environment variables if needed
    export PYTORCH_CUDA_ALLOC_CONF=garbage_collection_threshold:0.9,max_split_size_mb:512
fi

# Optional: Initialize database if it doesn't exist
if [ ! -f /app/airunner.db ]; then
    echo "Initializing AIRunner database..."
    python3 -m airunner.setup_database
fi

# Execute the provided command (or default CMD)
exec "$@"