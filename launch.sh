#!/bin/bash
# This script is intended to be used as a launcher for the onboard-grades-tracker application.
# Please ensure that the file path and any required dependencies are correctly configured 
# before executing this script. Adapt the script to your specific environment and requirements.

SCRIPT_DIR="$HOME/onboard-grades-tracker" # Directory where the script is located
LOG_FILE="$SCRIPT_DIR/cron.log" # Log file path
MAX_LINES=5000 # Maximum number of lines to keep in the log file
START_HOUR=6 # Start hour for the script to run
END_HOUR=21 # End hour for the script to run

# Truncate the log file if it exceeds MAX_LINES
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
        tail -n $MAX_LINES "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
fi

# Check if the current time is between 21:00 and 06:00
CURRENT_HOUR=$(date +%H)
if [ "$CURRENT_HOUR" -ge "$END_HOUR" ] || [ "$CURRENT_HOUR" -lt "$START_HOUR" ]; then
    exit 0
fi

echo "$(date) - Start script" >> $LOG_FILE
/usr/bin/python3 $SCRIPT_DIR/main.py >> $LOG_FILE 2>&1
echo "$(date) - End script" >> $LOG_FILE
echo "" >> $LOG_FILE
