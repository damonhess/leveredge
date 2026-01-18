# LeverEdge Database Management

*Updated: January 18, 2026*

## Quick Reference

```bash
# Check database health
db-health

# Check migration status
migrate-dev version
migrate-prod version

# Create new migration
new-migration add_something

# Apply migrations
migrate-dev up
migrate-prod up

# Rollback
migrate-dev down 1
migrate-prod down 1

# Backup
backup-database prod full
backup-database prod schema
backup-database dev full
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Supabase Stack                        │
├──────────────────────────┬──────────────────────────────┤
│         PROD             │            DEV               │
│   supabase-db-prod       │     supabase-db-dev         │
│   Port: 54322            │     Port: 54323             │
│   Real data              │     Test data               │
├──────────────────────────┴──────────────────────────────┤
│                   Migration System                       │
│              golang-migrate + SQL files                  │
│              /opt/leveredge/migrations/                  │
└─────────────────────────────────────────────────────────┘
```

## Migration Workflow

1. **Create migration:**
   ```bash
   new-migration add_new_feature
   ```

2. **Edit the SQL files:**
   - `000XXX_add_new_feature.up.sql` - Changes to apply
   - `000XXX_add_new_feature.down.sql` - Rollback

3. **Test in DEV:**
   ```bash
   migrate-dev up
   # Test your changes
   ```

4. **Apply to PROD:**
   ```bash
   backup-database prod full  # Always backup first!
   migrate-prod up
   ```

5. **Commit:**
   ```bash
   git add migrations/
   git commit -m "Migration: add new feature"
   ```

## Rules

- **Never edit applied migrations** - Create a new one instead
- **Always write down migrations** - Even if just a comment
- **Test in DEV first** - Always
- **Backup before PROD changes** - Always
- **One migration = one change** - Keep them focused

## Current Migrations

| Version | Name | Description |
|---------|------|-------------|
| 000001 | baseline | Core ARIA tables, LLM usage, n8n histories |
| 000002 | aegis_v2 | AEGIS V2 credential management system |
| 000003 | conclave | Council meeting system tables |
| 000004 | views_functions | Cost views, portfolio summary, triggers |
| 000005 | backup_monitoring | Backup history, system health, events |

## Current Tables

### Core ARIA
- `aria_knowledge` - Knowledge storage
- `aria_wins` - Portfolio wins
- `aria_portfolio_summary` - Portfolio aggregates
- `aria_conversations` - Conversation tracking
- `aria_messages` - Message history
- `llm_usage` - LLM cost tracking

### AEGIS V2 (Credential Management)
- `aegis_credentials_v2` - Encrypted credentials
- `aegis_credential_versions` - Version history
- `aegis_audit_log` - Access audit
- `aegis_rotation_history` - Rotation tracking
- `aegis_health_checks` - Health check results
- `aegis_providers` - Provider registry
- `aegis_credentials` - Legacy compatibility

### CONCLAVE (Council System)
- `council_meetings` - Council meetings
- `council_transcript` - Meeting transcripts
- `council_decisions` - Recorded decisions
- `council_actions` - Action items
- `council_agent_profiles` - Agent definitions
- `domain_supervisors` - Domain ownership

### Monitoring & Infrastructure
- `backup_history` - Backup tracking
- `system_health` - Component health
- `system_events` - Event log
- `db_metrics` - Database metrics
- `agent_health` - Agent status
- `hades_operations` - Rollback operations
- `build_log` - Deployment log
- `llm_model_pricing` - LLM pricing reference
- `llm_daily_summary` - Daily cost aggregation

### Views
- `llm_cost_summary` - Cost by agent/model/day
- `llm_daily_costs` - Daily totals
- `aegis_expiring_credentials` - Expiring soon
- `portfolio_summary` - Portfolio stats

## Backups

- **Location:** `/opt/leveredge/backups/database/`
- **Schedule:** Daily at 2 AM (full PROD backup)
- **Retention:** 30 days
- **Manual:** `backup-database prod full`

## Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| migrate-dev | ~/bin/migrate-dev | Run migrations on DEV |
| migrate-prod | ~/bin/migrate-prod | Run migrations on PROD |
| new-migration | ~/bin/new-migration | Create new migration pair |
| backup-database | ~/bin/backup-database | Manual database backup |
| db-health | ~/bin/db-health | Check both databases |

## Troubleshooting

### Dirty migration state
```bash
# Check current state
migrate-dev version  # Shows "X (dirty)"

# Force to clean state
migrate-dev force X-1
```

### Compare schemas
```bash
db-health
```

### Check specific table
```bash
docker exec supabase-db-prod psql -U postgres -d postgres -c "\d+ table_name"
```

### View migration history
```bash
docker exec supabase-db-prod psql -U postgres -d postgres -c "SELECT * FROM schema_migrations;"
```

### Manual SQL access
```bash
# PROD
docker exec -it supabase-db-prod psql -U postgres -d postgres

# DEV
docker exec -it supabase-db-dev psql -U postgres -d postgres
```

## Known Differences

DEV has 164 tables while PROD has 79. This is intentional:
- DEV contains many experimental and placeholder tables
- PROD only has tables actually needed for production
- Both are at the same migration version (5)

New features should use migrations to ensure PROD gets needed tables.
