# AEGIS V2 - Enterprise Credential Management System

## OVERVIEW

Upgrade AEGIS from basic credential registry to enterprise-grade credential management with auto-rotation, health monitoring, encryption, and comprehensive audit trails.

**Current AEGIS V1 Capabilities:**
- Register credentials (name → n8n credential ID mapping)
- Apply credentials to workflow nodes
- Basic usage logging
- Sync from n8n

**AEGIS V2 New Capabilities:**
- Auto-rotation with configurable schedules
- Credential health monitoring (validity, expiry)
- AES-256 encryption at rest
- Multi-provider support (n8n, Supabase, external APIs)
- Visual dashboard with traffic light status
- Expiry alerts via HERMES
- Rotation history and versioning
- Emergency rotation capability
- Credential templates for common patterns

---

## RESEARCH FINDINGS (Applied)

| Finding | Application |
|---------|-------------|
| 49% of cyberattacks involve credential theft | Encrypt at rest, audit all access |
| Auto-rotation as frequent as every 4 hours | Configurable rotation schedules |
| AES-256 encryption standard | Encrypt stored credentials |
| Traffic light dashboards for status | Visual health indicators |
| Comprehensive audit logs required | Full access/rotation/usage logging |

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                      AEGIS V2                                │
│                   Credential Vault                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Registry   │  │  Rotation   │  │     Health          │ │
│  │  Manager    │  │  Engine     │  │     Monitor         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Encryption │  │   Audit     │  │     Alert           │ │
│  │  Layer      │  │   Logger    │  │     System          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    Provider Adapters                         │
│  ┌────────┐  ┌──────────┐  ┌────────┐  ┌────────────────┐  │
│  │  n8n   │  │ Supabase │  │  API   │  │  Environment   │  │
│  │Adapter │  │ Adapter  │  │Adapter │  │    Adapter     │  │
│  └────────┘  └──────────┘  └────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## CREDENTIAL LIFECYCLE

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│ CREATE  │───▶│ ENCRYPT  │───▶│ STORE   │───▶│ MONITOR  │
└─────────┘    └──────────┘    └─────────┘    └──────────┘
                                                   │
                                                   ▼
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│ RETIRE  │◀───│ VERSION  │◀───│ ROTATE  │◀───│ ALERT    │
└─────────┘    └──────────┘    └─────────┘    └──────────┘
```

**States:**
- `ACTIVE` - Credential in use, healthy
- `EXPIRING` - Within alert threshold of expiry
- `EXPIRED` - Past expiry date
- `ROTATING` - Rotation in progress
- `FAILED` - Rotation or health check failed
- `RETIRED` - Manually deactivated

---

## DATABASE SCHEMA

```sql
-- Core credential registry (enhanced)
CREATE TABLE aegis_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'n8n', -- n8n, supabase, api, env
    description TEXT,
    
    -- Encrypted storage
    encrypted_value TEXT, -- AES-256 encrypted (for non-n8n creds)
    encryption_key_id TEXT, -- Reference to encryption key used
    
    -- Provider reference
    provider_credential_id TEXT, -- n8n credential ID, etc.
    
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
    rotation_interval_hours INT DEFAULT 720, -- 30 days default
    rotation_strategy TEXT DEFAULT 'manual', -- manual, scheduled, on_expiry
    next_rotation_at TIMESTAMPTZ,
    
    -- Alert config
    alert_threshold_hours INT DEFAULT 168, -- 7 days before expiry
    alert_sent BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Credential versions (for rollback)
CREATE TABLE aegis_credential_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials(id) ON DELETE CASCADE,
    version INT NOT NULL,
    encrypted_value TEXT,
    provider_credential_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    reason TEXT, -- 'initial', 'rotation', 'manual_update', 'emergency'
    is_current BOOLEAN DEFAULT TRUE,
    
    UNIQUE(credential_id, version)
);

-- Comprehensive audit log
CREATE TABLE aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    credential_id UUID REFERENCES aegis_credentials(id),
    credential_name TEXT NOT NULL,
    action TEXT NOT NULL, -- 'created', 'read', 'applied', 'rotated', 'expired', 'failed', 'retired'
    actor TEXT NOT NULL, -- 'HEPHAESTUS', 'ARIA', 'scheduler', 'manual'
    target TEXT, -- workflow_id, node_name, etc.
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Rotation history
CREATE TABLE aegis_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials(id) ON DELETE CASCADE,
    rotated_at TIMESTAMPTZ DEFAULT NOW(),
    previous_version INT,
    new_version INT,
    trigger TEXT NOT NULL, -- 'scheduled', 'manual', 'emergency', 'expiry'
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_at TIMESTAMPTZ
);

-- Health check results
CREATE TABLE aegis_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL, -- 'healthy', 'unhealthy', 'unknown'
    response_time_ms INT,
    details JSONB DEFAULT '{}',
    error_message TEXT
);

