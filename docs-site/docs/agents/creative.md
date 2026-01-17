# Creative Fleet

The Creative Fleet provides automated content production across presentations, documents, images, video, and social media.

## Fleet Overview

| Agent | Port | Purpose | Type |
|-------|------|---------|------|
| MUSE | 8030 | Creative Director (coordinator) | FastAPI |
| CALLIOPE | 8031 | Writer (content, copy, scripts) | FastAPI (LLM) |
| THALIA | 8032 | Designer (presentations, layouts) | FastAPI |
| ERATO | 8033 | Media Producer (images, video, audio) | FastAPI |
| CLIO | 8034 | Reviewer (QA, brand compliance) | FastAPI (LLM) |

## Architecture

```
                    +---------------------+
                    |       MUSE          |
                    |   Creative Director |
                    |    (Coordinator)    |
                    +----------+----------+
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
+-------------+        +-------------+        +-------------+
|   CALLIOPE  |        |   THALIA    |        |   ERATO     |
|   Writer    |        |   Designer  |        |   Media     |
|  (Content)  |        |  (Visual)   |        |  (A/V)      |
+-------------+        +-------------+        +-------------+
       |                       |                       |
       |               +-------+-------+               |
       |               |               |               |
       v               v               v               v
+-------------+  +----------+  +----------+  +-------------+
|   CLIO      |  |  Brand   |  |  Asset   |  |   Video     |
|  Reviewer   |  | Library  |  | Storage  |  |  Pipeline   |
|   (QA)      |  +----------+  +----------+  +-------------+
+-------------+
```

---

## MUSE - Creative Director

**Port:** 8030 | **Type:** Coordinator

MUSE orchestrates creative projects, decomposes tasks, and coordinates specialist agents.

### Capabilities

- Parse creative briefs into structured tasks
- Route tasks to appropriate specialists
- Manage multi-step workflows
- Aggregate outputs into final deliverables
- Track project status and dependencies
- Create storyboards for video projects

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/projects/create` | POST | Create new creative project |
| `/projects/{id}` | GET | Get project status |
| `/projects/{id}/approve` | POST | Approve stage output |
| `/projects/{id}/output` | GET | Get final deliverables |
| `/storyboard` | POST | Create video storyboard |
| `/fleet` | GET | List creative fleet capabilities |

### Project Types

| Type | Output | Typical Time | Estimated Cost |
|------|--------|--------------|----------------|
| `presentation` | .pptx | 5 min | ~$0.50 |
| `document` | .docx, .pdf | 3 min | ~$0.10 |
| `image` | .png, .jpg | 30 sec | ~$0.08 |
| `video` | .mp4 | 8 min | ~$0.80 |
| `social` | text + image | 2 min | ~$0.15 |

### Example Usage

```bash
# Create presentation project
curl -X POST http://localhost:8030/projects/create \
  -H "Content-Type: application/json" \
  -d '{
    "type": "presentation",
    "brief": "Create a 10-slide pitch deck for compliance automation demo",
    "brand_id": "leveredge",
    "priority": "high"
  }'

# Create video project
curl -X POST http://localhost:8030/projects/create \
  -H "Content-Type: application/json" \
  -d '{
    "type": "video",
    "brief": "Create a 90-second explainer video for compliance automation",
    "video_options": {
      "duration_target": 90,
      "style": "avatar",
      "voice_id": "elevenlabs_rachel"
    }
  }'
```

---

## CALLIOPE - Writer

**Port:** 8031 | **Type:** LLM-Powered

CALLIOPE handles all content creation, copywriting, and script generation.

### Capabilities

- Long-form content (reports, articles, case studies)
- Short-form copy (headlines, taglines, CTAs)
- Presentation content (slide text, speaker notes)
- Video scripts (narration, dialogue, captions)
- Technical writing (docs, specs, guides)
- Social media copy (platform-optimized)

### Writing Styles

| Style | Description |
|-------|-------------|
| `professional` | Clear, authoritative, data-driven |
| `conversational` | Friendly, approachable, relatable |
| `technical` | Precise, detailed, accurate |
| `persuasive` | Compelling, benefit-focused, action-oriented |
| `educational` | Explanatory, step-by-step, accessible |
| `energetic` | Dynamic, exciting, fast-paced |

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/write` | POST | Generate content |
| `/rewrite` | POST | Revise content with feedback |
| `/expand` | POST | Expand bullet points |
| `/script/video` | POST | Generate video script with scenes |

### Example Usage

```bash
# Generate video script
curl -X POST http://localhost:8031/script/video \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Compliance automation benefits",
    "duration_target": 90,
    "style": "professional",
    "include_captions": true
  }'
```

---

## THALIA - Designer

**Port:** 8032 | **Type:** Executor

THALIA handles visual design, presentations, and layouts.

### Capabilities

- Presentation design (slides, templates)
- Document formatting (headers, layouts)
- Chart/graph creation
- Brand template application
- Layout optimization
- Thumbnail design
- Landing page design (Tailwind CSS)
- UI component generation
- Wireframe creation

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/design/presentation` | POST | Create branded presentation |
| `/design/document` | POST | Format document |
| `/design/chart` | POST | Generate chart/graph |
| `/design/thumbnail` | POST | Create thumbnail |
| `/design/landing-page` | POST | Generate landing page HTML |
| `/design/ui-component` | POST | Generate UI component |
| `/design/wireframe` | POST | Generate wireframe mockup |

### Design System

```yaml
color_palettes:
  leveredge:
    primary: "#1B2951"      # Deep storm blue
    secondary: "#B8860B"    # Golden bronze
    accent: "#36454F"       # Charcoal grey
    background: "#FFFFFF"
    text: "#1A1A1A"

