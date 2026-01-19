# CHRONOS

**Port:** 8010
**Domain:** THE_KEEP
**Status:** ✅ Operational

---

## Identity

**Name:** CHRONOS
**Title:** Master of Time
**Tagline:** "Time bends to CHRONOS"

## Purpose

CHRONOS manages automated backups, scheduling, and time-based operations. It ensures data safety through regular backups and provides rollback capabilities.

---

## API Endpoints

### Health
```
GET /health
```

### Backups

```
POST /backup
{
  "type": "full|incremental",
  "components": ["database", "workflows", "config"]
}

GET /backups
GET /backups/{id}
DELETE /backups/{id}
```

### Restore
```
POST /restore/{backup_id}
{
  "components": ["database"],
  "dry_run": true
}
```

### Schedule
```
GET /schedules
POST /schedules
DELETE /schedules/{id}
```

---

## Backup Types

| Type | Frequency | Retention | Components |
|------|-----------|-----------|------------|
| Full | Daily | 7 days | All |
| Incremental | Hourly | 24 hours | Changed files |
| Database | Every 6 hours | 3 days | PostgreSQL dumps |
| Workflows | On change | 30 days | n8n workflows |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `chronos_backup` | Create a backup |
| `chronos_restore` | Restore from backup |
| `chronos_list_backups` | List available backups |
| `chronos_schedule` | Create scheduled task |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `backup_history` | Backup records |
| `scheduled_tasks` | Cron-like schedules |
| `restore_log` | Restoration history |

---

## Configuration

Environment variables:
- `DATABASE_URL` - Database connection
- `BACKUP_PATH` - Backup storage location
- `S3_BUCKET` - Optional S3 backup destination
- `RETENTION_DAYS` - Default retention period

---

## Integration Points

### Calls To
- PostgreSQL for database dumps
- File system for file backups
- S3 for offsite storage
- HERMES for notifications

### Called By
- Scheduled triggers
- HADES for disaster recovery
- Claude Code before destructive ops

---

## Backup Storage

```
/opt/leveredge/shared/backups/
├── daily/
│   ├── 2026-01-19/
│   │   ├── database.sql.gz
│   │   ├── workflows.json
│   │   └── config.tar.gz
│   └── ...
├── hourly/
│   └── ...
└── manual/
    └── ...
```

---

## Pre-Destructive Backup

Before any destructive operation, create a backup:

```bash
curl -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d '{"type": "full", "reason": "Pre-migration backup"}'
```

---

## Deployment

```bash
docker run -d --name chronos \
  --network leveredge-network \
  -p 8010:8010 \
  -v /opt/leveredge/shared/backups:/backups \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  chronos:dev
```

---

## Changelog

- 2026-01-19: Documentation created
- 2026-01-16: Initial deployment
