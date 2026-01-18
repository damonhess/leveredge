#!/bin/bash
set -e

TARGET=${1:-prod}
TYPE=${2:-full}
BACKUP_DIR="/opt/leveredge/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

if [ "$TARGET" == "prod" ]; then
    CONTAINER="supabase-db-prod"
    PORT="54322"
elif [ "$TARGET" == "dev" ]; then
    CONTAINER="supabase-db-dev"
    PORT="54323"
else
    echo "Usage: backup-database [prod|dev] [full|schema]"
    exit 1
fi

FILENAME="${TARGET}_${TYPE}_${TIMESTAMP}.sql"
FILEPATH="$BACKUP_DIR/$FILENAME"

echo "Backing up $TARGET ($TYPE) to $FILEPATH..."

if [ "$TYPE" == "full" ]; then
    docker exec $CONTAINER pg_dump -U postgres -d postgres --no-owner --no-acl > "$FILEPATH"
elif [ "$TYPE" == "schema" ]; then
    docker exec $CONTAINER pg_dump -U postgres -d postgres --schema-only --no-owner --no-acl > "$FILEPATH"
else
    echo "Unknown type: $TYPE (use full or schema)"
    exit 1
fi

# Compress
gzip "$FILEPATH"
FILEPATH="${FILEPATH}.gz"

# Get size
SIZE=$(du -h "$FILEPATH" | cut -f1)

echo "Backup complete: $FILEPATH ($SIZE)"

# Log to database (if prod backup and backup_history exists)
if [ "$TARGET" == "prod" ]; then
    FILE_BYTES=$(stat -c%s "$FILEPATH" 2>/dev/null || stat -f%z "$FILEPATH" 2>/dev/null || echo "0")
    docker exec supabase-db-prod psql -U postgres -d postgres -c "
    INSERT INTO backup_history (backup_type, target, file_path, file_size_bytes, started_at, completed_at, status)
    VALUES ('$TYPE', '$TARGET', '$FILEPATH', $FILE_BYTES, NOW() - INTERVAL '1 minute', NOW(), 'completed')
    ON CONFLICT DO NOTHING;" 2>/dev/null || true
fi

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete 2>/dev/null || true

echo "Done."
