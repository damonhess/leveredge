# Data Plane Migration

## Current State
- **PROD n8n**: Container `n8n` on port 5678 (from /home/damon/stack/)
- **DEV n8n**: Container `n8n-dev` on port 5678 internally (from /home/damon/stack/)
- **Shared Postgres**: Container `n8n-postgres` serving both PROD (n8n db) and DEV (n8n_dev db)

## Target State
- **PROD n8n**: Container `prod-n8n` on port 5678 (from /opt/leveredge/data-plane/prod/n8n/)
- **DEV n8n**: Container `dev-n8n` on port 5680 (from /opt/leveredge/data-plane/dev/n8n/)
- **Separate Postgres**: Each environment has its own postgres container

## CRITICAL: DEV is Source of Truth
DEV has the newer ARIA workflow (Jan 14 vs Jan 13 in PROD).

## Migration Steps

### Step 1: Export DEV Database (Before Migration)
```bash
# Export n8n_dev database from shared postgres
docker exec n8n-postgres pg_dump -U n8n -d n8n_dev > /opt/leveredge/data-plane/dev/n8n_dev_backup.sql
```

### Step 2: Stop Old Containers
```bash
cd /home/damon/stack
docker compose stop n8n n8n-dev n8n-postgres
```

### Step 3: Start New PROD
```bash
cd /opt/leveredge/data-plane/prod/n8n
docker compose up -d
# Wait for healthy
docker compose logs -f
```

### Step 4: Verify PROD
```bash
curl https://n8n.leveredgeai.com/webhook/aria-health
```

### Step 5: Start New DEV
```bash
cd /opt/leveredge/data-plane/dev/n8n
docker compose up -d

# Wait for postgres to be ready, then import database
docker exec -i dev-n8n-postgres psql -U n8n -d n8n_dev < /opt/leveredge/data-plane/dev/n8n_dev_backup.sql
```

### Step 6: Verify DEV
```bash
curl https://dev.n8n.leveredgeai.com/webhook/aria-health
```

### Step 7: Promote ARIA from DEV to PROD
Use n8n-troubleshooter to export ARIA workflows from DEV and import to PROD.

## Rollback
If anything breaks:
```bash
# Stop new containers
docker compose -f /opt/leveredge/data-plane/prod/n8n/docker-compose.yml down
docker compose -f /opt/leveredge/data-plane/dev/n8n/docker-compose.yml down

# Restart old containers
cd /home/damon/stack
docker compose up -d n8n n8n-dev n8n-postgres
```

## Notes
- Data is preserved (using existing volumes)
- Caddy config may need updating to point to new containers
- The control plane (control.n8n.leveredgeai.com) is separate and not affected
