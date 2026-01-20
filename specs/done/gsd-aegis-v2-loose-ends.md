# GSD: AEGIS V2 + INFRASTRUCTURE LOOSE ENDS

*Prepared: January 17, 2026*
*Purpose: Upgrade AEGIS to enterprise credential management + clean up infrastructure loose ends*
*Estimated Duration: 6-8 hours*

---

## OVERVIEW

This GSD focuses on:
1. **AEGIS V2** - Full enterprise credential management upgrade
2. **Cost Tracking** - Wire LLM usage into ARIA and agents
3. **Dev Credential Separation** - Separate dev/prod credentials properly
4. **Cloudflare Access** - Replace basic auth on control plane
5. **GitHub Cleanup** - Consolidate accounts and verify connectivity

**CRITICAL REMINDERS:**
- You have n8n-control MCP for control plane workflows
- You have n8n-troubleshooter MCP for data plane workflows
- DEV FIRST - all changes go to dev, test, then prod
- Commit after each section
- Notify HERMES on completion

---

## SECTION 1: AEGIS V2 DATABASE SCHEMA

### 1.1 Run Migration (DEV First)

```sql
-- Connect to DEV database first, then PROD after testing

-- Core credential registry (enhanced)
CREATE TABLE IF NOT EXISTS aegis_credentials_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'n8n',
    description TEXT,
    
    -- Encrypted storage
    encrypted_value TEXT,
    encryption_key_id TEXT,
    
    -- Provider reference
    provider_credential_id TEXT,
    
    -- Lifecycle
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expiring', 'expired', 'rotating', 'failed', 'retired')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_health_check TIMESTAMPTZ,
    
    -- Rotation config
    rotation_enabled BOOLEAN DEFAULT FALSE,
    rotation_interval_hours INT DEFAULT 720,
    rotation_strategy TEXT DEFAULT 'manual',
    next_rotation_at TIMESTAMPTZ,
    
    -- Alert config
    alert_threshold_hours INT DEFAULT 168,
    alert_sent BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Credential versions
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

-- Audit log
CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    credential_id UUID REFERENCES aegis_credentials_v2(id),
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_creds_status ON aegis_credentials_v2(status);
CREATE INDEX IF NOT EXISTS idx_creds_expires ON aegis_credentials_v2(expires_at);
CREATE INDEX IF NOT EXISTS idx_creds_next_rotation ON aegis_credentials_v2(next_rotation_at);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON aegis_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON aegis_audit_log(action);
```

### 1.2 Populate Provider Registry

```sql
INSERT INTO aegis_providers (provider_name, provider_type, base_url, validation_endpoint, credential_fields) VALUES
('openai', 'api_key', 'https://api.openai.com/v1', '/models', 
 '{"api_key": {"type": "secret", "required": true}}'),
('anthropic', 'api_key', 'https://api.anthropic.com/v1', '/messages',
 '{"api_key": {"type": "secret", "required": true}}'),
('github', 'api_key', 'https://api.github.com', '/user',
 '{"personal_access_token": {"type": "secret", "required": true}}'),
('cloudflare', 'api_key', 'https://api.cloudflare.com/client/v4', '/user/tokens/verify',
 '{"api_token": {"type": "secret", "required": true}}'),
('telegram', 'api_key', 'https://api.telegram.org', '/getMe',
 '{"bot_token": {"type": "secret", "required": true}}'),
('google_oauth', 'oauth2', 'https://oauth2.googleapis.com', '/tokeninfo',
 '{"client_id": {"type": "string"}, "client_secret": {"type": "secret"}, "refresh_token": {"type": "secret"}}'),
('supabase', 'api_key', NULL, NULL,
 '{"project_url": {"type": "string"}, "anon_key": {"type": "string"}, "service_role_key": {"type": "secret"}}'),
('caddy_basic_auth', 'basic_auth', NULL, NULL,
 '{"username": {"type": "string"}, "password_hash": {"type": "secret"}, "config_path": {"type": "string"}}'),
('elevenlabs', 'api_key', 'https://api.elevenlabs.io/v1', '/voices',
 '{"api_key": {"type": "secret", "required": true}}'),
('fal_ai', 'api_key', 'https://fal.run', '/health',
 '{"api_key": {"type": "secret", "required": true}}'),
('sendgrid', 'api_key', 'https://api.sendgrid.com/v3', '/user/profile',
 '{"api_key": {"type": "secret", "required": true}}'),
('stripe', 'api_key', 'https://api.stripe.com/v1', '/balance',
 '{"secret_key": {"type": "secret"}, "publishable_key": {"type": "string"}}')
ON CONFLICT (provider_name) DO NOTHING;
```

