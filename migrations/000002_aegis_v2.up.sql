-- Migration 000002: AEGIS V2 Enterprise Credential Management

-- Enhanced credentials table
CREATE TABLE IF NOT EXISTS aegis_credentials_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'n8n',
    description TEXT,
    encrypted_value TEXT,
    encryption_key_id TEXT,
    provider_credential_id TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expiring', 'expired', 'rotating', 'failed', 'retired')),
    environment TEXT DEFAULT 'prod',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_health_check TIMESTAMPTZ,
    rotation_enabled BOOLEAN DEFAULT FALSE,
    rotation_interval_hours INT DEFAULT 720,
    rotation_strategy TEXT DEFAULT 'manual',
    next_rotation_at TIMESTAMPTZ,
    alert_threshold_hours INT DEFAULT 168,
    alert_sent BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Credential versions for rollback
CREATE TABLE IF NOT EXISTS aegis_credential_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    version INT NOT NULL,
    encrypted_value TEXT,
    provider_credential_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    reason TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    UNIQUE(credential_id, version)
);

-- Comprehensive audit log
CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    credential_id UUID,
    credential_name TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    target TEXT,
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Rotation history
CREATE TABLE IF NOT EXISTS aegis_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    rotated_at TIMESTAMPTZ DEFAULT NOW(),
    previous_version INT,
    new_version INT,
    trigger TEXT NOT NULL,
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_at TIMESTAMPTZ
);

-- Health checks
CREATE TABLE IF NOT EXISTS aegis_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,
    response_time_ms INT,
    details JSONB DEFAULT '{}',
    error_message TEXT
);

-- Provider registry
CREATE TABLE IF NOT EXISTS aegis_providers (
    id SERIAL PRIMARY KEY,
    provider_name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL,
    base_url TEXT,
    validation_endpoint TEXT,
    credential_fields JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Legacy credentials table (for backward compatibility)
CREATE TABLE IF NOT EXISTS aegis_credentials (
    id SERIAL PRIMARY KEY,
    credential_name TEXT UNIQUE NOT NULL,
    provider TEXT,
    n8n_credential_id TEXT,
    credential_type TEXT,
    description TEXT,
    environment TEXT DEFAULT 'prod',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_aegis_v2_status ON aegis_credentials_v2(status);
CREATE INDEX IF NOT EXISTS idx_aegis_v2_expires ON aegis_credentials_v2(expires_at);
CREATE INDEX IF NOT EXISTS idx_aegis_v2_env ON aegis_credentials_v2(environment);
CREATE INDEX IF NOT EXISTS idx_aegis_v2_provider ON aegis_credentials_v2(provider);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_ts ON aegis_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_action ON aegis_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_cred ON aegis_audit_log(credential_name);
CREATE INDEX IF NOT EXISTS idx_aegis_health_cred ON aegis_health_checks(credential_id);
CREATE INDEX IF NOT EXISTS idx_aegis_health_ts ON aegis_health_checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_provider ON aegis_credentials(provider);

-- Seed providers
INSERT INTO aegis_providers (provider_name, provider_type, base_url, validation_endpoint, credential_fields) VALUES
('openai', 'api_key', 'https://api.openai.com/v1', '/models', '{"api_key": {"type": "secret", "required": true}}'),
('anthropic', 'api_key', 'https://api.anthropic.com/v1', '/messages', '{"api_key": {"type": "secret", "required": true}}'),
('github', 'api_key', 'https://api.github.com', '/user', '{"personal_access_token": {"type": "secret", "required": true}}'),
('cloudflare', 'api_key', 'https://api.cloudflare.com/client/v4', '/user/tokens/verify', '{"api_token": {"type": "secret", "required": true}}'),
('telegram', 'api_key', 'https://api.telegram.org', '/getMe', '{"bot_token": {"type": "secret", "required": true}}'),
('google_oauth', 'oauth2', 'https://oauth2.googleapis.com', '/tokeninfo', '{"client_id": {"type": "string"}, "client_secret": {"type": "secret"}, "refresh_token": {"type": "secret"}}'),
('supabase', 'api_key', NULL, NULL, '{"project_url": {"type": "string"}, "anon_key": {"type": "string"}, "service_role_key": {"type": "secret"}}'),
('caddy_basic_auth', 'basic_auth', NULL, NULL, '{"username": {"type": "string"}, "password_hash": {"type": "secret"}}'),
('elevenlabs', 'api_key', 'https://api.elevenlabs.io/v1', '/voices', '{"api_key": {"type": "secret", "required": true}}'),
('sendgrid', 'api_key', 'https://api.sendgrid.com/v3', '/user/profile', '{"api_key": {"type": "secret", "required": true}}'),
('stripe', 'api_key', 'https://api.stripe.com/v1', '/balance', '{"secret_key": {"type": "secret"}, "publishable_key": {"type": "string"}}'),
('fal_ai', 'api_key', 'https://fal.run', '/health', '{"api_key": {"type": "secret", "required": true}}'),
('replicate', 'api_key', 'https://api.replicate.com/v1', '/models', '{"api_token": {"type": "secret", "required": true}}'),
('google_ai', 'api_key', 'https://generativelanguage.googleapis.com/v1', '/models', '{"api_key": {"type": "secret", "required": true}}')
ON CONFLICT (provider_name) DO NOTHING;

SELECT 'AEGIS V2 migration complete' as status;