-- Credential templates
CREATE TABLE aegis_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    description TEXT,
    schema JSONB NOT NULL, -- Required fields, validation rules
    rotation_defaults JSONB, -- Default rotation config
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_credentials_status ON aegis_credentials(status);
CREATE INDEX idx_credentials_expires ON aegis_credentials(expires_at);
CREATE INDEX idx_credentials_next_rotation ON aegis_credentials(next_rotation_at);
CREATE INDEX idx_audit_credential ON aegis_audit_log(credential_id);
CREATE INDEX idx_audit_timestamp ON aegis_audit_log(timestamp);
CREATE INDEX idx_audit_action ON aegis_audit_log(action);
```

---

## API ENDPOINTS

### Registry Management

```yaml
GET /health
response: { status, agent, version, credentials_count, healthy_count, expiring_count }

GET /credentials
query: { status?, provider?, type?, limit?, offset? }
response: { credentials[], total, healthy, expiring, expired }

GET /credentials/{name}
response: { credential_details, health_status, rotation_info, usage_stats }

POST /credentials
body: {
  name: string,
  credential_type: string,
  provider: "n8n" | "supabase" | "api" | "env",
  provider_credential_id?: string,  # For n8n
  value?: string,                   # For direct storage (encrypted)
  expires_at?: datetime,
  rotation_enabled?: boolean,
  rotation_interval_hours?: int,
  rotation_strategy?: "manual" | "scheduled" | "on_expiry",
  alert_threshold_hours?: int,
  tags?: string[],
  metadata?: object
}
response: { id, name, status, created_at }

PATCH /credentials/{name}
body: { description?, expires_at?, rotation_enabled?, rotation_interval_hours?, tags?, metadata? }
response: { credential, updated_fields }

DELETE /credentials/{name}
response: { status: "retired", credential_name }
```

### Credential Operations

```yaml
POST /credentials/{name}/apply
body: {
  workflow_id: string,
  node_name: string,
  requested_by: string
}
response: { status: "applied", credential, workflow_id, node }

POST /credentials/{name}/rotate
body: {
  trigger: "manual" | "emergency",
  reason?: string
}
response: { status: "rotated", previous_version, new_version, duration_ms }

POST /credentials/{name}/rollback
body: {
  version?: int  # Specific version or previous
}
response: { status: "rolled_back", from_version, to_version }

POST /credentials/{name}/test
response: { status: "healthy" | "unhealthy", response_time_ms, details }
```

### Health & Monitoring

```yaml
GET /health/dashboard
response: {
  summary: {
    total: int,
    healthy: int,
    expiring: int,
    expired: int,
    failed: int
  },
  credentials: [
    { name, status, health, expires_in_hours, last_used }
  ],
  alerts: [
    { credential, alert_type, message, created_at }
  ]
}

GET /health/expiring
query: { threshold_hours?: int }
response: { credentials[], count }

POST /health/check-all
response: { checked: int, healthy: int, unhealthy: int, details[] }
```

### Rotation Management

```yaml
GET /rotation/schedule
response: { upcoming_rotations[], overdue_rotations[] }

POST /rotation/run-scheduled
response: { rotated: int, failed: int, details[] }

GET /rotation/history
query: { credential_name?, limit?, offset? }
response: { history[], total }
```

### Audit & Compliance

```yaml
GET /audit/log
query: { credential_name?, action?, actor?, start_date?, end_date?, limit? }
response: { log[], total }

GET /audit/report
query: { start_date, end_date }
response: {
  period: { start, end },
  summary: {
    total_accesses: int,
    rotations: int,
    failures: int,
    unique_actors: int
  },
  by_credential: [...],
  by_action: [...],
  anomalies: [...]
}
```

### Sync & Import

```yaml
POST /sync/n8n
response: { synced: int, new: [], updated: [] }

POST /import/template
body: { template_name: string, values: object }
response: { credential, created: boolean }
```

---

## ROTATION ENGINE

### Rotation Strategies

```python
class RotationStrategy:
    """Base rotation strategy"""
    
    MANUAL = "manual"           # Only rotate on explicit request
    SCHEDULED = "scheduled"     # Rotate on interval (e.g., every 30 days)
    ON_EXPIRY = "on_expiry"     # Rotate when approaching expiry threshold
```

### Rotation Flow

```
1. TRIGGER (scheduled, manual, emergency, expiry)
        │
        ▼
2. LOCK credential (prevent concurrent rotation)
        │
        ▼
3. CREATE new version
        │
        ▼
4. GENERATE/FETCH new credential value
   ├── n8n: Create new credential via API
   ├── API: Call provider's rotation endpoint
   └── env: Update environment variable
        │
        ▼