---

## SECTION 2: AEGIS V2 FASTAPI APP

### 2.1 Create Encryption Module

```python
# /opt/leveredge/control-plane/agents/aegis/encryption.py

from cryptography.fernet import Fernet
import os

MASTER_KEY_PATH = "/opt/leveredge/secrets/aegis_master.key"

class CredentialEncryption:
    def __init__(self):
        self.fernet = None
        self._init_encryption()
    
    def _init_encryption(self):
        os.makedirs(os.path.dirname(MASTER_KEY_PATH), exist_ok=True)
        
        if os.path.exists(MASTER_KEY_PATH):
            with open(MASTER_KEY_PATH, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(MASTER_KEY_PATH, 'wb') as f:
                f.write(key)
            os.chmod(MASTER_KEY_PATH, 0o600)
        
        self.fernet = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        return self.fernet.decrypt(encrypted_value.encode()).decode()

encryption = CredentialEncryption()
```

### 2.2 Create AEGIS V2 App

Create `/opt/leveredge/control-plane/agents/aegis/aegis_v2.py` with:

**Core Endpoints:**
- `GET /health` - Health check with credential counts
- `GET /credentials` - List all (no values exposed)
- `GET /credentials/{name}` - Get credential details
- `POST /credentials` - Create new credential
- `PATCH /credentials/{name}` - Update credential
- `DELETE /credentials/{name}` - Retire credential

**Value Operations:**
- `GET /credentials/{name}/value` - Get decrypted value (logged)
- `POST /credentials/{name}/test` - Test credential validity
- `POST /credentials/{name}/rotate` - Rotate with new value
- `POST /credentials/{name}/rollback` - Rollback to previous version

**Health & Monitoring:**
- `GET /health/dashboard` - Full dashboard with alerts
- `GET /health/expiring` - Credentials expiring soon
- `POST /health/check-all` - Run health checks on all

**Rotation:**
- `GET /rotation/schedule` - Upcoming/overdue rotations
- `POST /rotation/run-scheduled` - Execute due rotations
- `GET /rotation/history` - Rotation history

**Audit:**
- `GET /audit/log` - Audit log with filters
- `GET /providers` - List registered providers

**Key Features:**
- AES-256 encryption for stored values
- Audit logging on all access
- Health check per provider type
- Version history for rollback
- HERMES alerts on failures

Reference the full implementation in `/opt/leveredge/specs/aegis-v2-credentials.md`

### 2.3 Deploy AEGIS V2

```bash
# Create systemd service
cat > /etc/systemd/system/leveredge-aegis-v2.service << 'EOF'
[Unit]
Description=LeverEdge AEGIS V2 Credential Manager
After=network.target

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/aegis
ExecStart=/usr/bin/python3 -m uvicorn aegis_v2:app --host 0.0.0.0 --port 8012
Restart=always
Environment=PYTHONPATH=/opt/leveredge/shared/lib

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable leveredge-aegis-v2
sudo systemctl start leveredge-aegis-v2
```

### 2.4 Verify Deployment

```bash
curl http://localhost:8012/health
# Should return: {"status": "healthy", "agent": "AEGIS", "version": "2.0", ...}
```

---

## SECTION 3: COST TRACKING INTEGRATION

### 3.1 Verify Tables Exist

```sql
-- Check llm_usage table exists
SELECT * FROM llm_usage LIMIT 1;

-- If not, create it:
CREATE TABLE IF NOT EXISTS llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT NOT NULL,
    output_tokens INT NOT NULL,
    estimated_cost_usd DECIMAL(10,6),
    context TEXT,
    operation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_agent ON llm_usage(agent_name);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at);
```

### 3.2 Create Cost Tracking Library

```python
# /opt/leveredge/shared/lib/cost_tracker.py

import httpx
from datetime import datetime
from typing import Optional

# Pricing per million tokens (as of Jan 2026)
PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}

class CostTracker:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        if model in PRICING:
            p = PRICING[model]
            return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
        return 0.0
    
    async def log_usage(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        context: str,
        operation: Optional[str] = None
    ):
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.supabase_url}/rest/v1/llm_usage",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "agent_name": agent_name,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "estimated_cost_usd": cost,
                    "context": context,
                    "operation": operation,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        
        return cost
```

### 3.3 Wire into CHIRON

Add to `/opt/leveredge/control-plane/agents/chiron/chiron.py`:

```python
from shared.lib.cost_tracker import CostTracker
import os

tracker = CostTracker(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# After each Anthropic API call:
async def call_claude_with_tracking(messages, system, operation):
    response = await anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        system=system,
        messages=messages
    )
    
    # Log usage
    await tracker.log_usage(
        agent_name="CHIRON",
        model="claude-3-5-sonnet-20241022",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        context=f"operation: {operation}",
        operation=operation
    )
    
    return response
```

