# GSD: DATABASE MIGRATION SYSTEM

*Prepared: January 18, 2026*
*Purpose: Establish proper database migrations with golang-migrate*
*Estimated Duration: 2-3 hours*

---

## SITUATION

- **DEV** has most schema changes (AEGIS V2, new tables, etc.)
- **PROD** has real data that must be preserved
- Databases have drifted - no versioning, no confidence
- Need: Identical schemas, versioned changes, testable workflow

---

## GOAL

1. Install golang-migrate
2. Audit both databases - document ALL differences
3. Create baseline migration from PROD (preserve existing)
4. Create delta migrations from DEV additions
5. Apply migrations to make PROD match DEV schema
6. Establish migration workflow for all future changes

**CRITICAL:**
- NEVER drop tables in PROD that have data
- BACKUP PROD before any changes
- DEV schema is the source of truth for structure
- PROD data is preserved

---

## SECTION 1: BACKUP PROD DATABASE

### 1.1 Create Full Backup

```bash
# Create backup directory
mkdir -p /opt/leveredge/backups/migrations

# Full PROD backup (schema + data)
docker exec supabase-db-prod pg_dump -U postgres -d postgres \
    --no-owner --no-acl \
    > /opt/leveredge/backups/migrations/prod_full_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -la /opt/leveredge/backups/migrations/
head -50 /opt/leveredge/backups/migrations/prod_full_backup_*.sql
```

### 1.2 Create Schema-Only Backups

```bash
# PROD schema only
docker exec supabase-db-prod pg_dump -U postgres -d postgres \
    --schema-only --no-owner --no-acl -n public \
    > /opt/leveredge/backups/migrations/prod_schema_$(date +%Y%m%d).sql

# DEV schema only
docker exec supabase-db-dev pg_dump -U postgres -d postgres \
    --schema-only --no-owner --no-acl -n public \
    > /opt/leveredge/backups/migrations/dev_schema_$(date +%Y%m%d).sql
```

---

## SECTION 2: INSTALL GOLANG-MIGRATE

### 2.1 Download and Install

```bash
# Download latest release
curl -L https://github.com/golang-migrate/migrate/releases/download/v4.17.0/migrate.linux-amd64.tar.gz -o /tmp/migrate.tar.gz

# Extract
cd /tmp && tar xvzf migrate.tar.gz

# Install
sudo mv migrate /usr/local/bin/
sudo chmod +x /usr/local/bin/migrate

# Verify
migrate --version
```

### 2.2 Create Migration Directory

```bash
mkdir -p /opt/leveredge/migrations
```

---

## SECTION 3: AUDIT DATABASE DIFFERENCES

### 3.1 List All Tables in Both Databases

```bash
# PROD tables
echo "=== PROD TABLES ===" > /tmp/db_audit.txt
docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" >> /tmp/db_audit.txt

# DEV tables
echo -e "\n=== DEV TABLES ===" >> /tmp/db_audit.txt
docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" >> /tmp/db_audit.txt

cat /tmp/db_audit.txt
```

### 3.2 Find Tables in DEV but NOT in PROD

```bash
# Get sorted lists
docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /tmp/prod_tables.txt

docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /tmp/dev_tables.txt

# Tables in DEV but not PROD (need to add)
echo "=== TABLES TO ADD TO PROD ===" 
comm -23 /tmp/dev_tables.txt /tmp/prod_tables.txt

# Tables in PROD but not DEV (investigate - may have data)
echo -e "\n=== TABLES ONLY IN PROD (verify if needed) ==="
comm -13 /tmp/dev_tables.txt /tmp/prod_tables.txt
```

### 3.3 Check Row Counts in PROD

For any tables that exist in PROD, check if they have data:

```bash
# Generate row count query
docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | \
while read table; do
    [ -z "$table" ] && continue
    table=$(echo $table | tr -d ' ')
    count=$(docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
        "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ')
    echo "$table: $count rows"
done
```

