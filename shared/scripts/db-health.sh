#!/bin/bash

echo "=== Database Health Check ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

for TARGET in prod dev; do
    if [ "$TARGET" == "prod" ]; then
        CONTAINER="supabase-db-prod"
    else
        CONTAINER="supabase-db-dev"
    fi

    echo "--- $TARGET ---"

    # Check container running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        echo "Container: Running"
    else
        echo "Container: NOT RUNNING"
        continue
    fi

    # Check connection
    if docker exec $CONTAINER pg_isready -U postgres > /dev/null 2>&1; then
        echo "Connection: Ready"
    else
        echo "Connection: NOT READY"
        continue
    fi

    # Get stats
    TABLES=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')

    SIZE=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT pg_size_pretty(pg_database_size('postgres'));" | tr -d ' ')

    CONNECTIONS=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'postgres';" | tr -d ' ')

    MIGRATION=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null | tr -d ' ' || echo "N/A")

    echo "Tables: $TABLES"
    echo "Size: $SIZE"
    echo "Connections: $CONNECTIONS"
    echo "Migration Version: $MIGRATION"
    echo ""
done

# Compare schemas
echo "--- Schema Comparison ---"
PROD_TABLES=$(docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')
DEV_TABLES=$(docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')

if [ "$PROD_TABLES" == "$DEV_TABLES" ]; then
    echo "Table count: Match ($PROD_TABLES tables)"
else
    echo "Table count: MISMATCH (PROD: $PROD_TABLES, DEV: $DEV_TABLES)"
fi

PROD_VER=$(docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null | tr -d ' ' || echo "0")
DEV_VER=$(docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$PROD_VER" == "$DEV_VER" ]; then
    echo "Migration version: Match (v$PROD_VER)"
else
    echo "Migration version: MISMATCH (PROD: v$PROD_VER, DEV: v$DEV_VER)"
fi