5. TEST new credential (health check)
        │
        ├── SUCCESS ──────────────────────┐
        │                                 │
        ▼                                 ▼
6a. ROLLBACK if failed          6b. APPLY to workflows
        │                                 │
        ▼                                 ▼
7a. ALERT via HERMES            7b. UPDATE status, timestamps
        │                                 │
        ▼                                 ▼
8. LOG to audit                 8. LOG to audit
        │                                 │
        ▼                                 ▼
9. UNLOCK credential            9. UNLOCK credential
```

### Auto-Rotation Scheduler

```python
# Runs every hour via n8n workflow
async def run_scheduled_rotations():
    """
    1. Find credentials where:
       - rotation_enabled = True
       - rotation_strategy = 'scheduled'
       - next_rotation_at <= NOW()
       
    2. For each credential:
       - Execute rotation
       - Update next_rotation_at
       - Log result
       
    3. Find credentials where:
       - rotation_strategy = 'on_expiry'
       - expires_at - alert_threshold <= NOW()
       
    4. For each expiring credential:
       - Execute rotation
       - Update expires_at (if applicable)
       - Log result
    """
```

---

## HEALTH MONITORING

### Health Check Types

```yaml
n8n_credential:
  method: "Test credential via n8n workflow execution"
  indicators:
    - Can execute test workflow
    - No authentication errors
    
api_credential:
  method: "Call provider's test endpoint"
  indicators:
    - 200 response
    - Response time < threshold
    - Valid token response
    
database_credential:
  method: "Execute simple query"
  indicators:
    - Connection successful
    - Query returns expected result
```

### Status Determination

```python
def determine_status(credential, health_check):
    if credential.expires_at and credential.expires_at < now():
        return "expired"
    
    if credential.rotation_in_progress:
        return "rotating"
    
    if health_check and not health_check.success:
        return "failed"
    
    if credential.expires_at:
        hours_until_expiry = (credential.expires_at - now()).hours
        if hours_until_expiry <= credential.alert_threshold_hours:
            return "expiring"
    
    return "active"
```

### Dashboard Status Colors

```yaml
green:
  status: ["active"]
  label: "Healthy"
  
yellow:
  status: ["expiring"]
  label: "Expiring Soon"
  
red:
  status: ["expired", "failed"]
  label: "Action Required"
  
blue:
  status: ["rotating"]
  label: "Rotation in Progress"
  
gray:
  status: ["retired"]
  label: "Retired"
```

---

## ENCRYPTION LAYER

### Encryption at Rest

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class CredentialEncryption:
    """AES-256 encryption for credential values"""
    
    def __init__(self, master_key: str):
        # Derive key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'aegis_salt_v2',  # Should be per-credential in production
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        return self.fernet.decrypt(encrypted_value.encode()).decode()
```

### Key Management

```yaml
master_key_location: "/opt/leveredge/secrets/aegis_master.key"
key_rotation: "Manual, requires system restart"
backup_keys: "Stored encrypted in separate location"
```

---

## ALERTING (via HERMES)

### Alert Types

```yaml
credential_expiring:
  trigger: "expires_at - alert_threshold_hours <= NOW()"
  message: "🔐 Credential '{name}' expires in {hours} hours"
  channel: "telegram"
  priority: "high"

credential_expired:
  trigger: "expires_at < NOW()"
  message: "🚨 Credential '{name}' has EXPIRED"
  channel: "telegram"
  priority: "critical"

rotation_failed:
  trigger: "rotation_result.success = false"
  message: "❌ Rotation failed for '{name}': {error}"
  channel: "telegram"
  priority: "critical"

health_check_failed:
  trigger: "health_check.status = 'unhealthy'"
  message: "⚠️ Health check failed for '{name}': {details}"
  channel: "telegram"
  priority: "high"

rotation_success:
  trigger: "rotation_result.success = true"
  message: "✅ Credential '{name}' rotated successfully"
  channel: "telegram"
  priority: "low"
```

---

## PROVIDER ADAPTERS

### n8n Adapter

```python
class N8nCredentialAdapter:
    """Adapter for n8n credential management"""
    
    async def list_credentials(self) -> List[Credential]:
        """Fetch all credentials from n8n (metadata only)"""
        
    async def get_credential(self, credential_id: str) -> Credential:
        """Get credential details (no value)"""
        
    async def create_credential(self, type: str, name: str, data: dict) -> str:
        """Create new credential, return ID"""
        
    async def update_credential(self, credential_id: str, data: dict) -> bool:
        """Update credential value"""
        
    async def delete_credential(self, credential_id: str) -> bool:
        """Delete credential"""
        
    async def apply_to_workflow(self, credential_id: str, workflow_id: str, node_name: str) -> bool:
        """Apply credential to workflow node"""
```

### Supabase Adapter

