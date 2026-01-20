# CREATIVE FLEET - Complete Content Production System

## OVERVIEW

A multi-agent creative production system for automated content generation across presentations, documents, images, video, and social media. Uses coordinator-worker pattern with specialized agents for each content type.

**Primary Use Cases:**
1. Client deliverables (proposals, reports, case studies)
2. Marketing content (social posts, blog articles, landing pages)
3. Internal documentation (specs, guides, SOPs)
4. Sales materials (pitch decks, one-pagers, demos)
5. Video content (explainers, demos, social clips)

**Architecture Pattern:** Coordinator → Specialist Workers

---

## RESEARCH FINDINGS (Applied)

| Finding | Application |
|---------|-------------|
| $4.79B AI presentation market by 2029 | Focus on presentation automation |
| 80% reduction in manual slide prep | Measurable ROI for clients |
| 5-agent content teams pattern | Research, Content, Design, Review, Publish |
| 60-70% AI + human refinement | Human-in-loop for brand consistency |
| Coordinator-worker model | MUSE coordinates specialist agents |
| Synthesia enterprise avatars | Video production capability |
| 1.3-1.6x real-time render | Fast video turnaround |

---

## ARCHITECTURE

```
                    ┌─────────────────────┐
                    │       MUSE          │
                    │   Creative Director │
                    │    (Coordinator)    │
                    └──────────┬──────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   CALLIOPE  │        │   THALIA    │        │   ERATO     │
│   Writer    │        │   Designer  │        │   Media     │
│  (Content)  │        │  (Visual)   │        │  (A/V)      │
└─────────────┘        └─────────────┘        └─────────────┘
       │                       │                       │
       │               ┌───────┴───────┐               │
       │               │               │               │
       ▼               ▼               ▼               ▼
┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐
│   CLIO      │  │  Brand   │  │  Asset   │  │   Video     │
│  Reviewer   │  │ Library  │  │ Storage  │  │  Pipeline   │
│   (QA)      │  │          │  │          │  │             │
└─────────────┘  └──────────┘  └──────────┘  └─────────────┘
```

**Agent Names (Greek Muses):**
- **MUSE** - Creative Director (coordinator, task decomposition) - Port 8030
- **CALLIOPE** - Writer (copy, docs, scripts) - Port 8031
- **THALIA** - Designer (presentations, graphics, layouts) - Port 8032
- **ERATO** - Media Producer (images, video, audio) - Port 8033
- **CLIO** - Reviewer (QA, brand compliance, fact-check) - Port 8034

---

## CONTENT TYPES & WORKFLOWS

### 1. PRESENTATIONS

**Input:** Brief, topic, audience, brand guidelines
**Output:** .pptx file ready for delivery

**Workflow:**
```
User Request
    │
    ▼
MUSE: Analyze brief, create outline
    │
    ▼
CALLIOPE: Write slide content, speaker notes
    │
    ▼
THALIA: Apply design, create visuals
    │
    ▼
ERATO: Generate custom graphics/charts
    │
    ▼
CLIO: Review for brand, accuracy, flow
    │
    ▼
Output: Final .pptx
```

**Tools Used:**
- python-pptx for generation
- DALL-E 3 for custom graphics
- Chart.js for data visualization
- Brand template library

---

### 2. DOCUMENTS

**Types:** Proposals, reports, case studies, SOPs, specs
**Output:** .docx, .pdf, .md

**Workflow:**
```
User Request
    │
    ▼
MUSE: Analyze requirements, structure outline
    │
    ▼
SCHOLAR: Research (if needed)
    │
    ▼
CALLIOPE: Write content sections
    │
    ▼
THALIA: Format, add headers/visuals
    │
    ▼
CLIO: Review, fact-check, polish
    │
    ▼
Output: Final document
```

**Tools Used:**
- python-docx for Word docs
- WeasyPrint/ReportLab for PDFs
- Markdown for specs/docs

---

### 3. IMAGES

**Types:** Social graphics, diagrams, illustrations, thumbnails
**Output:** .png, .svg, .jpg

