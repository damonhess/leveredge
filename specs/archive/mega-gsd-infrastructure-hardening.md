# MEGA GSD: INFRASTRUCTURE HARDENING & PROVIDER CONNECTIVITY

*Prepared: January 17, 2026*
*For: Autonomous execution while Damon is away*
*Estimated Duration: 4-6 hours*

---

## OVERVIEW

This GSD tackles multiple infrastructure loose ends to harden the LeverEdge platform before launch. Work through each section in order, committing progress as you go.

**CRITICAL REMINDERS:**
- You have n8n-control MCP for control plane workflows
- You have n8n-troubleshooter MCP for data plane workflows
- DEV FIRST - all changes go to dev, test, then prod
- Log all significant operations to aria_knowledge
- Notify HERMES on completion of major sections

---

## SECTION 1: DATABASE MIRRORING (Dev ↔ Prod)

### Goal
Create automated sync mechanism so dev and prod databases stay aligned for schema (but NOT user data).

### Tasks

#### 1.1 Create Schema Sync Script
```bash
# Location: /opt/leveredge/shared/scripts/sync-schema.sh
```

The script should:
- Dump schema-only from prod: `pg_dump --schema-only`
- Apply to dev (tables, functions, triggers, RLS policies)
- Skip data tables (conversations, user data)
- Include: agent configs, workflow metadata, system tables

#### 1.2 Create Backup Verification Script
```bash
# Location: /opt/leveredge/shared/scripts/verify-backups.sh
```

The script should:
- Check CHRONOS backup directory for recent backups
- Verify backup integrity (can restore)
- Alert via HERMES if backups are stale (>24 hours)

#### 1.3 Add Cron Jobs
```bash
# Schema sync: Daily at 3 AM
0 3 * * * /opt/leveredge/shared/scripts/sync-schema.sh

# Backup verify: Daily at 4 AM  
0 4 * * * /opt/leveredge/shared/scripts/verify-backups.sh
```

#### 1.4 Create Migration Tracking Table
```sql
-- In both dev and prod
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW(),
    applied_by TEXT DEFAULT 'system',
    checksum TEXT
);
```

---

## SECTION 2: CLOUDFLARE ACCESS FOR CONTROL PLANE

### Goal
Replace basic auth with Cloudflare Access (email-based authentication).

### Current State
- control.n8n.leveredgeai.com uses basic auth
- Caddy handles reverse proxy

### Tasks

#### 2.1 Create Cloudflare Access Application
Via Cloudflare Dashboard or API:
- Application name: "LeverEdge Control Plane"
- Domain: control.n8n.leveredgeai.com
- Session duration: 24 hours
- Policy: Allow damon@leveredgeai.com

#### 2.2 Create Access Policy
```json
{
  "name": "LeverEdge Admins",
  "decision": "allow",
  "include": [
    {"email": {"email": "damon@leveredgeai.com"}},
    {"email_domain": {"domain": "leveredgeai.com"}}
  ]
}
```

#### 2.3 Update Caddy Configuration
```caddyfile
control.n8n.leveredgeai.com {
    # Remove basic_auth block
    # Cloudflare Access handles auth via headers
    
    reverse_proxy n8n-control:5678 {
        header_up X-Forwarded-Proto https
    }
    
    # Optional: Verify Cloudflare Access JWT
    # @cf_access header Cf-Access-Authenticated-User-Email *
    # handle @cf_access {
    #     reverse_proxy n8n-control:5678
    # }
}
```

#### 2.4 Add Access to Other Control Plane Services
Apply same pattern to:
- grafana.leveredgeai.com
- aegis.leveredgeai.com (future)
- Any other admin interfaces

#### 2.5 Document Access Setup
Update `/opt/leveredge/docs/CLOUDFLARE-ACCESS.md` with:
- How to add new users
- How to revoke access
- Service endpoints protected

---

## SECTION 3: AEGIS PROVIDER CONNECTIVITY

### Goal
Ensure AEGIS can manage and validate credentials for all external providers.

### Tasks

#### 3.1 Create Provider Registry Table
```sql
CREATE TABLE IF NOT EXISTS aegis_providers (
    id SERIAL PRIMARY KEY,
    provider_name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL, -- 'api_key', 'oauth2', 'service_account'
    base_url TEXT,
    auth_endpoint TEXT,
    token_endpoint TEXT,
    docs_url TEXT,
    required_scopes TEXT[],
    credential_fields JSONB, -- What fields are needed
    validation_endpoint TEXT, -- How to test if creds work
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2 Populate Provider Registry
```sql
INSERT INTO aegis_providers (provider_name, provider_type, base_url, validation_endpoint, credential_fields) VALUES