### 3.4 Document Schema Differences for Shared Tables

For tables that exist in BOTH databases, compare columns:

```bash
# Create comparison script
cat > /tmp/compare_columns.sh << 'EOF'
#!/bin/bash
TABLE=$1
echo "=== Comparing $TABLE ==="

echo "PROD columns:"
docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT column_name, data_type, is_nullable 
     FROM information_schema.columns 
     WHERE table_name = '$TABLE' AND table_schema = 'public'
     ORDER BY ordinal_position;"

echo -e "\nDEV columns:"
docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT column_name, data_type, is_nullable 
     FROM information_schema.columns 
     WHERE table_name = '$TABLE' AND table_schema = 'public'
     ORDER BY ordinal_position;"
EOF

chmod +x /tmp/compare_columns.sh

# Compare key tables (add more as needed)
/tmp/compare_columns.sh aria_knowledge
/tmp/compare_columns.sh aria_wins
/tmp/compare_columns.sh aegis_credentials
```

### 3.5 Save Audit Results

```bash
# Save full audit to file
cat > /opt/leveredge/migrations/AUDIT_$(date +%Y%m%d).md << 'EOF'
# Database Audit - $(date +%Y-%m-%d)

## Tables to Add to PROD (from DEV)
[paste output from 3.2]

## Tables Only in PROD
[paste output from 3.2]

## Row Counts in PROD
[paste output from 3.3]

## Column Differences
[paste output from 3.4]

## Decision Log
- Table X: Add to PROD via migration
- Table Y: Exists only in PROD, has data, keep it
- etc.
EOF
```

---

## SECTION 4: CREATE SCHEMA MIGRATIONS TABLE

### 4.1 Create in BOTH Databases

This table tracks which migrations have been applied:

```sql
-- Run in PROD
docker exec supabase-db-prod psql -U postgres -d postgres -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version BIGINT PRIMARY KEY,
    dirty BOOLEAN NOT NULL DEFAULT FALSE
);
"

-- Run in DEV
docker exec supabase-db-dev psql -U postgres -d postgres -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version BIGINT PRIMARY KEY,
    dirty BOOLEAN NOT NULL DEFAULT FALSE
);
"
```

---

## SECTION 5: CREATE BASELINE MIGRATION

### 5.1 Migration 001 - Baseline (PROD Current State)

This captures PROD's current schema as the baseline. Both DEV and PROD will be marked as having this applied.

```bash
# Create migration file
cat > /opt/leveredge/migrations/000001_baseline_prod.up.sql << 'EOF'
-- Migration 000001: Baseline from PROD
-- This represents the schema that existed in PROD as of January 18, 2026
-- 
-- NOTE: This migration is for documentation/versioning purposes.
-- Both DEV and PROD already have these tables.
-- We mark it as applied without running it.

-- Tables that exist in PROD:
-- (list them here for documentation, but don't CREATE - they exist)

-- aria_knowledge
-- aria_wins  
-- aria_portfolio_summary
-- aegis_credentials
-- llm_usage
-- [add all PROD tables from audit]

SELECT 'Baseline migration - PROD schema captured' as status;
EOF

# Create down migration (rollback)
cat > /opt/leveredge/migrations/000001_baseline_prod.down.sql << 'EOF'
-- Cannot rollback baseline - this is the starting point
SELECT 'Cannot rollback baseline migration' as status;
EOF
```

### 5.2 Mark Baseline as Applied (Without Running)

```bash
# Mark as applied in PROD
docker exec supabase-db-prod psql -U postgres -d postgres -c \
    "INSERT INTO schema_migrations (version, dirty) VALUES (1, false) ON CONFLICT DO NOTHING;"

# Mark as applied in DEV  
docker exec supabase-db-dev psql -U postgres -d postgres -c \
    "INSERT INTO schema_migrations (version, dirty) VALUES (1, false) ON CONFLICT DO NOTHING;"
```