**Workflow:**
```
User Request
    │
    ▼
MUSE: Interpret creative brief
    │
    ▼
ERATO: Generate via AI (DALL-E 3)
    │
    ├── Option A: Accept
    │
    ├── Option B: Iterate with feedback
    │
    └── Option C: Manual edit needed
    │
    ▼
CLIO: Brand compliance check
    │
    ▼
Output: Final image(s)
```

**Tools Used:**
- DALL-E 3 API (primary)
- Pillow for post-processing
- SVG generation for diagrams

---

### 4. VIDEO

**Types:** Explainers, demos, social clips, tutorials, testimonials
**Output:** .mp4, .webm

**Workflow:**
```
User Request
    │
    ▼
MUSE: Create video brief, script outline, storyboard
    │
    ▼
CALLIOPE: Write script, voiceover text, captions
    │
    ▼
ERATO: Generate visuals, b-roll, animations
    │
    ▼
ERATO: Text-to-speech (ElevenLabs) or Avatar (Synthesia)
    │
    ▼
ERATO: Assemble timeline, add music, transitions
    │
    ▼
CLIO: Review final cut, brand compliance
    │
    ▼
Output: Final video + thumbnail
```

**Tools Used:**
- Synthesia API (avatar videos)
- HeyGen API (alternative avatars)
- ElevenLabs (voice generation)
- FFmpeg (video processing, assembly)
- MoviePy (Python video editing)
- Pexels/Pixabay API (stock footage)

**Video Types Supported:**

| Type | Duration | Avatar | Use Case |
|------|----------|--------|----------|
| Explainer | 60-180s | Yes | Product demos, how-tos |
| Social Clip | 15-60s | Optional | LinkedIn, Twitter, Instagram |
| Tutorial | 3-10min | Yes | Training, onboarding |
| Testimonial | 30-90s | No (stock) | Social proof |
| Promo | 30-60s | Optional | Ads, announcements |

---

### 5. SOCIAL CONTENT

**Types:** LinkedIn posts, Twitter threads, image + caption combos
**Output:** Text + image packages

**Workflow:**
```
User Request (topic, platform, tone)
    │
    ▼
MUSE: Platform strategy, content angle
    │
    ▼
CALLIOPE: Write copy (platform-optimized)
    │
    ▼
ERATO: Generate accompanying image
    │
    ▼
CLIO: Review for platform best practices
    │
    ▼
Output: Ready-to-post content package
```

**Platform-Specific Guidelines:**

| Platform | Max Length | Image Size | Best Practices |
|----------|------------|------------|----------------|
| LinkedIn | 3000 chars | 1200x627 | Professional tone, 3-5 hashtags |
| Twitter/X | 280 chars | 1600x900 | Punchy, threads for long content |
| Instagram | 2200 chars | 1080x1080 | Visual-first, 20-30 hashtags |

---

## AGENT SPECIFICATIONS

### MUSE - Creative Director (Port 8030)

**Role:** Coordinator, task decomposition, quality orchestration

**Capabilities:**
- Parse creative briefs into structured tasks
- Route tasks to appropriate specialists
- Manage multi-step workflows
- Aggregate outputs into final deliverables
- Track project status and dependencies
- Create storyboards for video projects

**Endpoints:**
```yaml
POST /projects/create
body: {
  type: "presentation" | "document" | "image" | "video" | "social",
  brief: string,
  brand_id?: string,
  deadline?: datetime,
  priority?: "low" | "medium" | "high",
  video_options?: {
    duration_target: int,
    style: "avatar" | "motion" | "slideshow",
    voice_id?: string,
    avatar_id?: string
  }
}
response: { project_id, status, estimated_time, task_breakdown }

GET /projects/{id}
response: { project, tasks[], current_stage, progress_pct }

POST /projects/{id}/approve
body: { stage: string, approved: boolean, feedback?: string }

GET /projects/{id}/output
response: { files[], preview_urls[] }

POST /projects/{id}/cancel
response: { status: "cancelled", refund_estimate }
```

