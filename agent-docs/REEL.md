# REEL

**Port:** 8033
**Category:** creative
**Status:** Defined

---

## Identity

**Name:** REEL
**Description:** Media Producer - Images, video, audio

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "reel",
  "port": 8033
}
```

---

## Actions

### generate-image
```
POST /generate/image
```
Generate AI image via DALL-E 3

### generate-video
```
POST /generate/video
```
Full video production pipeline

### generate-voiceover
```
POST /generate/voiceover
```
Generate voiceover via ElevenLabs

### source-stock
```
POST /source/stock
```
Find stock footage/photos


---

## Capabilities

- image_generation
- video_production
- voice_synthesis
- avatar_videos
- stock_sourcing

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `reel.action.completed`
- `reel.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name reel \
  --network leveredge-fleet-net \
  -p 8033:8033 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  reel:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d reel
```

---

*Generated: 2026-01-20 03:27*
