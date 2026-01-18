#!/bin/bash
# ARIA Prompt Protection - Triggers backup on any change
# This file is SACRED. Changes must be backed up.

ARIA_PROMPT_DIR="/opt/leveredge/control-plane/agents/aria-chat/prompts"
BACKUP_DIR="/opt/leveredge/backups/aria-prompts"
LOG_FILE="/opt/leveredge/logs/aria-prompt-changes.log"

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname $LOG_FILE)"

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aria_prompt_$TIMESTAMP.md"

cp "$ARIA_PROMPT_DIR/aria_system_prompt.txt" "$BACKUP_FILE"

# Log the change
echo "[$TIMESTAMP] ARIA prompt backup created: $BACKUP_FILE" >> "$LOG_FILE"
echo "[$TIMESTAMP] Triggered by: ${1:-manual}" >> "$LOG_FILE"

# Call CHRONOS for official backup (if available)
curl -s -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d "{\"reason\": \"ARIA prompt changed\", \"files\": [\"$ARIA_PROMPT_DIR\"]}" \
  >> "$LOG_FILE" 2>&1 || true

echo "ARIA prompt backed up to: $BACKUP_FILE"
