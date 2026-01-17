# Backup & Restore Guide

This guide covers backup and restore operations using CHRONOS and HADES.

## Overview

```
+------------------------------------------------------------------+
|                    BACKUP/RESTORE FLOW                            |
|                                                                   |
|  CHRONOS (Backup)                     HADES (Restore)            |
|  +------------------+                 +------------------+        |
|  |  Schedule        |                 |  Rollback        |        |
|  |  On-demand       |                 |  Recovery        |        |
|  |  Pre-deploy      |                 |  Version control |        |
|  +--------+---------+                 +--------+---------+        |
|           |                                    ^                  |
|           v                                    |                  |
|  +------------------+                 +--------+---------+        |
|  |  /opt/leveredge/ |                 |  Restore from    |        |
|  |  shared/backups/ |---------------->|  backup file     |        |
|  +------------------+                 +------------------+        |
|                                                                   |
+------------------------------------------------------------------+
```

## CHRONOS - Backup Manager

Port: 8010

### Create Backup

```bash
curl -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pre-deploy",
    "component": "prod-n8n",
    "reason": "Before workflow update"
  }'
```

Response:
```json
{
  "backup_id": "backup_20260117_120000",
  "type": "pre-deploy",
  "component": "prod-n8n",
  "path": "/opt/leveredge/shared/backups/prod-n8n/backup_20260117_120000.tar.gz",
  "size_mb": 45.2,
  "created_at": "2026-01-17T12:00:00Z"
}
```

### Backup Types

| Type | Description | Retention |
|------|-------------|-----------|
| `pre-deploy` | Before deployments | 7 days |
| `scheduled` | Automatic daily/weekly | 30 days |
| `manual` | On-demand | 90 days |
| `emergency` | Before risky operations | 180 days |

### List Backups

```bash
curl http://localhost:8010/list?component=prod-n8n
```

```json
{
  "backups": [
    {
      "backup_id": "backup_20260117_120000",
      "type": "pre-deploy",
      "component": "prod-n8n",
      "size_mb": 45.2,
      "created_at": "2026-01-17T12:00:00Z"
    },
    {
      "backup_id": "backup_20260117_020000",
      "type": "scheduled",
      "component": "prod-n8n",
      "size_mb": 44.8,
      "created_at": "2026-01-17T02:00:00Z"
    }
  ],
  "total": 2
}
```

### Verify Backup

```bash
curl -X POST http://localhost:8010/verify \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "backup_20260117_120000"}'
```

```json
{
  "backup_id": "backup_20260117_120000",
  "valid": true,
  "integrity_check": "passed",
  "file_count": 156,
  "verified_at": "2026-01-17T12:05:00Z"
}
```

---

## Backup Schedule

CHRONOS runs scheduled backups automatically:

| Schedule | Time (UTC) | Components |
|----------|------------|------------|
| Daily | 2:00 AM | All databases, n8n workflows |
| Weekly | Sunday 3:00 AM | Full system backup |

### Cron Configuration

```yaml
# n8n workflow: CHRONOS-Scheduler
triggers:
  - cron: "0 2 * * *"   # Daily at 2 AM
  - cron: "0 3 * * 0"   # Weekly Sunday 3 AM
```

---

## What Gets Backed Up

### n8n Workflows

```bash
# Export all workflows
docker exec prod-n8n n8n export:workflow --all --output=/tmp/workflows.json
```

Contents:
- All workflow definitions
- Workflow settings
- Workflow tags

### Supabase Database

```bash
# PROD backup
docker exec supabase-db-prod pg_dump -U postgres -d postgres -F c -f /tmp/backup.dump
docker cp supabase-db-prod:/tmp/backup.dump ./prod_backup_$(date +%Y%m%d).dump

# DEV backup
docker exec supabase-db-dev pg_dump -U postgres -d postgres -F c -f /tmp/backup.dump
```

Contents:
- All tables and data
- Functions and triggers
- Indexes
- RLS policies

### Configuration Files

- `/opt/leveredge/config/agent-registry.yaml`
- Environment files (`.env`)
- Docker compose files

### Agent Data

- Event Bus SQLite database
- Agent-specific state files

---

## HADES - Rollback/Recovery

Port: 8008

### Rollback to Backup

```bash
curl -X POST http://localhost:8008/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup_20260117_020000",
    "component": "prod-n8n"
  }'
```

Response:
```json
{
  "status": "completed",
  "backup_id": "backup_20260117_020000",
  "component": "prod-n8n",
  "rolled_back_at": "2026-01-17T12:10:00Z",
  "pre_rollback_backup": "backup_20260117_121000"
}
```

### List Available Versions

```bash
curl http://localhost:8008/versions?component=prod-n8n
```

```json
{
  "versions": [
    {"backup_id": "backup_20260117_120000", "created_at": "2026-01-17T12:00:00Z"},
    {"backup_id": "backup_20260117_020000", "created_at": "2026-01-17T02:00:00Z"},
    {"backup_id": "backup_20260116_020000", "created_at": "2026-01-16T02:00:00Z"}
  ]
}
```

