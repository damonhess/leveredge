# n8n Chat Memory Cleanup

Automated maintenance system for archiving and cleaning up old conversations from n8n's chat memory.

## Overview

This cleanup system:
1. Archives old conversations from `n8n_chat_histories` to `aria_chat_archives`
2. Deletes archived records from the source table
3. Runs on a weekly schedule (Sunday at 4 AM)
4. Reports status via HERMES notification system

## Safety Features

- **Archive Before Delete**: Records are always archived before deletion - no data loss
- **Dry Run Mode**: Test the cleanup without making changes
- **Transaction-Based**: All operations are atomic - rollback on failure
- **Detailed Logging**: Full audit trail of all operations

## Files

| File | Description |
|------|-------------|
| `cleanup.py` | Main cleanup script with archive and delete logic |
| `cleanup-workflow.json` | n8n workflow for scheduled execution |
| `schema.sql` | Archive table DDL |
| `requirements.txt` | Python dependencies |

## Installation

### 1. Install Dependencies

```bash
cd /opt/leveredge/maintenance/chat-cleanup
pip install -r requirements.txt
```

### 2. Create Archive Table

Connect to your n8n PostgreSQL database and run:

```bash
# DEV environment
docker exec -i dev-n8n-postgres psql -U n8n -d n8n < schema.sql

# Or manually connect and run
psql -h localhost -p 5432 -U n8n -d n8n -f schema.sql
```

### 3. Import n8n Workflow

Import `cleanup-workflow.json` into n8n:
1. Open n8n UI
2. Go to Workflows
3. Import from file
4. Select `cleanup-workflow.json`
5. Activate the workflow

## Usage

### Manual Execution

```bash
# Dry run (see what would be cleaned up)
python3 cleanup.py --dry-run

# Live run with default settings (30-day retention)
python3 cleanup.py

# Custom retention period
python3 cleanup.py --retention-days 60

# With JSON output (for automation)
python3 cleanup.py --json-output

# Full example with all options
python3 cleanup.py \
  --host localhost \
  --port 5432 \
  --database n8n \
  --user n8n \
  --password yourpassword \
  --retention-days 30 \
  --json-output
```

### Environment Variables

The script supports environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | Database host |
| `POSTGRES_PORT` | 5432 | Database port |
| `POSTGRES_DB` | n8n | Database name |
| `POSTGRES_USER` | n8n | Database user |
| `POSTGRES_PASSWORD` | (empty) | Database password |
| `RETENTION_DAYS` | 30 | Days to retain conversations |

### DEV Environment

For the DEV environment with Docker:

```bash
# Run against dev-n8n-postgres container
python3 cleanup.py \
  --host localhost \
  --port 5432 \
  --database n8n \
  --user n8n \
  --password $DEV_N8N_POSTGRES_PASSWORD \
  --dry-run
```

## Archive Table Schema

```sql
CREATE TABLE aria_chat_archives (
    id SERIAL PRIMARY KEY,
    original_id TEXT NOT NULL,      -- ID from n8n_chat_histories
    session_id TEXT NOT NULL,       -- Chat session identifier
    message JSONB,                  -- Full message content
    created_at TIMESTAMP,           -- Original creation time
    archived_at TIMESTAMP DEFAULT NOW()  -- When archived
);
```

## Workflow Schedule

The n8n workflow runs every Sunday at 4:00 AM (cron: `0 4 * * 0`).

To modify the schedule:
1. Open the workflow in n8n
2. Edit the "Weekly Schedule" node
3. Change the cron expression

## Monitoring

### Cleanup Statistics

Each run produces statistics:
- `records_found` - Number of records older than retention period
- `records_archived` - Number of records copied to archive
- `records_deleted` - Number of records removed from source
- `sessions_affected` - Number of unique chat sessions cleaned

### HERMES Notifications

The workflow reports to HERMES with:
- **Success**: Low priority notification with stats
- **Failure**: High priority alert with error details

### Check Archive Contents

```sql
-- Count archived records
SELECT COUNT(*) FROM aria_chat_archives;

-- View recent archives
SELECT * FROM aria_chat_archives
ORDER BY archived_at DESC
LIMIT 10;

-- Archives by session
SELECT session_id, COUNT(*) as message_count,
       MIN(created_at) as oldest, MAX(created_at) as newest
FROM aria_chat_archives
GROUP BY session_id;
```

## Troubleshooting

### Common Issues

1. **Connection refused**
   - Verify PostgreSQL is running
   - Check host and port settings
   - Ensure network connectivity (Docker networking if applicable)

2. **Permission denied**
   - Verify database user has SELECT, INSERT, DELETE permissions
   - Check credentials

3. **Table not found**
   - Ensure `n8n_chat_histories` exists (created by n8n chat nodes)
   - Run `schema.sql` to create archive table

### Debug Mode

For verbose output, run with Python logging:

```bash
PYTHONUNBUFFERED=1 python3 cleanup.py --dry-run 2>&1 | tee cleanup.log
```

## Recovery

If you need to restore archived data:

```sql
-- View archived messages for a session
SELECT * FROM aria_chat_archives
WHERE session_id = 'your-session-id'
ORDER BY created_at;

-- Restore specific records (manual process)
INSERT INTO n8n_chat_histories (id, "sessionId", message, "createdAt")
SELECT original_id::integer, session_id, message, created_at
FROM aria_chat_archives
WHERE session_id = 'your-session-id';
```

## License

Internal Leveredge maintenance tool.