### 3.4 Wire into SCHOLAR

Same pattern for SCHOLAR:

```python
# After each API call in scholar.py
await tracker.log_usage(
    agent_name="SCHOLAR",
    model="claude-3-5-sonnet-20241022",
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
    context=f"research: {topic}",
    operation="deep_research"
)
```

### 3.5 Wire into CONVENER

Same pattern for council meetings:

```python
await tracker.log_usage(
    agent_name="CONVENER",
    model="claude-3-5-sonnet-20241022",
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
    context=f"meeting: {meeting_id}",
    operation="facilitation"
)
```

### 3.6 Create Cost Summary View

```sql
CREATE OR REPLACE VIEW llm_cost_summary AS
SELECT 
    date_trunc('day', created_at) as day,
    agent_name,
    model,
    COUNT(*) as calls,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    SUM(estimated_cost_usd) as total_cost
FROM llm_usage
GROUP BY 1, 2, 3
ORDER BY 1 DESC, total_cost DESC;

-- Daily totals
CREATE OR REPLACE VIEW llm_daily_costs AS
SELECT 
    date_trunc('day', created_at) as day,
    SUM(estimated_cost_usd) as total_cost,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    COUNT(*) as total_calls
FROM llm_usage
GROUP BY 1
ORDER BY 1 DESC;
```

---

## SECTION 4: DEV CREDENTIAL SEPARATION

### 4.1 Audit Current State

```bash
# Find all credential references in prod n8n
# Use n8n-troubleshooter MCP to query workflows
```

### 4.2 Create DEV Credentials in n8n

In n8n DEV instance, create copies of:
- `Google Sheets DEV` (copy of prod Google Sheets)
- `Telegram Bot DEV` (separate bot for dev)
- `Google Drive DEV`
- `Anthropic DEV` (same key, different name for tracking)
- `Supabase DEV` (already exists)

### 4.3 Register in AEGIS V2

```bash
# Register dev credentials
curl -X POST http://localhost:8012/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "telegram_bot_dev",
    "credential_type": "bot_token",
    "provider": "telegram",
    "description": "Telegram bot for DEV environment",
    "tags": ["dev", "telegram"]
  }'

# Repeat for each dev credential
```

### 4.4 Update AEGIS to Track Environment

```sql
ALTER TABLE aegis_credentials_v2 
ADD COLUMN IF NOT EXISTS environment TEXT DEFAULT 'prod';

-- Update existing
UPDATE aegis_credentials_v2 
SET environment = 'dev' 
WHERE name LIKE '%_dev' OR name LIKE '%DEV%';
```

---

## SECTION 5: CLOUDFLARE ACCESS FOR CONTROL PLANE

### 5.1 Create Cloudflare Access Application

Via Cloudflare Dashboard (Zero Trust > Access > Applications):

1. **Application Name:** LeverEdge Control Plane
2. **Domain:** control.n8n.leveredgeai.com
3. **Session Duration:** 24 hours

### 5.2 Create Access Policy

Policy Name: LeverEdge Admins
- Include: Email equals damon@leveredgeai.com
- Include: Email domain is leveredgeai.com

### 5.3 Update Caddy Configuration

```caddyfile
# /etc/caddy/Caddyfile

control.n8n.leveredgeai.com {
    # Remove basic_auth block - Cloudflare Access handles auth
    reverse_proxy n8n-control:5678 {
        header_up X-Forwarded-Proto https
    }
}
```

### 5.4 Reload Caddy

```bash
sudo systemctl reload caddy
```

### 5.5 Test Access

1. Clear browser cookies for control.n8n.leveredgeai.com
2. Navigate to control.n8n.leveredgeai.com
3. Should redirect to Cloudflare Access login
4. Login with damon@leveredgeai.com
5. Verify access works

### 5.6 Apply to Other Control Plane Services (Optional)

If you want Cloudflare Access on:
- grafana.leveredgeai.com
- aegis.leveredgeai.com (when exposed)

Add them to the same Access Application or create separate ones.

---

## SECTION 6: GITHUB CLEANUP

### 6.1 Verify SSH Keys

```bash
# Check existing keys
ls -la ~/.ssh/

# Test GitHub connectivity
ssh -T git@github.com
```

### 6.2 Audit Repositories

```bash
cd /opt/leveredge
git remote -v

# Check all repos have proper remotes
find /opt/leveredge -name ".git" -type d -exec dirname {} \; | while read repo; do
    echo "=== $repo ==="
    cd "$repo" && git remote -v
done
```