### Emergency Recovery

For full system recovery:

```bash
curl -X POST http://localhost:8008/recover \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup_20260117_020000",
    "components": ["prod-n8n", "supabase", "agents"]
  }'
```

---

## Manual Backup Procedures

### Backup n8n Workflows

```bash
# From inside container
docker exec prod-n8n n8n export:workflow \
  --all \
  --output=/tmp/workflows-$(date +%Y%m%d).json

# Copy to host
docker cp prod-n8n:/tmp/workflows-$(date +%Y%m%d).json \
  /opt/leveredge/shared/backups/workflows/
```

### Backup Supabase

```bash
# Full backup
docker exec supabase-db-prod pg_dump \
  -U postgres \
  -d postgres \
  -F c \
  -f /tmp/supabase_$(date +%Y%m%d).dump

docker cp supabase-db-prod:/tmp/supabase_$(date +%Y%m%d).dump \
  /opt/leveredge/shared/backups/supabase/
```

### Backup Event Bus

```bash
# Copy SQLite database
cp /opt/leveredge/control-plane/event-bus/events.db \
  /opt/leveredge/shared/backups/event-bus/events_$(date +%Y%m%d).db
```

---

## Manual Restore Procedures

### Restore n8n Workflows

```bash
# Copy backup to container
docker cp /opt/leveredge/shared/backups/workflows/workflows-20260117.json \
  prod-n8n:/tmp/

# Import
docker exec prod-n8n n8n import:workflow --input=/tmp/workflows-20260117.json
```

### Restore Supabase

```bash
# Copy backup to container
docker cp /opt/leveredge/shared/backups/supabase/supabase_20260117.dump \
  supabase-db-prod:/tmp/

# Restore (will drop and recreate)
docker exec supabase-db-prod pg_restore \
  -U postgres \
  -d postgres \
  --clean \
  --if-exists \
  /tmp/supabase_20260117.dump
```

!!! warning "Database Restore"
    Restoring the database will overwrite all current data. Create a backup before restoring.

### Restore Event Bus

```bash
# Stop Event Bus
sudo pkill -f "uvicorn.*8099"

# Replace database
cp /opt/leveredge/shared/backups/event-bus/events_20260117.db \
  /opt/leveredge/control-plane/event-bus/events.db

# Restart Event Bus
cd /opt/leveredge/control-plane/event-bus
sudo nohup /usr/local/bin/python3.11 -m uvicorn event_bus:app \
  --host 0.0.0.0 --port 8099 > /tmp/eventbus.log 2>&1 &
```

---

## Disaster Recovery

### Full System Recovery with GAIA

If the entire system needs rebuilding:

```bash
# 1. Ensure GAIA is running
cd /opt/leveredge/gaia
sudo nohup /usr/local/bin/python3.11 -m uvicorn gaia:app \
  --host 0.0.0.0 --port 8000 > /tmp/gaia.log 2>&1 &

# 2. Trigger full rebuild
curl -X POST http://localhost:8000/rebuild \
  -H "Content-Type: application/json" \
  -d '{
    "backup_source": "/opt/leveredge/shared/backups",
    "components": ["all"]
  }'
```

### Recovery Order

1. **Event Bus** - Communication backbone
2. **Supabase** - Database
3. **Control n8n** - Agent workflows
4. **PROD n8n** - Production workflows
5. **Agents** - FastAPI services

---

## Backup Storage

### Local Storage

```
/opt/leveredge/shared/backups/
├── prod-n8n/
│   ├── backup_20260117_120000.tar.gz
│   └── backup_20260117_020000.tar.gz
├── supabase/
│   ├── supabase_20260117.dump
│   └── supabase_20260116.dump
├── event-bus/
│   └── events_20260117.db
└── config/
    └── agent-registry_20260117.yaml
```

### Remote Backup (Recommended)

For production, sync backups to remote storage:

```bash
# S3 sync
aws s3 sync /opt/leveredge/shared/backups/ s3://leveredge-backups/

# rsync to remote server
rsync -avz /opt/leveredge/shared/backups/ backup-server:/backups/leveredge/
```

---

## Best Practices

### Before Major Changes

1. Always trigger CHRONOS backup:
   ```bash
   curl -X POST http://localhost:8010/backup \
     -d '{"type": "pre-deploy", "component": "affected-component"}'
   ```

2. Note the backup_id for potential rollback

3. Verify backup completed successfully

### Backup Verification

- Weekly: Verify backup integrity
- Monthly: Test restore to dev environment
- Quarterly: Full disaster recovery drill

### Retention Policy

| Backup Type | Retention |
|-------------|-----------|
| Pre-deploy | 7 days |
| Daily scheduled | 30 days |
| Weekly scheduled | 90 days |
| Manual/Emergency | 180 days |

---

## Related Documentation

- [Monitoring Guide](monitoring.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Architecture Overview](../architecture/overview.md)
