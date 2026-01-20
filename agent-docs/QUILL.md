# QUILL

**Port:** 8031
**Category:** creative
**Status:** LLM-Powered

---

## Identity

**Name:** QUILL
**Description:** Elite Writer - Content, copy, scripts

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "quill",
  "port": 8031
}
```

---

## Actions

### write
```
POST /write
```
Generate content

### script-video
```
POST /script/video
```
Generate video script with scenes

### rewrite
```
POST /rewrite
```
Revise content based on feedback


---

## Capabilities

- long_form_content
- short_form_copy
- video_scripts
- technical_writing
- social_media

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `quill.action.completed`
- `quill.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name quill \
  --network leveredge-fleet-net \
  -p 8031:8031 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  quill:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d quill
```

---

*Generated: 2026-01-20 03:27*