```python
class SupabaseCredentialAdapter:
    """Adapter for Supabase credentials (service role key, anon key)"""
    
    async def test_credential(self, credential: Credential) -> HealthCheckResult:
        """Test Supabase connection with credential"""
        
    async def rotate_key(self, key_type: str) -> str:
        """Rotate Supabase key (requires Supabase dashboard API)"""
```

### Environment Adapter

```python
class EnvironmentCredentialAdapter:
    """Adapter for environment variable credentials"""
    
    async def get_value(self, env_var: str) -> str:
        """Get current value"""
        
    async def set_value(self, env_var: str, value: str) -> bool:
        """Update environment variable (requires container restart)"""
```

---

## N8N WORKFLOWS

### 1. AEGIS Health Monitor (Hourly)

```yaml
name: "AEGIS-Health-Monitor"
trigger: Cron "0 * * * *"  # Every hour
nodes:
  - HTTP Request: GET /health/check-all
  - IF: Any unhealthy?
    - Yes: HTTP Request to HERMES /notify
  - IF: Any expiring?
    - Yes: HTTP Request to HERMES /notify
```

### 2. AEGIS Rotation Scheduler (Hourly)

```yaml
name: "AEGIS-Rotation-Scheduler"
trigger: Cron "30 * * * *"  # Every hour at :30
nodes:
  - HTTP Request: POST /rotation/run-scheduled
  - IF: Any failures?
    - Yes: HTTP Request to HERMES /notify (critical)
  - Log results to Event Bus
```

### 3. AEGIS Daily Report

```yaml
name: "AEGIS-Daily-Report"
trigger: Cron "0 8 * * *"  # 8 AM daily
nodes:
  - HTTP Request: GET /health/dashboard
  - Format: Create summary report
  - HTTP Request to HERMES: Send daily status
```

---

## IMPLEMENTATION ORDER

### Phase 1: Core Enhancement (4-6 hours)
| # | Task | Effort |
|---|------|--------|
| 1 | Database migration (new tables) | 1 hr |
| 2 | Enhanced credential model | 1 hr |
| 3 | Basic encryption layer | 1 hr |
| 4 | Enhanced audit logging | 1-2 hrs |

### Phase 2: Health Monitoring (3-4 hours)
| # | Task | Effort |
|---|------|--------|
| 5 | Health check system | 1-2 hrs |
| 6 | Status determination logic | 1 hr |
| 7 | Dashboard endpoint | 1 hr |

### Phase 3: Rotation Engine (4-5 hours)
| # | Task | Effort |
|---|------|--------|
| 8 | Rotation engine core | 2 hrs |
| 9 | Version management | 1 hr |
| 10 | Rollback capability | 1 hr |
| 11 | Scheduled rotation | 1 hr |

### Phase 4: Alerting & Integration (2-3 hours)
| # | Task | Effort |
|---|------|--------|
| 12 | HERMES integration | 1 hr |
| 13 | n8n scheduler workflows | 1 hr |
| 14 | Event Bus integration | 1 hr |

### Phase 5: Provider Adapters (2-3 hours)
| # | Task | Effort |
|---|------|--------|
| 15 | Enhanced n8n adapter | 1 hr |
| 16 | Supabase adapter | 1 hr |
| 17 | Environment adapter | 1 hr |

**Total Effort:** ~15-21 hours

---

## SUCCESS CRITERIA

- [ ] All credentials encrypted at rest (AES-256)
- [ ] Health check runs every hour
- [ ] Expiring credentials trigger alerts 7 days before
- [ ] Auto-rotation works for scheduled credentials
- [ ] Rotation history preserved for 90 days
- [ ] Dashboard shows all credentials with status
- [ ] Audit log captures all access/changes
- [ ] Rollback works within 24 hours of rotation
- [ ] HERMES receives all critical alerts
- [ ] Zero credential values exposed in logs

---

## SECURITY CONSIDERATIONS

### Access Control
- Only AEGIS can decrypt credential values
- Other agents request credentials by name, never see values
- All access logged with actor identity

### Audit Requirements
- Log every credential access (read, apply, rotate)
- Log all failed attempts
- Preserve audit logs for 1 year minimum
- Generate compliance reports on demand

### Encryption
- AES-256 for values at rest
- TLS for all API communication
- Master key stored separately from data

### Rotation
- Old versions retained for rollback (encrypted)
- Automatic cleanup of versions older than 90 days
- Emergency rotation available without approval

---

## GIT COMMIT MESSAGE

```
Add AEGIS V2 credential management specification

New capabilities:
- Auto-rotation with configurable schedules
- AES-256 encryption at rest
- Credential health monitoring
- Version history and rollback
- Expiry alerts via HERMES
- Comprehensive audit logging
- Dashboard with traffic light status

Database: 6 new tables
Endpoints: 20+ new/enhanced
Effort: ~18 hours
Security: Enterprise-grade credential management
```