**Task Decomposition Example (Video):**
```json
{
  "request": "Create a 90-second explainer video for compliance automation",
  "decomposition": {
    "brief_analysis": {
      "agent": "MUSE",
      "task": "Analyze brief, create storyboard"
    },
    "script": {
      "agent": "CALLIOPE",
      "task": "Write video script and captions",
      "depends_on": ["brief_analysis"]
    },
    "voiceover": {
      "agent": "ERATO",
      "task": "Generate voiceover via ElevenLabs",
      "depends_on": ["script"]
    },
    "visuals": {
      "agent": "ERATO",
      "task": "Generate/source visuals for each scene",
      "depends_on": ["brief_analysis"]
    },
    "avatar": {
      "agent": "ERATO",
      "task": "Generate avatar presenter via Synthesia",
      "depends_on": ["script"]
    },
    "assembly": {
      "agent": "ERATO",
      "task": "Assemble video timeline with FFmpeg",
      "depends_on": ["voiceover", "visuals", "avatar"]
    },
    "review": {
      "agent": "CLIO",
      "task": "Review final video for brand/quality",
      "depends_on": ["assembly"]
    }
  }
}
```

---

### CALLIOPE - Writer (Port 8031)

**Role:** Content creation, copywriting, scripts

**Capabilities:**
- Long-form content (reports, articles, case studies)
- Short-form copy (headlines, taglines, CTAs)
- Presentation content (slide text, speaker notes)
- Video scripts (narration, dialogue, captions)
- Technical writing (docs, specs, guides)
- Social media copy (platform-optimized)

**Endpoints:**
```yaml
POST /write
body: {
  type: "slides" | "document" | "copy" | "script" | "social" | "video_script",
  brief: string,
  tone?: string,
  length?: "short" | "medium" | "long",
  outline?: string[],
  context?: object,
  platform?: "linkedin" | "twitter" | "instagram"
}
response: { content, word_count, sections[], estimated_duration? }

POST /rewrite
body: {
  original: string,
  feedback: string,
  preserve?: string[]
}
response: { revised_content, changes_made[] }

POST /expand
body: {
  bullet_points: string[],
  target_length: int
}
response: { expanded_content }

POST /script/video
body: {
  topic: string,
  duration_target: int,  # seconds
  style: "conversational" | "professional" | "energetic",
  include_captions: boolean
}
response: {
  script: string,
  scenes: [
    { scene_num, duration, narration, visual_direction, on_screen_text }
  ],
  total_duration: int,
  word_count: int
}
```

**Writing Styles:**
```yaml
professional: "Clear, authoritative, data-driven"
conversational: "Friendly, approachable, relatable"
technical: "Precise, detailed, accurate"
persuasive: "Compelling, benefit-focused, action-oriented"
educational: "Explanatory, step-by-step, accessible"
energetic: "Dynamic, exciting, fast-paced"
```

---

### THALIA - Designer (Port 8032)

**Role:** Visual design, layouts, presentations

**Capabilities:**
- Presentation design (slides, templates)
- Document formatting (headers, layouts)
- Chart/graph creation
- Brand template application
- Layout optimization
- Thumbnail design

**Endpoints:**
```yaml
POST /design/presentation
body: {
  content: { slides: [...] },
  brand_id?: string,
  template?: string,
  style?: "minimal" | "corporate" | "creative" | "data-heavy"
}
response: { file_path, preview_url, slide_count }

POST /design/document
body: {
  content: string,
  format: "docx" | "pdf",
  brand_id?: string,
  template?: string
}
response: { file_path, preview_url }

POST /design/chart
body: {
  type: "bar" | "line" | "pie" | "area" | "scatter" | "gauge",
  data: object,
  style?: object,
  animated?: boolean
}
response: { image_path, svg_path, animation_path? }

POST /design/thumbnail
body: {
  title: string,
  style: "youtube" | "social" | "blog",
  brand_id?: string,
  background_image?: string
}
response: { image_path, sizes: { small, medium, large } }
```

**Design System:**
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

spacing:
  slide_margin: "0.75in"
  content_gap: "24px"
```

---

### ERATO - Media Producer (Port 8033)

**Role:** Image generation, video production, audio

**Capabilities:**
- AI image generation (DALL-E 3)
- Image post-processing
- Video assembly and editing
- Avatar video generation (Synthesia, HeyGen)
- Voice generation (ElevenLabs)
- Audio processing
- Thumbnail creation
- Stock footage sourcing

**Endpoints:**
```yaml
# IMAGE GENERATION
POST /generate/image
body: {
  prompt: string,
  style?: string,
  size?: "1024x1024" | "1792x1024" | "1024x1792",
  n?: int,
  brand_colors?: string[]
}
response: { images[], generation_id }

