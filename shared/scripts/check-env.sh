#!/bin/bash
# Check current environment and lock status

LOCK_FILE="/opt/leveredge/.environment-lock"

if [ ! -f "$LOCK_FILE" ]; then
    echo "dev"  # Default to dev if no lock file
    exit 0
fi

source "$LOCK_FILE"

# Check if unlock has expired
if [ -n "$PROD_UNLOCK_UNTIL" ]; then
    EXPIRY=$(date -d "$PROD_UNLOCK_UNTIL" +%s 2>/dev/null || echo 0)
    NOW=$(date +%s)

    if [ "$NOW" -gt "$EXPIRY" ]; then
        # Auto-relock
        /opt/leveredge/shared/scripts/lock-prod.sh > /dev/null
        echo "dev"
        exit 0
    fi
fi

if [ "$PROD_LOCKED" = "true" ]; then
    echo "dev"
else
    echo "prod"
fi
