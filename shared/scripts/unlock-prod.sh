#!/bin/bash
# Temporarily unlock production access

set -e

LOCK_FILE="/opt/leveredge/.environment-lock"
LOG_FILE="/opt/leveredge/logs/prod-access.log"
MAX_DURATION=7200  # 2 hours max

usage() {
    echo "Usage: unlock-prod.sh <duration_minutes> <reason>"
    echo "  duration: 1-120 minutes"
    echo "  reason: Why you need prod access (quoted string)"
    echo ""
    echo "Example: unlock-prod.sh 30 'Deploying ARIA V3.2 hotfix'"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

DURATION=$1
REASON="${@:2}"

# Validate duration
if [ "$DURATION" -lt 1 ] || [ "$DURATION" -gt 120 ]; then
    echo "ERROR: Duration must be 1-120 minutes"
    exit 1
fi

# Calculate unlock expiry
UNLOCK_UNTIL=$(date -d "+${DURATION} minutes" -Iseconds)
CURRENT_USER=$(whoami)
TIMESTAMP=$(date -Iseconds)

# Update lock file
cat > "$LOCK_FILE" << EOF
# LeverEdge Environment Lock
# DO NOT EDIT MANUALLY - Use unlock-prod.sh

CURRENT_ENV=prod
PROD_LOCKED=false
PROD_UNLOCK_UNTIL=$UNLOCK_UNTIL
PROD_UNLOCK_REASON="$REASON"
PROD_UNLOCK_BY=$CURRENT_USER
LAST_MODIFIED=$TIMESTAMP
EOF

# Log the access
echo "[$TIMESTAMP] PROD UNLOCKED by $CURRENT_USER for ${DURATION}m: $REASON" >> "$LOG_FILE"

echo "✅ Production UNLOCKED until $UNLOCK_UNTIL"
echo "⚠️  Remember to run 'lock-prod.sh' when done!"
echo ""
echo "Access logged to: $LOG_FILE"