POST /process/image
body: {
  image_path: string,
  operations: ["resize", "crop", "overlay", "filter", "watermark"][]
}
response: { processed_path }

# VIDEO GENERATION
POST /generate/video
body: {
  script: string,
  style: "avatar" | "motion_graphics" | "slideshow" | "stock_footage",
  duration_target?: int,
  voice_config?: {
    provider: "elevenlabs" | "synthesia",
    voice_id: string,
    speed?: float
  },
  avatar_config?: {
    provider: "synthesia" | "heygen",
    avatar_id: string,
    background?: string
  },
  music?: {
    style: "corporate" | "upbeat" | "calm" | "none",
    volume: float
  }
}
response: { 
  video_path, 
  thumbnail_path, 
  duration, 
  render_time,
  cost_breakdown: { voice, avatar, storage }
}

POST /generate/avatar
body: {
  script: string,
  avatar_id: string,
  provider: "synthesia" | "heygen",
  background?: "office" | "studio" | "custom",
  custom_background_url?: string
}
response: { video_path, duration, render_time }

POST /generate/voiceover
body: {
  text: string,
  voice_id: string,
  provider: "elevenlabs",
  speed?: float,
  pitch?: float
}
response: { audio_path, duration, characters_used }

POST /assemble/video
body: {
  scenes: [
    {
      type: "avatar" | "image" | "video" | "text",
      content_path: string,
      duration: float,
      transition?: "fade" | "cut" | "slide",
      audio_path?: string,
      text_overlay?: string
    }
  ],
  output_format: "mp4" | "webm",
  resolution: "1080p" | "720p" | "4k",
  background_music?: string
}
response: { video_path, duration, file_size }

POST /source/stock
body: {
  query: string,
  type: "video" | "image",
  count: int,
  orientation?: "landscape" | "portrait" | "square"
}
response: { assets[], source: "pexels" | "pixabay" }
```

**Image Generation Prompts (Optimized):**
```yaml
diagram:
  prefix: "Clean, minimal technical diagram showing"
  suffix: ", white background, no text, vector style"

illustration:
  prefix: "Modern flat illustration of"
  suffix: ", vibrant colors, professional, suitable for business presentation"

icon:
  prefix: "Simple, flat icon representing"
  suffix: ", single color, minimal detail, suitable for UI"

hero_image:
  prefix: "Professional photograph of"
  suffix: ", high quality, business context, shallow depth of field"

video_scene:
  prefix: "Cinematic still frame showing"
  suffix: ", 16:9 aspect ratio, professional lighting, suitable for corporate video"
```

**Video Styles:**
```yaml
avatar:
  description: "AI presenter delivers script on camera"
  providers: ["synthesia", "heygen"]
  best_for: "Explainers, tutorials, announcements"
  cost: "$0.50-1.00 per minute"

motion_graphics:
  description: "Animated text, shapes, and graphics"
  tools: ["remotion", "ffmpeg"]
  best_for: "Social clips, ads, intros"
  cost: "$0.10 per minute"

slideshow:
  description: "Images with transitions and narration"
  tools: ["ffmpeg", "moviepy"]
  best_for: "Quick content, photo stories"
  cost: "$0.05 per minute"

stock_footage:
  description: "Licensed stock video with voiceover"
  sources: ["pexels", "pixabay"]
  best_for: "B-roll, testimonials, mood pieces"
  cost: "$0 + voice cost"
```

---

### CLIO - Reviewer (Port 8034)

**Role:** Quality assurance, brand compliance, fact-checking

**Capabilities:**
- Brand guideline compliance
- Grammar/spelling check
- Fact verification (via SCHOLAR)
- Consistency review
- Accessibility check
- Video quality review
- Audio quality check

**Endpoints:**
```yaml
POST /review
body: {
  content_type: "presentation" | "document" | "image" | "video" | "copy",
  content_path: string,
  brand_id?: string,
  check_types?: ["brand", "grammar", "facts", "accessibility", "quality"][]
}
response: {
  passed: boolean,
  score: int,
  issues: [
    { type, severity, location, description, suggestion, timestamp? }
  ]
}

