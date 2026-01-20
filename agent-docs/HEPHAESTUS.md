# HEPHAESTUS

**Port:** 8011
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** HEPHAESTUS
**Description:** File operations, commands, deployment, and orchestration

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "hephaestus",
  "port": 8011
}
```

---

## Actions

### read-file
```
GET /tools/file/read
```
Read file contents

### create-file
```
POST /tools/file/create
```
Create or update file

### list-directory
```
GET /tools/file/list
```
List directory contents

### run-command
```
POST /tools/command/run
```
Execute whitelisted command

### git-commit
```
POST /tools/git/commit
```
Git commit changes

### orchestrate-parallel
```
POST /tools/orchestrate/parallel
```
Execute multiple chains in parallel via ATLAS

### orchestrate-batch-status
```
GET /tools/orchestrate/batch/{batch_id}/status
```
Get status of parallel batch execution

### orchestrate-batch-results
```
GET /tools/orchestrate/batch/{batch_id}/results
```
Get full results of parallel batch execution


---

## Capabilities

- file_operations
- command_execution
- deployment
- git_operations
- parallel_orchestration

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `hephaestus.action.completed`
- `hephaestus.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name hephaestus \
  --network leveredge-fleet-net \
  -p 8011:8011 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  hephaestus:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d hephaestus
```

---

*Generated: 2026-01-20 03:27*
