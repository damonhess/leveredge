# DEPLOYMENT AGENT SPEC: APOLLO - God of Order and Prophecy

**Priority:** MEDIUM
**Status:** DEFERRED (post-launch)
**Purpose:** Automate and enforce deployment strategy

---

## PROBLEM

1. Specs can accidentally target PROD directly
2. No automated enforcement of dev-first workflow
3. Manual promotion is error-prone
4. No deployment history/audit trail

---

## SOLUTION: APOLLO

Deployment orchestrator that:
- Intercepts all deployment requests
- Enforces DEV → TEST → PROD pipeline
- Blocks direct-to-PROD deployments
- Maintains deployment history
- Integrates with CHRONOS (backup) and HADES (rollback)

---

## CAPABILITIES

### 1. Pipeline Enforcement
```
DEV → Smoke Tests → STAGING (optional) → PROD
```

No skipping stages without explicit override + reason.

### 2. Pre-Deployment Checks
- CHRONOS backup exists
- All tests pass
- No uncommitted changes
- Schema migrations applied
- Health checks pass

### 3. Deployment Strategies
- **Blue-Green:** Zero-downtime swaps
- **Canary:** Gradual rollout with metrics
- **Rolling:** Container-by-container updates
- **Immediate:** For hotfixes (requires override)

### 4. Rollback Integration
- Automatic rollback on failed health checks
- One-click rollback via HADES
- Deployment history for any-version rollback

### 5. Audit Trail
```sql
CREATE TABLE deployment_history (
  id UUID PRIMARY KEY,
  service TEXT NOT NULL,
  from_version TEXT,
  to_version TEXT,
  environment TEXT NOT NULL,
  strategy TEXT NOT NULL,
  deployed_by TEXT NOT NULL,
  deployed_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT NOT NULL,
  rollback_version TEXT,
  notes TEXT
);
```

---

## ENDPOINTS

| Endpoint | Purpose |
|----------|---------|
| `POST /deploy` | Request deployment (goes through pipeline) |
| `POST /promote` | Promote from one env to next |
| `POST /rollback` | Rollback to previous version |
| `GET /status/{service}` | Current deployment status |
| `GET /history/{service}` | Deployment history |
| `POST /hotfix` | Emergency direct-to-prod (requires reason) |

---

## INTEGRATION

- **CHRONOS:** Backup before every deployment
- **HADES:** Rollback on failure
- **PANOPTES:** Health checks post-deployment
- **HERMES:** Notifications on deploy/rollback
- **LCIS:** Log deployment lessons

---

## CLI USAGE

```bash
# Deploy to DEV (default)
apollo deploy aria-frontend

# Promote DEV → PROD (runs full pipeline)
apollo promote aria-frontend

# Emergency hotfix (requires reason)
apollo hotfix aria-frontend --reason "Critical auth bug"

# Rollback
apollo rollback aria-frontend --to=v1.2.3
```

---

## WHY APOLLO?

In Greek mythology, Apollo brought order, prophecy (foresight), and healing. He:
- Brings **order** to chaotic deployments
- Provides **foresight** via pre-deployment checks
- Enables **healing** via automatic rollback

---

*Build after March 1 launch. For now, enforce dev-first manually and use promote-aria-to-prod.sh.*
