# SUPABASE/POSTGRES STATUS & FIX PLAN

## CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ONE POSTGRES CONTAINER                           │
│                           (supabase-db)                                  │
│                       localhost:54322 exposed                            │
│                                                                          │
│   ┌─────────────────────────┐    ┌─────────────────────────┐           │
│   │   DATABASE: postgres    │    │  DATABASE: postgres_dev │           │
│   │        (PROD)           │    │        (DEV)            │           │
│   │                         │    │                         │           │
│   │  • aria_* tables        │    │  • aria_* tables        │           │
│   │  • REAL user data       │    │  • Test data only       │           │
│   └────────────┬────────────┘    └────────────┬────────────┘           │
│                │                              │                         │
│                ▼                              ▼                         │
│   ┌─────────────────────────┐    ┌─────────────────────────┐           │
│   │   PROD Supabase Stack   │    │   DEV Supabase Stack    │           │
│   │   (supabase-kong, etc)  │    │   (supabase-kong-dev)   │           │
│   └─────────────────────────┘    └─────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    HOST SERVICES                                         │
│                                                                          │
│   aria-threading (8113) ──────► 127.0.0.1:54322/postgres_dev            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## ISSUES TO FIX

### Issue 1: Shared Postgres Container ⚠️
**Risk:** Single point of failure - if supabase-db dies, both PROD and DEV go down.
**Severity:** Medium (acceptable for now, fix later)
**Fix:** Create separate postgres containers for PROD and DEV
**Priority:** Post-launch

### Issue 2: Missing Migration Files ❌
**Risk:** Can't recreate database, can't sync PROD/DEV schemas
**Severity:** High
**What's missing:**

| Schema | Has Migration File? | Applied Where? |
|--------|---------------------|----------------|
| aria_coaching_tables | ✅ 20260117 | DEV only? |
| aria_unified_threading | ✅ 20260118 | DEV only? |
| aria_async_tasks | ❌ NO FILE | DEV only |
| aria_unified_memory (elite) | ❌ NO FILE | DEV only |

**Fix:** Create migration files for all schemas, verify both DBs have them

### Issue 3: DEV/PROD Schema Sync ❌
**Risk:** PROD doesn't have the new tables
**Severity:** High (if we try to deploy ARIA to PROD)
**Current state:** All new tables only exist in postgres_dev

**Fix:** Run migrations against postgres (PROD database) 

### Issue 4: No Migration Tracking ❌
**Risk:** Don't know what's applied where
**Severity:** Medium
**Fix:** Create schema_migrations table or use Supabase migrations properly

---

## VERIFICATION QUERIES

Run these to understand current state:

### Check what tables exist in each database

```bash
# DEV database (postgres_dev)
docker exec supabase-db psql -U postgres -d postgres_dev -c "\dt aria_*"

# PROD database (postgres)
docker exec supabase-db psql -U postgres -d postgres -c "\dt aria_*"
```

### Check if pgvector extension exists

```bash
# DEV
docker exec supabase-db psql -U postgres -d postgres_dev -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

# PROD
docker exec supabase-db psql -U postgres -d postgres -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

---

## FIX PLAN

### Phase 1: Audit Current State (10 min)
1. Run verification queries above
2. Document exactly what tables exist where
3. Check pgvector extension status

### Phase 2: Create Missing Migration Files (30 min)
1. Export aria_async_tasks schema from DEV → create migration file
2. Export aria_unified_memory schema from DEV → create migration file
3. Store all in /opt/leveredge/data-plane/dev/supabase/migrations/

### Phase 3: Apply Migrations to PROD (30 min)
1. Backup PROD database first
2. Create pgvector extension in PROD if missing
3. Apply each migration file to postgres (PROD)
4. Verify tables exist

### Phase 4: Create Migration Tracking (15 min)
1. Create schema_migrations table in both DBs
2. Record what's been applied
3. Create simple migration runner script

### Phase 5: Document Process (15 min)
1. Update OPS-RUNBOOK.md with migration procedure
2. Create promote-schema.sh script for future

---

## IMMEDIATE ACTION

Run this to audit:

```bash
echo "=== DEV TABLES ===" && \
docker exec supabase-db psql -U postgres -d postgres_dev -c "\dt aria_*" && \
echo "" && \
echo "=== PROD TABLES ===" && \
docker exec supabase-db psql -U postgres -d postgres -c "\dt aria_*" && \
echo "" && \
echo "=== DEV PGVECTOR ===" && \
docker exec supabase-db psql -U postgres -d postgres_dev -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" && \
echo "" && \
echo "=== PROD PGVECTOR ===" && \
docker exec supabase-db psql -U postgres -d postgres -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

---

## DECISION NEEDED

**Option A: Fix Now (2 hours)**
- Create all migration files
- Sync PROD to match DEV schema
- Set up tracking
- Then continue with integration testing

**Option B: Fix After Integration Testing (defer)**
- Continue with integration testing on DEV only
- Fix migration issues before promoting to PROD
- Risk: PROD deployment delayed

**Recommendation:** Option A - Fix now. Clean foundation.
