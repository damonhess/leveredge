-- ============================================================================
-- CREATIVE FLEET - Database Schema
-- ============================================================================
--
-- Complete content production system database schema
-- Tables for projects, tasks, assets, brands, costs, and generations
--
-- Run via: psql -h localhost -U postgres -d leveredge < schema.sql
-- ============================================================================

-- Brands
CREATE TABLE IF NOT EXISTS creative_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,

    -- Colors
    color_primary TEXT DEFAULT '#1B2951',
    color_secondary TEXT DEFAULT '#B8860B',
    color_accent TEXT DEFAULT '#36454F',
    color_background TEXT DEFAULT '#FFFFFF',
    color_text TEXT DEFAULT '#1A1A1A',

    -- Typography
    font_headings TEXT DEFAULT 'Inter',
    font_body TEXT DEFAULT 'Inter',
    font_code TEXT DEFAULT 'JetBrains Mono',

    -- Assets
    logo_path TEXT,
    logo_dark_path TEXT,
    icon_path TEXT,
    watermark_path TEXT,

    -- Voice
    tone TEXT DEFAULT 'professional',
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

-- Brand Assets
CREATE TABLE IF NOT EXISTS creative_brand_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES creative_brands(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    asset_path TEXT NOT NULL,
    usage_context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Voices
CREATE TABLE IF NOT EXISTS creative_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES creative_brands(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,  -- elevenlabs, synthesia
    voice_id TEXT NOT NULL,
    description TEXT,
    sample_url TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Avatars
CREATE TABLE IF NOT EXISTS creative_avatars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES creative_brands(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,  -- synthesia, heygen
    avatar_id TEXT NOT NULL,
    description TEXT,
    preview_url TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects
CREATE TABLE IF NOT EXISTS creative_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,  -- presentation, document, image, video, social
    title TEXT,
    brief TEXT NOT NULL,
    brand_id UUID REFERENCES creative_brands(id),
    status TEXT DEFAULT 'pending',  -- pending, in_progress, review, completed, failed
    priority TEXT DEFAULT 'medium',
    requested_by TEXT,
    deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    output_paths JSONB DEFAULT '[]',
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    video_config JSONB,  -- For video projects
    metadata JSONB DEFAULT '{}'
);

-- Tasks
CREATE TABLE IF NOT EXISTS creative_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,  -- MUSE, CALLIOPE, THALIA, ERATO, CLIO
    task_type TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, failed, skipped
    depends_on UUID[],
    input_data JSONB,
    output_data JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    cost_usd DECIMAL(10,4) DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- Generated Assets
CREATE TABLE IF NOT EXISTS creative_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES creative_tasks(id) ON DELETE SET NULL,
    asset_type TEXT NOT NULL,  -- image, video, audio, document, presentation
    file_path TEXT NOT NULL,
    file_size INT,
    mime_type TEXT,
    metadata JSONB,
    duration_seconds FLOAT,  -- For video/audio
    version INT DEFAULT 1,
    is_final BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generation History (for LLM/API calls)
CREATE TABLE IF NOT EXISTS creative_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES creative_tasks(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    generation_type TEXT NOT NULL,  -- text, image, video, voice, avatar
    prompt TEXT,
    model TEXT,
    provider TEXT,  -- anthropic, openai, elevenlabs, synthesia, heygen
    parameters JSONB,
    output_path TEXT,
    tokens_used INT,
    characters_used INT,
    duration_seconds FLOAT,
    cost_usd DECIMAL(10,4),
    render_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Video Scenes (for complex video projects)
CREATE TABLE IF NOT EXISTS creative_video_scenes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id) ON DELETE CASCADE,
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

-- Feedback/Iterations
CREATE TABLE IF NOT EXISTS creative_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES creative_assets(id) ON DELETE SET NULL,
    feedback_type TEXT,  -- revision, approval, rejection
    feedback_text TEXT,
    timestamp_seconds FLOAT,  -- For video feedback at specific time
    given_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost Tracking
CREATE TABLE IF NOT EXISTS creative_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES creative_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES creative_tasks(id) ON DELETE SET NULL,
    cost_type TEXT NOT NULL,  -- image, voice, avatar, api, storage
    provider TEXT,
    units_used FLOAT,
    unit_type TEXT,  -- tokens, characters, minutes, images
    cost_usd DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_creative_projects_status ON creative_projects(status);
CREATE INDEX IF NOT EXISTS idx_creative_projects_type ON creative_projects(type);
CREATE INDEX IF NOT EXISTS idx_creative_projects_created ON creative_projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_creative_tasks_project ON creative_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_creative_tasks_status ON creative_tasks(status);
CREATE INDEX IF NOT EXISTS idx_creative_tasks_agent ON creative_tasks(agent);
CREATE INDEX IF NOT EXISTS idx_creative_assets_project ON creative_assets(project_id);
CREATE INDEX IF NOT EXISTS idx_creative_assets_type ON creative_assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_creative_scenes_project ON creative_video_scenes(project_id);
CREATE INDEX IF NOT EXISTS idx_creative_costs_project ON creative_costs(project_id);
CREATE INDEX IF NOT EXISTS idx_creative_generations_task ON creative_generations(task_id);

-- Insert default LeverEdge brand
INSERT INTO creative_brands (
    name, description,
    color_primary, color_secondary, color_accent, color_background, color_text,
    font_headings, font_body, font_code,
    tone, voice_description
) VALUES (
    'LeverEdge AI',
    'Default LeverEdge brand profile',
    '#1B2951', '#B8860B', '#36454F', '#FFFFFF', '#1A1A1A',
    'Inter', 'Inter', 'JetBrains Mono',
    'professional',
    'Confident, knowledgeable, direct but approachable. Technical depth without jargon. Results-focused.'
) ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