POST /review/brand
body: {
  content_path: string,
  brand_id: string
}
response: {
  compliant: boolean,
  violations: [
    { rule, location, expected, actual }
  ]
}

POST /review/video
body: {
  video_path: string,
  brand_id?: string,
  checks: ["audio_quality", "visual_quality", "brand", "captions", "duration"][]
}
response: {
  passed: boolean,
  scores: {
    audio_quality: int,
    visual_quality: int,
    brand_compliance: int,
    caption_accuracy: int
  },
  issues: [
    { timestamp, type, description, suggestion }
  ]
}
```

**Review Checklists:**

```yaml
presentation:
  - Consistent font usage
  - Brand colors only
  - Logo placement correct
  - No orphan bullet points
  - Speaker notes present
  - Slide count appropriate

document:
  - Header hierarchy correct
  - Consistent formatting
  - Citations present (if claims made)
  - No passive voice overuse
  - Reading level appropriate

image:
  - Resolution sufficient
  - Brand colors present
  - No text cut off
  - Accessible contrast ratio

video:
  - Audio levels consistent (-14 to -10 LUFS)
  - No background noise/hum
  - Captions present and accurate
  - Intro/outro present
  - Brand watermark visible
  - Duration within target ±10%
  - Resolution matches spec
  - No visual artifacts
  - Transitions smooth
  - Music doesn't overpower voice
```

---

## BRAND LIBRARY

### Brand Profile Schema

```sql
CREATE TABLE creative_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    
    -- Colors
    color_primary TEXT,
    color_secondary TEXT,
    color_accent TEXT,
    color_background TEXT,
    color_text TEXT,
    
    -- Typography
    font_headings TEXT,
    font_body TEXT,
    font_code TEXT,
    
    -- Assets
    logo_path TEXT,
    logo_dark_path TEXT,
    icon_path TEXT,
    watermark_path TEXT,
    
    -- Voice
    tone TEXT,
    voice_description TEXT,
    
    -- Video Settings
    intro_video_path TEXT,
    outro_video_path TEXT,
    default_avatar_id TEXT,
    default_voice_id TEXT,
    background_music_path TEXT,
    
    -- Templates
    pptx_template_path TEXT,
    docx_template_path TEXT,
    video_template_path TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE creative_brand_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES creative_brands(id),
    asset_type TEXT NOT NULL,
    asset_path TEXT NOT NULL,
    usage_context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE creative_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES creative_brands(id),
    name TEXT NOT NULL,
    provider TEXT NOT NULL,  -- elevenlabs, synthesia
    voice_id TEXT NOT NULL,
    description TEXT,
    sample_url TEXT,
    is_default BOOLEAN DEFAULT FALSE
);

CREATE TABLE creative_avatars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES creative_brands(id),
    name TEXT NOT NULL,
    provider TEXT NOT NULL,  -- synthesia, heygen
    avatar_id TEXT NOT NULL,
    description TEXT,
    preview_url TEXT,
    is_default BOOLEAN DEFAULT FALSE
);
```

### Default Brand (LeverEdge)

```yaml
name: "LeverEdge AI"
colors:
  primary: "#1B2951"
  secondary: "#B8860B"
  accent: "#36454F"
  background: "#FFFFFF"
  text: "#1A1A1A"
  
typography:
  headings: "Inter"
  body: "Inter"
  code: "JetBrains Mono"

tone: "professional"
voice: "Confident, knowledgeable, direct but approachable. 
        Technical depth without jargon. Results-focused."

video:
  default_voice: "elevenlabs_rachel"
  default_avatar: "synthesia_anna"
  intro_duration: 3s
  outro_duration: 5s
  watermark_position: "bottom_right"

templates:
  pptx: "/opt/leveredge/creative/templates/leveredge-deck.pptx"
  docx: "/opt/leveredge/creative/templates/leveredge-doc.docx"
  video: "/opt/leveredge/creative/templates/leveredge-video.json"
```

---

## DATABASE SCHEMA

```sql
-- Projects
CREATE TABLE creative_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    title TEXT,
    brief TEXT NOT NULL,
    brand_id UUID REFERENCES creative_brands(id),
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    requested_by TEXT,
    deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    output_paths JSONB DEFAULT '[]',
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    video_config JSONB  -- For video projects
);

