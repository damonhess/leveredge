# ATLAS

**Port:** 8007
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** ATLAS
**Description:** Orchestration engine for complex chains and parallel batch execution

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "atlas",
  "port": 8007
}
```

---

## Actions

### execute
```
POST /execute
```
Execute a single chain or intent

### execute-parallel
```
POST /execute-parallel
```
Execute multiple chains in parallel with concurrency control

### batch-status
```
GET /batch/{batch_id}/status
```
Get progress of parallel batch execution

### batch-results
```
GET /batch/{batch_id}/results
```
Get full results of parallel batch execution

### list-chains
```
GET /chains
```
List available chains

### list-batches
```
GET /batches
```
List recent batch executions


---

## Capabilities

- chain_execution
- parallel_batch
- agent_coordination
- cost_tracking

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `atlas.action.completed`
- `atlas.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name atlas \
  --network leveredge-fleet-net \
  -p 8007:8007 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  atlas:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d atlas
```

---

*Generated: 2026-01-20 03:27*
