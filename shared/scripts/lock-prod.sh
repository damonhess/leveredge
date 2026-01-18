#!/bin/bash
# Re-lock production access

LOCK_FILE="/opt/leveredge/.environment-lock"
LOG_FILE="/opt/leveredge/logs/prod-access.log"
TIMESTAMP=$(date -Iseconds)

cat > "$LOCK_FILE" << EOF
# LeverEdge Environment Lock
# DO NOT EDIT MANUALLY - Use unlock-prod.sh

CURRENT_ENV=dev
PROD_LOCKED=true
PROD_UNLOCK_UNTIL=
PROD_UNLOCK_REASON=
PROD_UNLOCK_BY=
LAST_MODIFIED=$TIMESTAMP
EOF

echo "[$TIMESTAMP] PROD LOCKED" >> "$LOG_FILE"
echo "🔒 Production LOCKED. Default environment: DEV"
