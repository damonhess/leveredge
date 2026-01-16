# DATA PLANE MIGRATION SPEC

*Created: January 16, 2026*
*Status: EXECUTE TONIGHT*

---

## Current State

```
OLD PROD: /home/damon/stack/
├── n8n container (port 5678) - ARIA dated Jan 13
├── n8n-postgres container
└── supabase containers

OLD DEV: /home/damon/environments/dev/
├── n8n-dev container (same postgres, different DB)
├── ARIA dated Jan 14 (NEWER - SOURCE OF TRUTH)
└── supabase-dev containers
```

## Target State

```
/opt/leveredge/data-plane/
├── prod/
│   ├── n8n/           # port 5678
│   │   ├── docker-compose.yml
│   │   └── data/
│   └── supabase/      # existing supabase
│       └── (symlink or move)
└── dev/
    ├── n8n/           # port 5680
    │   ├── docker-compose.yml
    │   └── data/
    └── supabase/      # dev supabase
        └── (symlink or move)
```

## CRITICAL: Source of Truth

**DEV has newer ARIA (Jan 14).** 
**DO NOT overwrite DEV.**

Migration flow:
1. Keep existing containers running
2. Create new structure
3. Point to existing data volumes
4. Promote DEV ARIA → PROD after verified

---

## Step-by-Step Execution

### Step 1: Create Directory Structure
```bash
mkdir -p /opt/leveredge/data-plane/prod/n8n
mkdir -p /opt/leveredge/data-plane/prod/supabase
mkdir -p /opt/leveredge/data-plane/dev/n8n
mkdir -p /opt/leveredge/data-plane/dev/supabase
```

### Step 2: Symlink Existing Data (DON'T COPY)
```bash
# PROD n8n data
ln -s /home/damon/stack/n8n_data /opt/leveredge/data-plane/prod/n8n/data

# DEV uses same postgres with different database - handled by DB name
```

### Step 3: Create PROD docker-compose
```yaml
# /opt/leveredge/data-plane/prod/n8n/docker-compose.yml
version: '3.8'

services:
  prod-n8n-postgres:
    image: postgres:15-alpine
    container_name: prod-n8n-postgres
    environment:
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: n8n
    volumes:
      - /home/damon/stack/n8n_data/postgres:/var/lib/postgresql/data
    networks:
      - data-plane-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n -d n8n"]
      interval: 10s
      timeout: 5s
      retries: 5

  prod-n8n:
    image: n8nio/n8n:latest
    container_name: prod-n8n
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=prod-n8n-postgres
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_HOST=n8n.leveredgeai.com
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.leveredgeai.com
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
    volumes:
      - /home/damon/stack/n8n_data/n8n:/home/node/.n8n
    ports:
      - "5678:5678"
    networks:
      - data-plane-net
      - stack_net
    depends_on:
      prod-n8n-postgres:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  data-plane-net:
    driver: bridge
  stack_net:
    external: true
```

### Step 4: Create DEV docker-compose
```yaml
# /opt/leveredge/data-plane/dev/n8n/docker-compose.yml
version: '3.8'

services:
  dev-n8n-postgres:
    image: postgres:15-alpine
    container_name: dev-n8n-postgres
    environment:
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: n8n_dev
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - data-plane-dev-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n -d n8n_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  dev-n8n:
    image: n8nio/n8n:latest
    container_name: dev-n8n
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=dev-n8n-postgres
      - DB_POSTGRESDB_DATABASE=n8n_dev
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_HOST=dev.n8n.leveredgeai.com
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://dev.n8n.leveredgeai.com
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
    volumes:
      - ./data/n8n:/home/node/.n8n
    ports:
      - "5680:5678"
    networks:
      - data-plane-dev-net
      - stack_net
    depends_on:
      dev-n8n-postgres:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  data-plane-dev-net:
    driver: bridge
  stack_net:
    external: true
```

### Step 5: Environment Files
```bash
# /opt/leveredge/data-plane/prod/n8n/.env
POSTGRES_PASSWORD=<from existing>
N8N_ENCRYPTION_KEY=<from existing>

# /opt/leveredge/data-plane/dev/n8n/.env
POSTGRES_PASSWORD=<from existing>
N8N_ENCRYPTION_KEY=<from existing>
```

### Step 6: Stop Old Containers (Careful!)
```bash
# Stop old n8n (keep data!)
cd /home/damon/stack
docker compose stop n8n n8n-postgres

# Stop old dev n8n
docker stop n8n-dev
```

### Step 7: Start New Containers
```bash
# Start PROD
cd /opt/leveredge/data-plane/prod/n8n
docker compose up -d

# Start DEV
cd /opt/leveredge/data-plane/dev/n8n
docker compose up -d
```

### Step 8: Verify
```bash
# Check PROD ARIA
curl -s https://n8n.leveredgeai.com/webhook/aria-health || echo "Check PROD"

# Check DEV ARIA
curl -s https://dev.n8n.leveredgeai.com/webhook/aria-health || echo "Check DEV"
```

---

## ARIA Promotion (After Migration Verified)

Once both environments are running on new structure:

```bash
# Export ARIA workflows from DEV
n8n-troubleshooter export-workflow --id sNowLbJCOt4Pl6md --source dev > aria_web.json
n8n-troubleshooter export-workflow --id ARIARouter01v2v3 --source dev > aria_router.json
n8n-troubleshooter export-workflow --id ARIACostRpt01v2x --source dev > aria_cost.json

# Import to PROD
n8n-troubleshooter import-workflow --file aria_web.json --source prod
n8n-troubleshooter import-workflow --file aria_router.json --source prod
n8n-troubleshooter import-workflow --file aria_cost.json --source prod

# Activate in PROD
n8n-troubleshooter activate-workflow --id sNowLbJCOt4Pl6md --source prod
n8n-troubleshooter activate-workflow --id ARIARouter01v2v3 --source prod
n8n-troubleshooter activate-workflow --id ARIACostRpt01v2x --source prod
```

---

## Rollback Plan

If anything breaks:
```bash
# Stop new containers
docker compose down

# Restart old containers
cd /home/damon/stack
docker compose up -d n8n n8n-postgres

# Data is preserved (symlinks to original location)
```

---

## Success Criteria

- [ ] PROD n8n accessible at n8n.leveredgeai.com
- [ ] DEV n8n accessible at dev.n8n.leveredgeai.com
- [ ] ARIA workflows responding on both
- [ ] Old data preserved
- [ ] promote-to-prod.sh working
