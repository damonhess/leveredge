# DATA PLANE MIGRATION EXECUTION (UPDATED)

*Execute NOW - January 16, 2026*

## Pre-flight
- [x] CHRONOS backup: __20260116_053456
- [x] docker-compose files created
- [x] .env files created

## Step 0: INVENTORY ALL CONTAINERS FIRST

```bash
echo "=== ALL RUNNING CONTAINERS ==="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"

echo ""
echo "=== DOCKER COMPOSE FILES ==="
find /home/damon -name "docker-compose.yml" -o -name "docker-compose.yaml" 2>/dev/null
```

**STOP after Step 0 and report what containers exist.**

We need to know:
1. Which containers are from /home/damon/stack/
2. Which are standalone
3. What depends on what

## After Inventory - Continue Migration

### Step 1: Export DEV Database
```bash
docker exec n8n-postgres pg_dump -U n8n -d n8n_dev > /opt/leveredge/data-plane/dev/n8n_dev_backup.sql
echo "DEV database exported"
```

### Step 2: Stop ONLY n8n containers (not everything)
```bash
cd /home/damon/stack
docker compose stop n8n n8n-dev
# DO NOT stop other services like OpenProject, Leantime, etc.
echo "n8n containers stopped"
```

### Step 3: Verify Export
```bash
head -50 /opt/leveredge/data-plane/dev/n8n_dev_backup.sql
```

### Step 4: Stop Old n8n Postgres
```bash
cd /home/damon/stack
docker compose stop n8n-postgres
echo "Old postgres stopped"
```

### Step 5: Start New PROD
```bash
cd /opt/leveredge/data-plane/prod/n8n
docker compose up -d
sleep 10
docker compose ps
```

### Step 6: Start New DEV
```bash
cd /opt/leveredge/data-plane/dev/n8n
docker compose up -d
sleep 10
docker compose ps
```

### Step 7: Import DEV Database
```bash
sleep 5
docker exec -i dev-n8n-postgres psql -U n8n -d n8n_dev < /opt/leveredge/data-plane/dev/n8n_dev_backup.sql
echo "DEV database imported"
```

### Step 8: Verify Both Environments
```bash
echo "=== PROD n8n ==="
curl -s https://n8n.leveredgeai.com/healthz || echo "PROD not responding"

echo "=== DEV n8n ==="
curl -s https://dev.n8n.leveredgeai.com/healthz || echo "DEV not responding"
```

### Step 9: Check ARIA Workflows
```bash
docker exec prod-n8n-postgres psql -U n8n -d n8n -c "SELECT id, name, active FROM workflow_entity WHERE name ILIKE '%aria%';"
docker exec dev-n8n-postgres psql -U n8n -d n8n_dev -c "SELECT id, name, active FROM workflow_entity WHERE name ILIKE '%aria%';"
```

## If Anything Fails - ROLLBACK
```bash
docker compose -f /opt/leveredge/data-plane/prod/n8n/docker-compose.yml down
docker compose -f /opt/leveredge/data-plane/dev/n8n/docker-compose.yml down

cd /home/damon/stack
docker compose up -d n8n n8n-dev n8n-postgres
```

## Success Criteria
- [ ] Other services (OpenProject, Leantime, etc.) UNAFFECTED
- [ ] prod-n8n healthy on 5678
- [ ] dev-n8n healthy on 5680
- [ ] ARIA workflows visible in both
