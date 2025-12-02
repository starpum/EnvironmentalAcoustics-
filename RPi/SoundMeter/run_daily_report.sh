#!/bin/bash

# Daily noise report runner

VENV_PATH="/home/acoustic/.env/bin/activate"
PROJECT_DIR="/home/acoustic/Documents/Mesures"
LOG_KEEP=7

# Activate virtual environment
source "$VENV_PATH"

cd "$PROJECT_DIR" || exit 1

LOG_FILE="$PROJECT_DIR/daily_report_$(date +'%Y-%m-%d').log"
python3 Report_And_Mail.py >> "$LOG_FILE" 2>&1

# keep only the last $LOG_KEEP logs
ls -1t daily_report_*.log | tail -n +$((LOG_KEEP + 1)) | xargs -r rm --