-- AI Providers
('openai', 'api_key', 'https://api.openai.com/v1', '/models', 
 '{"api_key": {"type": "secret", "required": true}}'),

('anthropic', 'api_key', 'https://api.anthropic.com/v1', '/messages',
 '{"api_key": {"type": "secret", "required": true}}'),

('google_ai', 'api_key', 'https://generativelanguage.googleapis.com/v1', '/models',
 '{"api_key": {"type": "secret", "required": true}}'),

('replicate', 'api_key', 'https://api.replicate.com/v1', '/models',
 '{"api_token": {"type": "secret", "required": true}}'),

('fal_ai', 'api_key', 'https://fal.run', '/health',
 '{"api_key": {"type": "secret", "required": true}}'),

('elevenlabs', 'api_key', 'https://api.elevenlabs.io/v1', '/voices',
 '{"api_key": {"type": "secret", "required": true}}'),

-- Google Services (OAuth2)
('google_oauth', 'oauth2', 'https://oauth2.googleapis.com', '/tokeninfo',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

('google_drive', 'oauth2', 'https://www.googleapis.com/drive/v3', '/about',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

('google_sheets', 'oauth2', 'https://sheets.googleapis.com/v4', '/spreadsheets',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

('gmail', 'oauth2', 'https://gmail.googleapis.com/gmail/v1', '/users/me/profile',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

-- GitHub
('github', 'api_key', 'https://api.github.com', '/user',
 '{"personal_access_token": {"type": "secret", "required": true}}'),

-- Communication
('telegram', 'api_key', 'https://api.telegram.org', '/getMe',
 '{"bot_token": {"type": "secret", "required": true}}'),

('sendgrid', 'api_key', 'https://api.sendgrid.com/v3', '/user/profile',
 '{"api_key": {"type": "secret", "required": true}}'),

-- Infrastructure
('cloudflare', 'api_key', 'https://api.cloudflare.com/client/v4', '/user/tokens/verify',
 '{"api_token": {"type": "secret", "required": true}}'),

('supabase', 'api_key', NULL, NULL,
 '{"project_url": {"type": "string", "required": true}, "anon_key": {"type": "string", "required": true}, "service_role_key": {"type": "secret", "required": true}}'),

-- Payment
('stripe', 'api_key', 'https://api.stripe.com/v1', '/balance',
 '{"secret_key": {"type": "secret", "required": true}, "publishable_key": {"type": "string", "required": true}}'),

-- Media
('midjourney', 'api_key', NULL, NULL,
 '{"discord_token": {"type": "secret", "required": true}, "server_id": {"type": "string", "required": true}}'),

('runway', 'api_key', 'https://api.runwayml.com/v1', '/health',
 '{"api_key": {"type": "secret", "required": true}}');
```

#### 3.3 Create Credential Validation Functions
```python
# /opt/leveredge/control-plane/agents/aegis/validators.py

async def validate_openai(api_key: str) -> bool:
    """Test OpenAI API key validity"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return response.status_code == 200

async def validate_anthropic(api_key: str) -> bool:
    """Test Anthropic API key validity"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}]
            }
        )
        return response.status_code in [200, 400]  # 400 = valid key, bad request

async def validate_github(token: str) -> bool:
    """Test GitHub PAT validity"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.status_code == 200

async def validate_cloudflare(api_token: str) -> bool:
    """Test Cloudflare API token validity"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.cloudflare.com/client/v4/user/tokens/verify",
            headers={"Authorization": f"Bearer {api_token}"}
        )
        return response.status_code == 200

async def validate_telegram(bot_token: str) -> bool:
    """Test Telegram bot token validity"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getMe"
        )
        return response.status_code == 200

# Add validators for each provider...
```

#### 3.4 Add AEGIS Endpoints for Provider Management
```python
# Add to /opt/leveredge/control-plane/agents/aegis/aegis.py

@app.get("/providers")
async def list_providers():
    """List all registered providers"""
    return await db_query("SELECT provider_name, provider_type, docs_url FROM aegis_providers")

@app.get("/providers/{provider_name}")
async def get_provider(provider_name: str):
    """Get provider details and credential requirements"""
    return await db_query(
        "SELECT * FROM aegis_providers WHERE provider_name = $1",
        provider_name
    )

@app.post("/credentials/{provider_name}/validate")
async def validate_credential(provider_name: str, credential_id: str):
    """Test if stored credential is still valid"""
    # Get credential from vault
    # Run appropriate validator
    # Return status

@app.get("/credentials/status")
async def credential_health_check():
    """Check validity of all stored credentials"""
    # Iterate through all credentials
    # Run validators
    # Return health report
```

#### 3.5 Create Credential Expiration Tracking
```sql
ALTER TABLE aegis_credentials ADD COLUMN IF NOT EXISTS 
    expires_at TIMESTAMP,
    last_validated_at TIMESTAMP,
    validation_status TEXT DEFAULT 'unknown',
    rotation_reminder_days INTEGER DEFAULT 90;

-- View for expiring credentials
CREATE OR REPLACE VIEW aegis_expiring_credentials AS
SELECT 
    credential_name,
    provider,
    expires_at,
    expires_at - NOW() as time_until_expiry
FROM aegis_credentials
WHERE expires_at IS NOT NULL
  AND expires_at < NOW() + INTERVAL '30 days'
ORDER BY expires_at;
```

---

## SECTION 4: GITHUB INTEGRATION

### Goal
AEGIS can manage GitHub PATs, track repos, and verify connectivity.

### Tasks

#### 4.1 Create GitHub Repos Table
```sql
CREATE TABLE IF NOT EXISTS aegis_github_repos (
    id SERIAL PRIMARY KEY,
    repo_name TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    environment TEXT NOT NULL, -- 'prod', 'dev', 'shared'
    purpose TEXT,
    default_branch TEXT DEFAULT 'main',
    last_push_at TIMESTAMP,
    credential_id INTEGER REFERENCES aegis_credentials(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 4.2 Populate Known Repos
```sql
INSERT INTO aegis_github_repos (repo_name, repo_url, environment, purpose) VALUES
('leveredge', 'git@github.com:damonhess/leveredge.git', 'shared', 'Main infrastructure'),
('aria-assistant', 'git@github.com:damonhess/aria-assistant.git', 'shared', 'ARIA codebase'),
('leveredge-ui', 'git@github.com:damonhess/leveredge-ui.git', 'shared', 'Frontend apps');
-- Add more as discovered
```

#### 4.3 Create GitHub Health Check
```python
@app.get("/github/health")
async def github_health():
    """Check connectivity to all registered GitHub repos"""
    results = []
    repos = await db_query("SELECT * FROM aegis_github_repos")
    
    for repo in repos:
        try:
            # Test git ls-remote
            result = await run_command(f"git ls-remote {repo['repo_url']} HEAD")
            results.append({
                "repo": repo["repo_name"],
                "status": "ok",
                "last_commit": result.split()[0][:7]
            })
        except Exception as e:
            results.append({
                "repo": repo["repo_name"],
                "status": "error",
                "error": str(e)
            })
    
    return {"github_repos": results}
```

#### 4.4 SSH Key Management
Verify SSH keys are properly configured:
```bash
# Check existing keys
ls -la ~/.ssh/

# Test GitHub connectivity
ssh -T git@github.com

# If needed, generate new key
ssh-keygen -t ed25519 -C "leveredge@server"

# Add to GitHub via API or web
```

---

## SECTION 5: COST TRACKING INTEGRATION

### Goal
Wire up LLM usage tracking into actual API calls.

### Tasks

#### 5.1 Verify Tables Exist
```sql
-- Should already exist, verify structure
SELECT * FROM llm_usage LIMIT 1;
SELECT * FROM llm_usage_daily LIMIT 1;
```

#### 5.2 Create Cost Tracking Wrapper
```python
# /opt/leveredge/shared/lib/cost_tracker.py

import httpx
from datetime import datetime
from typing import Optional

class CostTracker:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
    
    async def log_usage(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        context: str,
        operation: Optional[str] = None
    ):
        # Calculate cost based on model
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.supabase_url}/rest/v1/llm_usage",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                    "Content-Type": "application/json"
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
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Pricing as of Jan 2026
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        }
        
        if model in pricing:
            p = pricing[model]
            return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
        return 0.0
```

#### 5.3 Update CHIRON to Use Cost Tracker
```python
# In chiron.py, after each LLM call:

from shared.lib.cost_tracker import CostTracker

tracker = CostTracker(SUPABASE_URL, SUPABASE_KEY)

# After calling Claude:
await tracker.log_usage(
    agent_name="CHIRON",
    model="claude-3-5-sonnet-20241022",
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
    context=f"endpoint: {endpoint}",
    operation=operation_type
)
```

#### 5.4 Update SCHOLAR Similarly
Apply same pattern to SCHOLAR and any other LLM-powered agents.

#### 5.5 Create Cost Dashboard View
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
ORDER BY 1 DESC, 4 DESC;
```

---

## SECTION 6: DEV CREDENTIAL SEPARATION

### Goal
Ensure dev environment has its own credentials, not sharing prod.

### Tasks

#### 6.1 Audit Current State
```bash
# Find all credential references in n8n workflows
docker exec supabase-db-dev psql -U postgres -c "
SELECT DISTINCT 
    jsonb_path_query(nodes, '$.*.credentials.*.name') as credential_name
FROM workflow_entity 
WHERE active = true;"
```

#### 6.2 Create DEV Versions of Critical Credentials
In n8n dev instance, create:
- [ ] `Google Sheets DEV`
- [ ] `Telegram Bot DEV`
- [ ] `Google Drive DEV`
- [ ] `Supabase DEV` (should exist)
- [ ] `Anthropic DEV`

#### 6.3 Update AEGIS Inventory
```sql
-- Track which credentials exist in which environment
ALTER TABLE aegis_credentials ADD COLUMN IF NOT EXISTS environment TEXT DEFAULT 'prod';

-- Update existing
UPDATE aegis_credentials SET environment = 'prod' WHERE environment IS NULL;

-- Add dev entries as they're created
```

---

## SECTION 7: SYSTEMD SERVICES FOR NEW AGENTS

### Goal
Ensure new agents auto-start on reboot.

### Tasks

#### 7.1 Create Service Template
```bash
# /opt/leveredge/shared/templates/agent.service.template

[Unit]
Description=LeverEdge {{AGENT_NAME}} Agent
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/{{AGENT_DIR}}
ExecStart=/usr/bin/python3 -m uvicorn {{AGENT_MODULE}}:app --host 0.0.0.0 --port {{PORT}}
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/leveredge/shared/lib

[Install]
WantedBy=multi-user.target
```

#### 7.2 Create Service Generator Script
```bash
#!/bin/bash
# /opt/leveredge/shared/scripts/create-agent-service.sh

AGENT_NAME=$1
AGENT_DIR=$2
AGENT_MODULE=$3
PORT=$4

if [ -z "$AGENT_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: create-agent-service.sh AGENT_NAME AGENT_DIR AGENT_MODULE PORT"
    exit 1
fi

# Generate service file
sed -e "s/{{AGENT_NAME}}/$AGENT_NAME/g" \
    -e "s/{{AGENT_DIR}}/$AGENT_DIR/g" \
    -e "s/{{AGENT_MODULE}}/$AGENT_MODULE/g" \
    -e "s/{{PORT}}/$PORT/g" \
    /opt/leveredge/shared/templates/agent.service.template \
    > /etc/systemd/system/leveredge-${AGENT_NAME,,}.service

sudo systemctl daemon-reload
sudo systemctl enable leveredge-${AGENT_NAME,,}
sudo systemctl start leveredge-${AGENT_NAME,,}

echo "Created and started leveredge-${AGENT_NAME,,}.service"
```

#### 7.3 Create Services for Key Agents
Run for each agent that should auto-start:
```bash
./create-agent-service.sh CONVENER convener convener 8300
./create-agent-service.sh SCRIBE scribe scribe 8301
./create-agent-service.sh CHIRON chiron chiron 8017
./create-agent-service.sh SCHOLAR scholar scholar 8018
```

---

## SECTION 8: DOCUMENTATION UPDATES

### Tasks

#### 8.1 Update AGENT-ROUTING.md
Add any new agents, ensure ports are current.

#### 8.2 Create CREDENTIALS.md
Document all provider integrations and credential management.

#### 8.3 Update ARCHITECTURE.md
Ensure diagram reflects current state.

---

## COMPLETION CHECKLIST

After each section, commit progress:

```bash
cd /opt/leveredge
git add .
git commit -m "GSD: [Section N] - description"
```

At the end:
1. Run full health check
2. Notify HERMES with summary
3. Update LOOSE-ENDS.md
4. Log to aria_knowledge

---

## NOTIFICATION ON COMPLETION

```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "🔧 MEGA GSD Complete!\n\n✅ Database mirroring configured\n✅ Cloudflare Access ready\n✅ AEGIS provider registry built\n✅ GitHub integration complete\n✅ Cost tracking wired up\n✅ Services created\n\nReview logs and test when you return.",
    "priority": "normal"
  }'
```

---

*End of MEGA GSD Specification*