---

## SECTION 6: CREATE DELTA MIGRATIONS (DEV → PROD)

Based on the audit, create migrations for tables/changes in DEV that need to go to PROD.

### 6.1 Migration 002 - AEGIS V2 Tables

```bash
cat > /opt/leveredge/migrations/000002_aegis_v2.up.sql << 'EOF'
-- Migration 000002: AEGIS V2 Enterprise Credential Management
-- Adds: aegis_credentials_v2, aegis_credential_versions, aegis_audit_log,
--       aegis_rotation_history, aegis_health_checks, aegis_providers

-- Core credential registry (enhanced)
CREATE TABLE IF NOT EXISTS aegis_credentials_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'n8n',
    description TEXT,
    encrypted_value TEXT,
    encryption_key_id TEXT,
    provider_credential_id TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expiring', 'expired', 'rotating', 'failed', 'retired')),
    environment TEXT DEFAULT 'prod',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_health_check TIMESTAMPTZ,
    rotation_enabled BOOLEAN DEFAULT FALSE,
    rotation_interval_hours INT DEFAULT 720,
    rotation_strategy TEXT DEFAULT 'manual',
    next_rotation_at TIMESTAMPTZ,
    alert_threshold_hours INT DEFAULT 168,
    alert_sent BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Credential versions
CREATE TABLE IF NOT EXISTS aegis_credential_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    version INT NOT NULL,
    encrypted_value TEXT,
    provider_credential_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    reason TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    UNIQUE(credential_id, version)
);

-- Audit log
CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    credential_id UUID REFERENCES aegis_credentials_v2(id),
    credential_name TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    target TEXT,
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Rotation history
CREATE TABLE IF NOT EXISTS aegis_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    rotated_at TIMESTAMPTZ DEFAULT NOW(),
    previous_version INT,
    new_version INT,
    trigger TEXT NOT NULL,
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_at TIMESTAMPTZ
);

-- Health checks
CREATE TABLE IF NOT EXISTS aegis_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,
    response_time_ms INT,
    details JSONB DEFAULT '{}',
    error_message TEXT
);

-- Provider registry
CREATE TABLE IF NOT EXISTS aegis_providers (
    id SERIAL PRIMARY KEY,
    provider_name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL,
    base_url TEXT,
    validation_endpoint TEXT,
    credential_fields JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_aegis_creds_status ON aegis_credentials_v2(status);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_expires ON aegis_credentials_v2(expires_at);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_env ON aegis_credentials_v2(environment);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_timestamp ON aegis_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_action ON aegis_audit_log(action);

-- Seed providers
INSERT INTO aegis_providers (provider_name, provider_type, base_url, validation_endpoint, credential_fields) VALUES
('openai', 'api_key', 'https://api.openai.com/v1', '/models', '{"api_key": {"type": "secret", "required": true}}'),
('anthropic', 'api_key', 'https://api.anthropic.com/v1', '/messages', '{"api_key": {"type": "secret", "required": true}}'),
('github', 'api_key', 'https://api.github.com', '/user', '{"personal_access_token": {"type": "secret", "required": true}}'),
('cloudflare', 'api_key', 'https://api.cloudflare.com/client/v4', '/user/tokens/verify', '{"api_token": {"type": "secret", "required": true}}'),
('telegram', 'api_key', 'https://api.telegram.org', '/getMe', '{"bot_token": {"type": "secret", "required": true}}'),
('google_oauth', 'oauth2', 'https://oauth2.googleapis.com', '/tokeninfo', '{"client_id": {"type": "string"}, "client_secret": {"type": "secret"}, "refresh_token": {"type": "secret"}}'),
('supabase', 'api_key', NULL, NULL, '{"project_url": {"type": "string"}, "anon_key": {"type": "string"}, "service_role_key": {"type": "secret"}}'),
('caddy_basic_auth', 'basic_auth', NULL, NULL, '{"username": {"type": "string"}, "password_hash": {"type": "secret"}, "config_path": {"type": "string"}}'),
('elevenlabs', 'api_key', 'https://api.elevenlabs.io/v1', '/voices', '{"api_key": {"type": "secret", "required": true}}'),
('sendgrid', 'api_key', 'https://api.sendgrid.com/v3', '/user/profile', '{"api_key": {"type": "secret", "required": true}}'),
('stripe', 'api_key', 'https://api.stripe.com/v1', '/balance', '{"secret_key": {"type": "secret"}, "publishable_key": {"type": "string"}}'),
('fal_ai', 'api_key', 'https://fal.run', '/health', '{"api_key": {"type": "secret", "required": true}}')
ON CONFLICT (provider_name) DO NOTHING;
EOF

cat > /opt/leveredge/migrations/000002_aegis_v2.down.sql << 'EOF'
-- Rollback AEGIS V2
DROP TABLE IF EXISTS aegis_health_checks CASCADE;
DROP TABLE IF EXISTS aegis_rotation_history CASCADE;
DROP TABLE IF EXISTS aegis_audit_log CASCADE;
DROP TABLE IF EXISTS aegis_credential_versions CASCADE;
DROP TABLE IF EXISTS aegis_credentials_v2 CASCADE;
DROP TABLE IF EXISTS aegis_providers CASCADE;
EOF
```

