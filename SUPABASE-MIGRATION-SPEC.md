# SUPABASE MIGRATION SPEC

*Execute NOW - January 16, 2026*
*CHRONOS backup requested*

---

## Current State

```
/home/damon/stack/
├── supabase-db (postgres:15)
├── supabase-rest (postgrest)
├── supabase-meta (postgres-meta)
└── volumes with REAL DATA

/home/damon/environments/dev/supabase/
├── supabase-db-dev
├── supabase-rest-dev
├── supabase-meta-dev
└── dev data
```

## Target State

```
/opt/leveredge/data-plane/
├── prod/supabase/
│   ├── docker-compose.yml
│   ├── .env
│   └── volumes/ (symlink to existing data)
└── dev/supabase/
    ├── docker-compose.yml
    ├── .env
    └── volumes/
```

---

## Step 1: Inventory Current Supabase

```bash
# Find all supabase containers
docker ps | grep supabase

# Check volumes
docker volume ls | grep supabase

# Find compose files
find /home/damon -name "docker-compose.yml" -exec grep -l supabase {} \;
```

## Step 2: Create Directory Structure

```bash
mkdir -p /opt/leveredge/data-plane/prod/supabase
mkdir -p /opt/leveredge/data-plane/dev/supabase
```

## Step 3: Copy PROD Compose (Don't Stop Yet)

From /home/damon/stack/, extract supabase services into:
`/opt/leveredge/data-plane/prod/supabase/docker-compose.yml`

Key requirements:
- Keep same volume paths (or symlink)
- Keep same network (stack_net)
- Keep same container names initially
- Copy .env credentials

## Step 4: Copy DEV Compose

From /home/damon/environments/dev/supabase/, copy to:
`/opt/leveredge/data-plane/dev/supabase/docker-compose.yml`

## Step 5: Migrate PROD

```bash
# Stop old supabase (from /home/damon/stack)
cd /home/damon/stack
docker compose stop supabase-db supabase-rest supabase-meta

# Start new supabase (from /opt/leveredge)
cd /opt/leveredge/data-plane/prod/supabase
docker compose up -d

# Verify
curl http://localhost:3000/rest/v1/ -H "apikey: YOUR_KEY"
```

## Step 6: Migrate DEV

```bash
cd /home/damon/environments/dev/supabase
docker compose down

cd /opt/leveredge/data-plane/dev/supabase
docker compose up -d
```

## Step 7: Update References

Any hardcoded paths in:
- n8n credentials
- ARIA workflows
- Agent configs

Should use container names (supabase-db, supabase-rest) not paths.

## Step 8: Clean Up Old Location

After verification:
```bash
# Remove supabase from /home/damon/stack/docker-compose.yml
# Keep only caddy and any other non-migrated services
```

---

## CRITICAL: Data Preservation

PROD Supabase has:
- aria_conversations
- aria_wins
- aria_portfolio_summary
- n8n_chat_histories
- User data

**DO NOT delete volumes. Symlink or mount existing volumes.**

---

## Rollback

```bash
# Stop new
docker compose -f /opt/leveredge/data-plane/prod/supabase/docker-compose.yml down

# Restart old
cd /home/damon/stack
docker compose up -d supabase-db supabase-rest supabase-meta
```

---

## Verification

```bash
# PROD Supabase
curl -s http://localhost:3000/rest/v1/ -H "apikey: $SUPABASE_ANON_KEY" | head

# DEV Supabase  
curl -s http://localhost:3001/rest/v1/ -H "apikey: $SUPABASE_DEV_ANON_KEY" | head

# ARIA still works
curl -X POST https://n8n.leveredgeai.com/webhook/aria -d '{"message":"test"}'
```