typography:
  headings: "Inter, sans-serif"
  body: "Inter, sans-serif"
  code: "JetBrains Mono, monospace"
```

### Example Usage

```bash
# Create presentation
curl -X POST http://localhost:8032/design/presentation \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "slides": [
        {"title": "Introduction", "bullets": ["Point 1", "Point 2"]},
        {"title": "Benefits", "bullets": ["Benefit 1", "Benefit 2"]}
      ]
    },
    "brand_id": "leveredge",
    "style": "corporate"
  }'
```

---

## ERATO - Media Producer

**Port:** 8033 | **Type:** Executor

ERATO handles image generation, video production, and audio synthesis.

### Capabilities

- AI image generation (DALL-E 3)
- Image post-processing
- Video assembly and editing
- Avatar video generation (Synthesia, HeyGen)
- Voice generation (ElevenLabs)
- Audio processing
- Stock footage sourcing (Pexels, Pixabay)

### Video Styles

| Style | Description | Cost |
|-------|-------------|------|
| `avatar` | AI presenter delivers script on camera | $0.50-1.00/min |
| `motion_graphics` | Animated text, shapes, and graphics | $0.10/min |
| `slideshow` | Images with transitions and narration | $0.05/min |
| `stock_footage` | Licensed stock video with voiceover | $0 + voice |

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/generate/image` | POST | Generate AI image |
| `/generate/video` | POST | Full video production |
| `/generate/avatar` | POST | Generate avatar presenter |
| `/generate/voiceover` | POST | Generate voiceover |
| `/assemble/video` | POST | Assemble video timeline |
| `/process/image` | POST | Post-process image |
| `/source/stock` | POST | Find stock assets |

### Example Usage

```bash
# Generate AI image
curl -X POST http://localhost:8033/generate/image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Modern flat illustration of compliance workflow automation",
    "style": "illustration",
    "size": "1792x1024"
  }'

# Generate avatar video
curl -X POST http://localhost:8033/generate/avatar \
  -H "Content-Type: application/json" \
  -d '{
    "script": "Welcome to our compliance automation platform...",
    "avatar_id": "synthesia_anna",
    "provider": "synthesia",
    "background": "office"
  }'
```

---

## CLIO - Reviewer

**Port:** 8034 | **Type:** LLM-Powered

CLIO handles quality assurance, brand compliance, and fact-checking.

### Capabilities

- Brand guideline compliance
- Grammar/spelling check
- Fact verification (via SCHOLAR)
- Consistency review
- Accessibility check
- Video quality review
- Audio quality check

### Review Checklists

=== "Presentation"
    - Consistent font usage
    - Brand colors only
    - Logo placement correct
    - No orphan bullet points
    - Speaker notes present
    - Slide count appropriate

=== "Document"
    - Header hierarchy correct
    - Consistent formatting
    - Citations present (if claims made)
    - No passive voice overuse
    - Reading level appropriate

=== "Video"
    - Audio levels consistent (-14 to -10 LUFS)
    - No background noise/hum
    - Captions present and accurate
    - Intro/outro present
    - Brand watermark visible
    - Duration within target +/-10%

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/review` | POST | Review any content type |
| `/review/brand` | POST | Brand compliance check |
| `/review/video` | POST | Review video quality |
| `/review/text` | POST | Grammar/tone review |
| `/fact-check` | POST | Verify facts via SCHOLAR |

### Example Usage

```bash
# Review content
curl -X POST http://localhost:8034/review \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "presentation",
    "content_path": "/opt/leveredge/creative/output/deck.pptx",
    "brand_id": "leveredge",
    "check_types": ["brand", "grammar", "accessibility"]
  }'
```

---

## Workflow Examples

### Client Pitch Deck

```
Request: "Create a 10-slide pitch deck for compliance demo"

Flow:
1. MUSE: Analyze brief, create outline
2. CALLIOPE: Write slide content, speaker notes
3. THALIA: Apply design, create visuals
4. ERATO: Generate custom graphics
5. CLIO: Review for brand, accuracy, flow

Output: Final .pptx file
Time: ~5 minutes
Cost: ~$0.50
```

### 90-Second Explainer Video

```
Request: "Create 90-second explainer video"

Flow:
1. MUSE: Create storyboard (6 scenes)
2. CALLIOPE: Write 200-word script
3. ERATO: Generate voiceover (ElevenLabs)
4. ERATO: Generate avatar presenter (Synthesia)
5. ERATO: Source B-roll footage (Pexels)
6. ERATO: Assemble video (FFmpeg)
7. CLIO: Review final cut

Output: .mp4 + thumbnail
Time: ~8 minutes
Cost: ~$0.81
```

---

## Cost Estimates

| Operation | Cost | Notes |
|-----------|------|-------|
| 10-slide presentation | ~$0.50 | Text + charts |
| Presentation + custom graphics | ~$1.50 | Add DALL-E images |
| Document (2000 words) | ~$0.10 | Text only |
| Social post + image | ~$0.15 | Short text + 1 image |
| 60-second video (avatar) | ~$0.80 | Voice + avatar |
| 60-second video (motion) | ~$0.20 | Voice + graphics |
| 60-second video (stock) | ~$0.10 | Voice + free footage |
