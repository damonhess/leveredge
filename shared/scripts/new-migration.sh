#!/bin/bash
set -e

NAME=$1
if [ -z "$NAME" ]; then
    echo "Usage: new-migration <migration_name>"
    echo "Example: new-migration add_user_preferences"
    exit 1
fi

DIR="/opt/leveredge/migrations"
LAST=$(ls -1 "$DIR"/*.up.sql 2>/dev/null | sort -V | tail -1 | grep -oP '\d{6}' | head -1 || echo "0")
NEXT=$(printf "%06d" $((10#$LAST + 1)))

UP="$DIR/${NEXT}_${NAME}.up.sql"
DOWN="$DIR/${NEXT}_${NAME}.down.sql"

cat > "$UP" << EOSQL
-- Migration $NEXT: $NAME
-- Created: $(date '+%Y-%m-%d %H:%M:%S')

-- Add your SQL here

SELECT 'Migration $NEXT complete' as status;
EOSQL

cat > "$DOWN" << EOSQL
-- Rollback $NEXT: $NAME

-- Add rollback SQL here

EOSQL

echo "Created:"
echo "  $UP"
echo "  $DOWN"
echo ""
echo "Workflow:"
echo "  1. Edit the migration files"
echo "  2. migrate-dev up"
echo "  3. Test in DEV"
echo "  4. migrate-prod up"
echo "  5. git add migrations/ && git commit"