-- Tasks
CREATE TABLE creative_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    task_type TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    depends_on UUID[],
    input_data JSONB,
    output_data JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    cost_usd DECIMAL(10,4) DEFAULT 0
);

-- Generated assets
CREATE TABLE creative_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id),
    task_id UUID REFERENCES creative_tasks(id),
    asset_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INT,
    mime_type TEXT,
    metadata JSONB,
    duration_seconds FLOAT,  -- For video/audio
    version INT DEFAULT 1,
    is_final BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generation history
CREATE TABLE creative_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES creative_tasks(id),
    agent TEXT NOT NULL,
    generation_type TEXT NOT NULL,  -- image, video, voice, avatar
    prompt TEXT,
    model TEXT,
    provider TEXT,
    parameters JSONB,
    output_path TEXT,
    tokens_used INT,
    characters_used INT,
    duration_seconds FLOAT,
    cost_usd DECIMAL(10,4),
    render_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Video scenes (for complex video projects)
CREATE TABLE creative_video_scenes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id),
    scene_number INT NOT NULL,
    duration_seconds FLOAT,
    scene_type TEXT,  -- avatar, motion, stock, image
    narration TEXT,
    visual_direction TEXT,
    on_screen_text TEXT,
    asset_path TEXT,
    audio_path TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feedback/iterations
CREATE TABLE creative_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id),
    asset_id UUID REFERENCES creative_assets(id),
    feedback_type TEXT,
    feedback_text TEXT,
    timestamp_seconds FLOAT,  -- For video feedback
    given_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost tracking
CREATE TABLE creative_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id),
    task_id UUID REFERENCES creative_tasks(id),
    cost_type TEXT NOT NULL,  -- image, voice, avatar, api, storage
    provider TEXT,
    units_used FLOAT,
    unit_type TEXT,  -- tokens, characters, minutes, images
    cost_usd DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_projects_status ON creative_projects(status);
CREATE INDEX idx_projects_type ON creative_projects(type);
CREATE INDEX idx_tasks_project ON creative_tasks(project_id);
CREATE INDEX idx_tasks_status ON creative_tasks(status);
CREATE INDEX idx_assets_project ON creative_assets(project_id);
CREATE INDEX idx_scenes_project ON creative_video_scenes(project_id);
CREATE INDEX idx_costs_project ON creative_costs(project_id);
```

---

## INTEGRATION POINTS

### With Existing Agents

```yaml
ARIA:
  triggers:
    - "create presentation", "make a deck"
    - "write a report", "design a..."
    - "make a video", "create an explainer"
    - "social post about..."
  action: Route to MUSE for project creation
  
SCHOLAR:
  use_case: Research phase for content creation
  integration: MUSE calls SCHOLAR for market data, competitor info

HERMES:
  use_case: Notifications on project completion
  integration: MUSE notifies via HERMES when deliverables ready

HEPHAESTUS:
  use_case: File operations, template management
  integration: All agents use HEPHAESTUS for file I/O

CHRONOS:
  use_case: Backup before major generations
  integration: MUSE triggers backup before expensive operations

AEGIS:
  use_case: API key management
  integration: All external API calls go through AEGIS
```

### API Keys Required

```yaml
DALL-E 3:
  env: OPENAI_API_KEY
  cost: ~$0.04-0.08 per image
  managed_by: AEGIS
  
Synthesia:
  env: SYNTHESIA_API_KEY
  cost: ~$0.50-1.00 per video minute
  managed_by: AEGIS
  
HeyGen:
  env: HEYGEN_API_KEY
  cost: ~$0.50 per video minute
  managed_by: AEGIS
  
ElevenLabs:
  env: ELEVENLABS_API_KEY
  cost: ~$0.30 per 1000 characters
  managed_by: AEGIS
  
Pexels:
  env: PEXELS_API_KEY
  cost: Free
  managed_by: AEGIS

Pixabay:
  env: PIXABAY_API_KEY
  cost: Free
  managed_by: AEGIS
```

---

## N8N WORKFLOWS

### 1. Creative Project Orchestrator

```yaml
name: "MUSE-Project-Orchestrator"
trigger: Webhook from ARIA or direct call
nodes:
  - Parse request, create project
  - Decompose into tasks
  - Execute tasks in dependency order
  - Aggregate outputs
  - Notify via HERMES on completion
