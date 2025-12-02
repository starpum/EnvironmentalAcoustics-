#!/bin/bash

# Set location of files

VENV_PATH="/home/acoustic/.env/bin/activate"
PROJECT_DIR="/home/acoustic/Documents/Mesures"
LOG_KEEP=7

# Activate virtual environment
source "$VENV_PATH"

cd "$PROJECT_DIR" || exit 1

LOG_FILE="$PROJECT_DIR/start_flask_on_boot_$(date +'%Y-%m-%d').log"
python LaunchServer.py >> "$LOG_FILE" 2>&1