### 6.2 Migration 003 - LLM Cost Tracking Views

```bash
cat > /opt/leveredge/migrations/000003_llm_cost_views.up.sql << 'EOF'
-- Migration 000003: LLM Cost Tracking Views

-- Ensure base table exists
CREATE TABLE IF NOT EXISTS llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT NOT NULL,
    output_tokens INT NOT NULL,
    estimated_cost_usd DECIMAL(10,6),
    context TEXT,
    operation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_agent ON llm_usage(agent_name);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at);

-- Cost summary view
CREATE OR REPLACE VIEW llm_cost_summary AS
SELECT 
    date_trunc('day', created_at) as day,
    agent_name,
    model,
    COUNT(*) as calls,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    SUM(estimated_cost_usd) as total_cost
FROM llm_usage
GROUP BY 1, 2, 3
ORDER BY 1 DESC, total_cost DESC;

-- Daily totals view
CREATE OR REPLACE VIEW llm_daily_costs AS
SELECT 
    date_trunc('day', created_at) as day,
    SUM(estimated_cost_usd) as total_cost,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    COUNT(*) as total_calls
FROM llm_usage
GROUP BY 1
ORDER BY 1 DESC;
EOF

cat > /opt/leveredge/migrations/000003_llm_cost_views.down.sql << 'EOF'
DROP VIEW IF EXISTS llm_daily_costs;
DROP VIEW IF EXISTS llm_cost_summary;
-- Note: Not dropping llm_usage table as it may have data
EOF
```

### 6.3 Additional Migrations

**Create additional migration files for any other tables found in the audit.**

For each table in DEV but not PROD:

```bash
# Template for additional migrations
cat > /opt/leveredge/migrations/000004_[table_name].up.sql << 'EOF'
-- Migration 000004: [Description]
-- Export DDL from DEV:
-- docker exec supabase-db-dev pg_dump -U postgres -d postgres --schema-only -t [table_name]

[paste DDL here]
EOF
```

---

## SECTION 7: APPLY MIGRATIONS TO PROD

### 7.1 First, Apply to DEV (Already Has Tables)

Mark DEV as having all migrations applied since tables already exist:

```bash
# Check current state
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    version

# Force to latest version (tables already exist in DEV)
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    force 3

# Verify
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    version
```

### 7.2 Apply Migrations to PROD

```bash
# Check current state
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    version

# Run migrations (will create new tables)
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    up

# Verify
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    version
```

### 7.3 Verify Tables Match