```

### 2. Video Assembly Pipeline

```yaml
name: "ERATO-Video-Pipeline"
trigger: Called by MUSE for video projects
nodes:
  - Generate voiceover (ElevenLabs)
  - Generate avatar (Synthesia/HeyGen)
  - Source stock footage (Pexels)
  - Assemble scenes (FFmpeg)
  - Add music, transitions
  - Generate thumbnail
  - Upload to storage
```

### 3. Cost Tracker

```yaml
name: "Creative-Cost-Tracker"
trigger: After each generation
nodes:
  - Calculate cost based on provider rates
  - Log to creative_costs table
  - Update project total
  - Alert if budget exceeded
```

---

## IMPLEMENTATION ORDER

### Phase 1: Foundation (6-8 hours)
| # | Task | Effort | Agent |
|---|------|--------|-------|
| 1 | Database schema (all tables) | 1.5 hrs | - |
| 2 | MUSE coordinator base | 2 hrs | MUSE |
| 3 | Project/task management | 2 hrs | MUSE |
| 4 | Brand library setup | 1.5 hrs | - |

### Phase 2: Content Creation (8-10 hours)
| # | Task | Effort | Agent |
|---|------|--------|-------|
| 5 | CALLIOPE writer agent | 3-4 hrs | CALLIOPE |
| 6 | THALIA presentation designer | 3-4 hrs | THALIA |
| 7 | Template system | 2 hrs | THALIA |

### Phase 3: Image Generation (4-5 hours)
| # | Task | Effort | Agent |
|---|------|--------|-------|
| 8 | ERATO image generation | 2-3 hrs | ERATO |
| 9 | Image post-processing | 1-2 hrs | ERATO |

### Phase 4: Video Production (10-12 hours)
| # | Task | Effort | Agent |
|---|------|--------|-------|
| 10 | ElevenLabs voice integration | 2 hrs | ERATO |
| 11 | Synthesia avatar integration | 2-3 hrs | ERATO |
| 12 | HeyGen avatar integration | 2 hrs | ERATO |
| 13 | FFmpeg video assembly | 2-3 hrs | ERATO |
| 14 | Stock footage sourcing | 1-2 hrs | ERATO |
| 15 | Video scene management | 1 hr | ERATO |

### Phase 5: Review & QA (4-5 hours)
| # | Task | Effort | Agent |
|---|------|--------|-------|
| 16 | CLIO reviewer base | 2 hrs | CLIO |
| 17 | Brand compliance checks | 1 hr | CLIO |
| 18 | Video quality review | 1-2 hrs | CLIO |

### Phase 6: Integration (4-5 hours)
| # | Task | Effort | Agent |
|---|------|--------|-------|
| 19 | ARIA integration | 1-2 hrs | - |
| 20 | SCHOLAR integration | 1 hr | - |
| 21 | Cost tracking system | 1 hr | - |
| 22 | End-to-end testing | 1-2 hrs | - |

**Total Effort:** ~36-45 hours

---

## EXAMPLE WORKFLOWS

### Example 1: Client Pitch Deck

**Request:**
```
"Create a 10-slide pitch deck for a compliance automation demo 
with TechCorp. Focus on time savings and audit readiness. 
Use our case study with ComplianceCo."
```

**Output:** `/opt/leveredge/creative/output/techcorp-pitch-v1.pptx`
**Time:** ~5 minutes
**Cost:** ~$0.50

---

### Example 2: 90-Second Explainer Video

**Request:**
```
"Create a 90-second explainer video about compliance automation.
Use an avatar presenter, show the product in action, end with CTA."
```

**MUSE Decomposition:**
```json
{
  "project_id": "proj_video_123",
  "type": "video",
  "tasks": [
    {
      "agent": "MUSE",
      "task": "Create storyboard (6 scenes)",
      "status": "complete"
    },
    {
      "agent": "CALLIOPE",
      "task": "Write 200-word script",
      "status": "complete",
      "output": "Are you spending hours on compliance reports..."
    },
    {
      "agent": "ERATO",
      "task": "Generate voiceover",
      "provider": "elevenlabs",
      "status": "complete",
      "cost": "$0.06"
    },
    {
      "agent": "ERATO",
      "task": "Generate avatar presenter",
      "provider": "synthesia",
      "status": "complete",
      "cost": "$0.75"
    },
    {
      "agent": "ERATO",
      "task": "Source B-roll footage",
      "provider": "pexels",
      "status": "complete",
      "cost": "$0"
    },
    {
      "agent": "ERATO",
      "task": "Assemble video",
      "status": "complete"
    },
    {
      "agent": "CLIO",
      "task": "Review final cut",
      "status": "complete",
      "issues": []
    }
  ],
  "total_cost": "$0.81",
  "duration": "92 seconds"
}
```

**Output:** 
- Video: `/opt/leveredge/creative/output/compliance-explainer-v1.mp4`
- Thumbnail: `/opt/leveredge/creative/output/compliance-explainer-thumb.png`

**Time:** ~8 minutes (mostly render time)
**Cost:** ~$0.81

---

### Example 3: LinkedIn Content Package

**Request:**
```
"Create a LinkedIn post about the importance of compliance automation
for mid-size companies, with an eye-catching image"
```

**Output:**
- Text: Optimized LinkedIn post (180 words)
- Image: `/opt/leveredge/creative/output/linkedin-compliance-image.png`

**Time:** ~2 minutes
**Cost:** ~$0.08

---

## COST ESTIMATES

| Operation | Cost | Notes |
|-----------|------|-------|
| 10-slide presentation | ~$0.50 | Text generation + charts |
| Presentation + custom graphics | ~$1.50 | Add DALL-E images |
| Document (2000 words) | ~$0.10 | Text only |
| Social post + image | ~$0.15 | Short text + 1 image |
| 60-second video (avatar) | ~$0.80 | Voice + avatar + assembly |
| 60-second video (motion) | ~$0.20 | Voice + graphics only |
| 60-second video (stock) | ~$0.10 | Voice + free footage |

**Monthly budget estimate:** $100-200 for typical usage
- 10-20 presentations: $10-30
- 50 images: $4-8
- 30 social posts: $5-10
- 10 videos (60s avg): $8-80

---

## SUCCESS CRITERIA

- [ ] MUSE can decompose any creative brief into tasks
- [ ] CALLIOPE generates quality content for all text types
- [ ] THALIA produces branded presentations from templates
- [ ] ERATO generates images via DALL-E 3
- [ ] ERATO generates voiceovers via ElevenLabs
- [ ] ERATO generates avatar videos via Synthesia/HeyGen
- [ ] ERATO assembles videos via FFmpeg
- [ ] ERATO sources stock footage from Pexels/Pixabay
- [ ] CLIO catches brand violations and quality issues
- [ ] CLIO reviews video quality (audio, visual, captions)
- [ ] End-to-end: Brief → Final deliverable
  - Presentation: <10 minutes
  - Document: <5 minutes
  - Image: <30 seconds
  - Video (60s): <10 minutes
- [ ] Brand consistency: 95%+ compliance rate
- [ ] Cost tracking accurate to $0.01
- [ ] All outputs saved to creative_assets table

---

## GIT COMMIT MESSAGE

```
Add Creative Fleet complete content production specification

Agents (Greek Muses):
- MUSE (8030): Creative Director (coordinator)
- CALLIOPE (8031): Writer (content, copy, scripts)
- THALIA (8032): Designer (presentations, layouts)
- ERATO (8033): Media Producer (images, video, audio)
- CLIO (8034): Reviewer (QA, brand compliance)

Content Types:
- Presentations (python-pptx)
- Documents (python-docx, PDF)
- Images (DALL-E 3)
- Video (Synthesia, HeyGen, ElevenLabs, FFmpeg)
- Social (multi-platform)

Video Capabilities:
- Avatar videos (Synthesia, HeyGen)
- Voice generation (ElevenLabs)
- Video assembly (FFmpeg, MoviePy)
- Stock footage (Pexels, Pixabay)

Database: 9 tables
Effort: ~40 hours
Integration: ARIA, SCHOLAR, HERMES, HEPHAESTUS, AEGIS
Cost tracking: Per-operation with budget alerts
```
