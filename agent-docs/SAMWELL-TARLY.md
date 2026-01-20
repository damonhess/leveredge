# LIBRARIAN

**Port:** 8201
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** LIBRARIAN
**Description:** Knowledge Manager - Document organization, search

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "samwell-tarly",
  "port": 8201
}
```

---

## Actions

### organize
```
POST /organize
```
Organize documents/knowledge

### search
```
POST /search
```
Search knowledge base


---

## Capabilities

- document_organization
- knowledge_management
- information_retrieval
- categorization

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `samwell-tarly.action.completed`
- `samwell-tarly.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name samwell-tarly \
  --network leveredge-fleet-net \
  -p 8201:8201 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  samwell-tarly:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d samwell-tarly
```

---

*Generated: 2026-01-20 03:27*