```bash
# Compare table lists again
docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /tmp/prod_tables_after.txt

docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /tmp/dev_tables_after.txt

# Should show no differences (except maybe schema_migrations)
diff /tmp/prod_tables_after.txt /tmp/dev_tables_after.txt
```

---

## SECTION 8: CREATE MIGRATION HELPER SCRIPTS

### 8.1 Create New Migration Script

```bash
cat > /opt/leveredge/shared/scripts/new-migration.sh << 'EOF'
#!/bin/bash
# new-migration.sh - Create a new database migration
#
# Usage: new-migration.sh <name>
# Example: new-migration.sh add_user_preferences

set -e

NAME=$1
if [ -z "$NAME" ]; then
    echo "Usage: $0 <migration_name>"
    exit 1
fi

MIGRATIONS_DIR="/opt/leveredge/migrations"

# Get next version number
LAST_VERSION=$(ls -1 "$MIGRATIONS_DIR"/*.up.sql 2>/dev/null | sort -V | tail -1 | grep -oP '\d{6}' | head -1)
if [ -z "$LAST_VERSION" ]; then
    NEXT_VERSION="000001"
else
    NEXT_VERSION=$(printf "%06d" $((10#$LAST_VERSION + 1)))
fi

UP_FILE="$MIGRATIONS_DIR/${NEXT_VERSION}_${NAME}.up.sql"
DOWN_FILE="$MIGRATIONS_DIR/${NEXT_VERSION}_${NAME}.down.sql"

cat > "$UP_FILE" << EOSQL
-- Migration $NEXT_VERSION: $NAME
-- Created: $(date '+%Y-%m-%d %H:%M:%S')
--
-- Description: [Add description here]

-- Your SQL here

EOSQL

cat > "$DOWN_FILE" << EOSQL
-- Rollback $NEXT_VERSION: $NAME
--
-- Description: Undo [description]

-- Your rollback SQL here

EOSQL

echo "Created:"
echo "  $UP_FILE"
echo "  $DOWN_FILE"
echo ""
echo "Next steps:"
echo "  1. Edit the migration files"
echo "  2. Test in DEV: migrate-dev up"
echo "  3. Apply to PROD: migrate-prod up"
EOF

chmod +x /opt/leveredge/shared/scripts/new-migration.sh
```

### 8.2 Create Migration Wrapper Scripts

```bash
# DEV migration wrapper
cat > /opt/leveredge/shared/scripts/migrate-dev.sh << 'EOF'
#!/bin/bash
# migrate-dev.sh - Run migrations on DEV database
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    "$@"
EOF

# PROD migration wrapper
cat > /opt/leveredge/shared/scripts/migrate-prod.sh << 'EOF'
#!/bin/bash
# migrate-prod.sh - Run migrations on PROD database
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    "$@"
EOF

chmod +x /opt/leveredge/shared/scripts/migrate-*.sh
```

### 8.3 Create Symlinks for Easy Access

```bash
sudo ln -sf /opt/leveredge/shared/scripts/migrate-dev.sh /usr/local/bin/migrate-dev
sudo ln -sf /opt/leveredge/shared/scripts/migrate-prod.sh /usr/local/bin/migrate-prod
sudo ln -sf /opt/leveredge/shared/scripts/new-migration.sh /usr/local/bin/new-migration
```

---

## SECTION 9: DOCUMENT THE WORKFLOW

### 9.1 Create Migration README

```bash
cat > /opt/leveredge/migrations/README.md << 'EOF'
# LeverEdge Database Migrations

## Quick Reference

```bash
# Check current version
migrate-dev version
migrate-prod version

# Create new migration
new-migration add_something

# Apply all pending migrations
migrate-dev up
migrate-prod up

# Apply specific number of migrations
migrate-dev up 1
migrate-prod up 1

# Rollback last migration
migrate-dev down 1
migrate-prod down 1

