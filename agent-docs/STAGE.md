# STAGE

**Port:** 8032
**Category:** creative
**Status:** Defined

---

## Identity

**Name:** STAGE
**Description:** Designer - Presentations, charts, layouts, web/UI design

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "stage",
  "port": 8032
}
```

---

## Actions

### design-presentation
```
POST /design/presentation
```
Create branded presentation

### design-chart
```
POST /design/chart
```
Generate chart/graph

### design-thumbnail
```
POST /design/thumbnail
```
Create thumbnail in multiple sizes

### design-landing-page
```
POST /design/landing-page
```
Generate complete landing page with Tailwind CSS

### design-ui-component
```
POST /design/ui-component
```
Generate individual UI components with Tailwind CSS

### design-wireframe
```
POST /design/wireframe
```
Generate wireframe/mockup for page layout

### design-website-template
```
POST /design/website-template
```
Generate complete website template with multiple pages


---

## Capabilities

- presentation_design
- document_formatting
- chart_generation
- thumbnail_creation
- landing_page_design
- ui_component_design
- wireframe_generation
- website_template_design

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `stage.action.completed`
- `stage.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name stage \
  --network leveredge-fleet-net \
  -p 8032:8032 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  stage:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d stage
```

---

*Generated: 2026-01-20 03:27*