### 6.3 Consolidate to Single Account

If using multiple GitHub accounts:
1. Choose primary: `damonhess`
2. Transfer repos from `damonhess-dev` if needed
3. Update remotes to use primary account

```bash
# Update remote if needed
git remote set-url origin git@github.com:damonhess/leveredge.git
```

### 6.4 Register GitHub PAT in AEGIS

```bash
curl -X POST http://localhost:8012/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "github_pat_primary",
    "credential_type": "personal_access_token",
    "provider": "github",
    "description": "GitHub PAT for damonhess account",
    "value": "ghp_xxxxxxxxxxxx",
    "rotation_enabled": true,
    "rotation_interval_hours": 2160,
    "alert_threshold_hours": 336
  }'
```

### 6.5 Test GitHub Credential

```bash
curl -X POST http://localhost:8012/credentials/github_pat_primary/test
```

---

## SECTION 7: N8N WORKFLOWS FOR AEGIS

### 7.1 Create AEGIS Health Monitor Workflow

In n8n-control, create workflow:

**Name:** AEGIS-Health-Monitor
**Trigger:** Cron every hour (`0 * * * *`)

```
Cron → HTTP Request (GET /health/check-all) → IF (unhealthy > 0) → HTTP Request (HERMES /notify)
```

### 7.2 Create AEGIS Rotation Scheduler

**Name:** AEGIS-Rotation-Scheduler  
**Trigger:** Cron every hour at :30 (`30 * * * *`)

```
Cron → HTTP Request (POST /rotation/run-scheduled) → IF (failed > 0) → HTTP Request (HERMES /notify critical)
```

### 7.3 Create AEGIS Daily Report

**Name:** AEGIS-Daily-Report
**Trigger:** Cron daily at 8 AM (`0 8 * * *`)

```
Cron → HTTP Request (GET /health/dashboard) → Format Message → HTTP Request (HERMES /notify)
```

---

## SECTION 8: IMPORT EXISTING CREDENTIALS

### 8.1 Import Critical Credentials to AEGIS

Register credentials AEGIS should track (values stored encrypted):

```bash
# Anthropic API Key
curl -X POST http://localhost:8012/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "anthropic_api_key",
    "credential_type": "api_key",
    "provider": "anthropic",
    "description": "Main Anthropic API key",
    "value": "sk-ant-xxxx",
    "rotation_enabled": false
  }'

# Cloudflare API Token
curl -X POST http://localhost:8012/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cloudflare_api_token",
    "credential_type": "api_token",
    "provider": "cloudflare",
    "description": "Cloudflare API token for DNS/Access",
    "value": "xxxx"
  }'

# Telegram Bot Token
curl -X POST http://localhost:8012/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "telegram_bot_prod",
    "credential_type": "bot_token",
    "provider": "telegram",
    "description": "HERMES Telegram bot",
    "value": "xxxx:yyyy"
  }'

# ARIA Basic Auth (Caddy)
curl -X POST http://localhost:8012/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "aria_basic_auth",
    "credential_type": "basic_auth",
    "provider": "caddy_basic_auth",
    "description": "ARIA web interface password",
    "value": "your_password_here",
    "metadata": {"config_path": "/etc/caddy/Caddyfile", "username": "damon"}
  }'
```

### 8.2 Test All Credentials

```bash
curl -X POST http://localhost:8012/health/check-all
```

---

## COMPLETION CHECKLIST

- [ ] AEGIS V2 database schema migrated (DEV then PROD)
- [ ] Provider registry populated
- [ ] AEGIS V2 FastAPI app deployed on port 8012
- [ ] Encryption key generated and secured
- [ ] Cost tracking library created
- [ ] Cost tracking wired into CHIRON, SCHOLAR, CONVENER
- [ ] DEV credentials created and registered
- [ ] Cloudflare Access configured for control plane
- [ ] GitHub SSH verified and PAT registered
- [ ] n8n workflows created (health monitor, rotation, daily report)
- [ ] Critical credentials imported to AEGIS
- [ ] All credentials health-checked

---

## COMMIT AFTER EACH SECTION

```bash
cd /opt/leveredge
git add .
git commit -m "GSD: Section N - description"
```

---

## NOTIFICATION ON COMPLETION

```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "🔐 AEGIS V2 + LOOSE ENDS COMPLETE!\n\n✅ AEGIS V2 deployed (port 8012)\n✅ Cost tracking wired in\n✅ Dev credentials separated\n✅ Cloudflare Access configured\n✅ GitHub cleaned up\n✅ Credentials imported\n\nAll systems secure.",
    "priority": "high"
  }'
```

---

*End of GSD*