# Force version (use carefully)
migrate-dev force <version>
```

## Workflow

1. **Create migration:**
   ```bash
   new-migration descriptive_name
   ```

2. **Edit the generated files:**
   - `000XXX_descriptive_name.up.sql` - Changes to apply
   - `000XXX_descriptive_name.down.sql` - How to rollback

3. **Test in DEV:**
   ```bash
   migrate-dev up
   # Test your changes
   migrate-dev down 1  # Rollback if needed
   ```

4. **Apply to PROD:**
   ```bash
   # Backup first!
   migrate-prod up
   ```

## Rules

1. **Never edit a migration that's been applied to PROD**
2. **Always write a down migration** (even if it's just a comment saying why it can't be rolled back)
3. **Test in DEV first** - always
4. **One migration = one logical change** - don't bundle unrelated changes
5. **Include data migrations carefully** - they can't always be rolled back

## File Format

- Version: 6 digits, zero-padded (000001, 000002, etc.)
- Name: lowercase, underscores (add_user_table, not AddUserTable)
- Extensions: `.up.sql` and `.down.sql`

## Troubleshooting

**Dirty database state:**
```bash
migrate-dev force <last_good_version>
```

**Check what migrations exist:**
```bash
ls -la /opt/leveredge/migrations/*.up.sql
```

**Compare DEV and PROD versions:**
```bash
migrate-dev version
migrate-prod version
```
EOF
```

---

## SECTION 10: UPDATE DOCUMENTATION

### 10.1 Update LESSONS-LEARNED.md

Add to Technical Debt Tracker:
- [x] Database migration system implemented

### 10.2 Update LOOSE-ENDS.md

Mark completed:
- [x] Database mirroring solution

---

## COMPLETION CHECKLIST

- [ ] PROD database backed up
- [ ] golang-migrate installed
- [ ] Audit completed - all differences documented
- [ ] Baseline migration (000001) created and marked applied
- [ ] AEGIS V2 migration (000002) created
- [ ] LLM cost views migration (000003) created
- [ ] Additional migrations created for other DEV-only tables
- [ ] DEV marked at correct version
- [ ] PROD migrations applied successfully
- [ ] Tables verified to match between DEV and PROD
- [ ] Helper scripts created (new-migration, migrate-dev, migrate-prod)
- [ ] README documentation written
- [ ] Git commit with all migration files

---

## GIT COMMIT

```bash
cd /opt/leveredge
git add migrations/
git add shared/scripts/migrate-*.sh
git add shared/scripts/new-migration.sh
git commit -m "Add database migration system with golang-migrate

- Install golang-migrate tool
- Create baseline migration from PROD
- Add AEGIS V2 tables migration
- Add LLM cost tracking views migration
- Create helper scripts (migrate-dev, migrate-prod, new-migration)
- Document migration workflow

DEV and PROD schemas now in sync and versioned."
```

---

## NOTIFICATION

```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "🗄️ DATABASE MIGRATION SYSTEM COMPLETE\n\n✅ golang-migrate installed\n✅ Baseline + 3 migrations created\n✅ PROD schema synced with DEV\n✅ Helper scripts installed\n\nWorkflow: new-migration → migrate-dev up → migrate-prod up",
    "priority": "high"
  }'
```

---

## FUTURE WORKFLOW

From now on, ALL database changes follow this process:

```bash
# 1. Create migration
new-migration add_new_feature_table

# 2. Edit the files
vim /opt/leveredge/migrations/000004_add_new_feature_table.up.sql
vim /opt/leveredge/migrations/000004_add_new_feature_table.down.sql

# 3. Test in DEV
migrate-dev up
# ... test everything ...

# 4. Apply to PROD
migrate-prod up

# 5. Commit
git add migrations/
git commit -m "Migration: add new feature table"
```

**Never again:**
- ❌ Direct SQL on PROD
- ❌ "It works in DEV, hope it works in PROD"
- ❌ Schema drift
- ❌ Unversioned changes

---

*End of GSD*
*Proper migrations. Versioned changes. Confidence.*
