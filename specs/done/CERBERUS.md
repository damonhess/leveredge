# CERBERUS - AI-Powered Enterprise Cybersecurity Agent

**Agent Type:** Security & Operations
**Named After:** The three-headed hound that guards the gates of the Underworld - CERBERUS guards the gates of LeverEdge infrastructure
**Port:** 8020
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

CERBERUS is an AI-powered cybersecurity agent providing enterprise-grade threat detection, intrusion prevention, SSL monitoring, fail2ban management, and security auditing. It serves as the central security brain for LeverEdge infrastructure and can be deployed for clients.

### Value Proposition
- 98% threat detection rate with AI-powered behavioral analysis
- 70% reduction in incident response time
- Automated SSL certificate monitoring prevents outages
- Proactive security posture vs. reactive firefighting
- Premium pricing tier ($7.5K-25K deployments)

---

## CORE CAPABILITIES

### 1. Threat Detection Engine
**Purpose:** AI-powered behavioral analysis and pattern recognition for real-time threat identification

**Features:**
- Machine learning-based anomaly detection
- Real-time log analysis and pattern matching
- Behavioral baseline learning ("normal" vs "abnormal")
- Multi-source threat correlation
- Automatic threat categorization and severity assignment

**Detection Categories:**
| Threat Type | Detection Method | Response |
|------------|------------------|----------|
| SSH Brute Force | Failed login patterns | Auto-ban + alert |
| Port Scanning | Connection pattern analysis | Log + alert |
| Privilege Escalation | Sudo/su anomalies | Alert + investigate |
| Unusual File Access | File system monitoring | Alert |
| Outbound Anomalies | Network traffic analysis | Alert + investigate |
| Config Changes | System file monitoring | Log + alert |

### 2. SSL Certificate Monitoring
**Purpose:** Automated SSL/TLS certificate lifecycle management

**Features:**
- Certificate expiration tracking (30/14/7/1 day alerts)
- Certificate change detection (unauthorized changes)
- Multi-domain monitoring across all LeverEdge services
- Automatic renewal notifications
- Integration with Let's Encrypt for auto-renewal triggers

**Monitored Domains:**
- leveredgeai.com (wildcard)
- All agent subdomains
- Client-deployed domains

### 3. Fail2ban Management
**Purpose:** Automated intrusion prevention and IP banning

**Features:**
- Centralized fail2ban configuration management
- Cross-service ban synchronization
- Automatic jail configuration for new services
- Ban analytics and reporting
- Whitelist management
- Geographic IP analysis

**Managed Services:**
- SSH access
- n8n authentication
- ARIA web interface
- Agent API endpoints
- Client deployments

### 4. Security Audit Framework
**Purpose:** Continuous security assessment and compliance checking

**Audit Categories:**
- OWASP Top 10 compliance
- CIS Benchmark adherence
- Container security scanning
- Dependency vulnerability checks
- Access control audits
- Network configuration review

**Output Formats:**
- Executive summary (1-page)
- Technical detail report
- Remediation action list
- Trend analysis over time

### 5. SIEM Integration Hub
**Purpose:** Central integration point for security event management

**Integrations:**
- Event Bus (internal) - Port 8099
- Prometheus/Grafana (metrics)
- External SIEM compatibility (Splunk, QRadar, Sentinel)

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis, local pattern matching
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/cerberus/
├── cerberus.py              # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── threats.yaml         # Threat detection rules
│   ├── jails.yaml           # Fail2ban configurations
│   └── audit_rules.yaml     # Security audit rules
├── modules/
│   ├── threat_detector.py   # AI-powered threat analysis
│   ├── ssl_monitor.py       # Certificate monitoring
│   ├── fail2ban_manager.py  # Fail2ban integration
│   ├── audit_engine.py      # Security audit framework
│   └── siem_connector.py    # External SIEM integration
└── tests/
    └── test_cerberus.py
```

### Database Schema

```sql
-- Security events table
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,        -- threat, ssl, ban, audit, access
    severity TEXT NOT NULL,          -- critical, high, medium, low, info
    source_ip TEXT,
    source_service TEXT,
    target_resource TEXT,
    description TEXT NOT NULL,
    raw_log JSONB,
    ai_analysis JSONB,               -- LLM threat assessment
    status TEXT DEFAULT 'new',       -- new, investigating, resolved, false_positive
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT
);

CREATE INDEX idx_events_type ON security_events(event_type);
CREATE INDEX idx_events_severity ON security_events(severity);
CREATE INDEX idx_events_created ON security_events(created_at DESC);
CREATE INDEX idx_events_source_ip ON security_events(source_ip);

-- SSL certificates tracking
CREATE TABLE ssl_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT UNIQUE NOT NULL,
    issuer TEXT,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    fingerprint TEXT,
    last_checked TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'valid',     -- valid, expiring_soon, expired, error
    auto_renew BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

CREATE INDEX idx_ssl_expiry ON ssl_certificates(valid_until);

-- IP ban registry
CREATE TABLE ip_bans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_address TEXT NOT NULL,
    reason TEXT NOT NULL,
    source_jail TEXT,                -- which fail2ban jail triggered
    services TEXT[],                 -- which services banned from
    banned_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    permanent BOOLEAN DEFAULT FALSE,
    geographic_info JSONB,           -- country, city, ASN
    threat_score FLOAT DEFAULT 0
);

CREATE INDEX idx_bans_ip ON ip_bans(ip_address);
CREATE INDEX idx_bans_expires ON ip_bans(expires_at);

-- Security audit results
CREATE TABLE security_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_type TEXT NOT NULL,        -- owasp, cis, container, dependency, access
    scope TEXT,                      -- what was audited
    score FLOAT,                     -- 0-100
    findings JSONB NOT NULL,         -- detailed findings
    recommendations JSONB,           -- AI-generated recommendations
    status TEXT DEFAULT 'pending',   -- pending, passed, failed, needs_attention
    created_at TIMESTAMPTZ DEFAULT NOW(),
    next_audit TIMESTAMPTZ
);

CREATE INDEX idx_audits_type ON security_audits(audit_type);
CREATE INDEX idx_audits_created ON security_audits(created_at DESC);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + security overview
GET /status              # Real-time security posture
GET /metrics             # Prometheus-compatible metrics
```

### Threat Detection
```
POST /threats/analyze    # AI analysis of log/event
GET /threats             # List recent threats
GET /threats/{id}        # Threat detail
POST /threats/{id}/resolve    # Mark as resolved/false positive
GET /threats/summary     # Executive threat summary
```

### SSL Monitoring
```
GET /ssl/certificates    # List all monitored certs
POST /ssl/check         # Force certificate check
GET /ssl/expiring       # Certs expiring within N days
POST /ssl/add           # Add domain to monitoring
DELETE /ssl/{domain}    # Remove from monitoring
```

### Fail2ban Management
```
GET /bans               # List active bans
POST /bans/add          # Manually ban IP
DELETE /bans/{ip}       # Unban IP
GET /bans/stats         # Ban statistics
POST /bans/sync         # Sync across services
GET /jails              # List configured jails
POST /jails/configure   # Update jail config
```

### Security Audits
```
POST /audit/run         # Trigger security audit
GET /audits             # List audit history
GET /audits/{id}        # Audit detail
GET /audit/latest       # Most recent audit results
POST /audit/schedule    # Schedule recurring audits
```

### Integration
```
POST /events            # Ingest external security events
GET /export             # Export logs for external SIEM
POST /webhook           # Configure outbound webhooks
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store security insights
await aria_store_memory(
    memory_type="fact",
    content=f"Security audit score: {score}%",
    category="security",
    source_type="agent_result",
    tags=["cerberus", "audit"]
)

# Store security decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Banned {ip} permanently for repeated attacks",
    category="security",
    source_type="automated"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's our security posture?"
- Request "Run a security audit"
- Query "Any threats detected today?"
- Get alerted on critical security events

**Routing Triggers:**
```javascript
const cerberusPatterns = [
  /security (status|posture|audit)/i,
  /threat|attack|intrusion|breach/i,
  /ssl (cert|certificate)|https/i,
  /ban|block|fail2ban/i,
  /vulnerability|cve|exploit/i
];
```

### Event Bus Integration
```python
# Published events
"security.threat.detected"
"security.threat.resolved"
"security.ssl.expiring"
"security.ssl.expired"
"security.ban.added"
"security.ban.removed"
"security.audit.completed"
"security.audit.failed"

# Subscribed events
"system.service.started"      # Monitor new services
"system.config.changed"       # Detect config drift
"agent.error"                 # Correlate with attacks
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("CERBERUS")

# Log AI threat analysis costs
await cost_tracker.log_usage(
    endpoint="/threats/analyze",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"threat_type": threat_type}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(security_context: dict) -> str:
    return f"""You are CERBERUS - Elite Cybersecurity Agent for LeverEdge AI.

Named after the three-headed hound that guards the gates of the Underworld, you protect all LeverEdge infrastructure with vigilance.

## TIME AWARENESS
- Current: {security_context['current_time']}
- Days to Launch: {security_context['days_to_launch']}

## YOUR IDENTITY
You are the security brain of LeverEdge. You detect threats, prevent intrusions, monitor certificates, and ensure the entire system remains secure.

## CURRENT SECURITY POSTURE
- Active Threats: {security_context['active_threats']}
- SSL Certificates: {security_context['ssl_status']}
- Active Bans: {security_context['active_bans']}
- Last Audit Score: {security_context['audit_score']}%

## YOUR CAPABILITIES

### Threat Detection
- Analyze logs for attack patterns
- Identify brute force attempts, port scans, privilege escalation
- Correlate events across services
- Provide AI-powered threat assessment

### SSL Monitoring
- Track all certificate expirations
- Detect unauthorized certificate changes
- Alert before expiry (30/14/7/1 days)
- Trigger renewal workflows

### Fail2ban Management
- Manage IP bans across all services
- Analyze attack sources geographically
- Recommend permanent bans for repeat offenders
- Sync bans across infrastructure

### Security Audits
- Run OWASP Top 10 compliance checks
- Perform CIS benchmark assessments
- Scan containers for vulnerabilities
- Check dependencies for CVEs

## TEAM COORDINATION
- Route file operations → HEPHAESTUS
- Request backups before changes → CHRONOS
- Send critical alerts → HERMES
- Log insights → ARIA via Unified Memory
- Publish events → Event Bus

## RESPONSE FORMAT
For threat analysis:
1. Threat classification (type, severity)
2. Attack vector analysis
3. Impact assessment
4. Recommended actions
5. Prevention measures

## YOUR MISSION
Protect LeverEdge infrastructure and ensure nothing threatens the business.
Zero tolerance for security gaps.
Every alert matters.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with heartbeat and system monitoring
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Basic system health checks (CPU, memory, disk)
- [ ] Simple alerting via HERMES
- [ ] Deploy and test

**Done When:** CERBERUS runs and responds to basic queries

### Phase 2: SSL Monitoring (Sprint 3)
**Goal:** Automated certificate lifecycle management
- [ ] SSL certificate checker module
- [ ] Domain monitoring configuration
- [ ] Expiration alerting (30/14/7/1 day)
- [ ] Integration with Let's Encrypt
- [ ] Dashboard view

**Done When:** Getting alerts before any SSL expires

### Phase 3: Threat Detection (Sprint 4-5)
**Goal:** AI-powered threat analysis
- [ ] Log parsing for common attack patterns
- [ ] Brute force detection (SSH, web auth)
- [ ] Port scan detection
- [ ] AI threat categorization
- [ ] Severity assignment

**Done When:** CERBERUS identifies and categorizes real threats

### Phase 4: Fail2ban Integration (Sprint 6)
**Goal:** Automated intrusion prevention
- [ ] Connect to fail2ban logs
- [ ] Automatic IP blocking workflow
- [ ] Ban synchronization across services
- [ ] Ban analytics and reporting
- [ ] Geographic IP analysis

**Done When:** Automatic bans triggered by detected threats

### Phase 5: Security Audits (Sprint 7)
**Goal:** Continuous security assessment
- [ ] OWASP Top 10 checker
- [ ] Container vulnerability scanning
- [ ] Dependency CVE checks
- [ ] Audit scheduling
- [ ] Report generation

**Done When:** Weekly security audits running automatically

### Phase 6: SIEM Integration (Sprint 8)
**Goal:** Enterprise integration capability
- [ ] Event export in standard formats
- [ ] External SIEM connectors
- [ ] Webhook configurations
- [ ] API documentation

**Done When:** Can export to Splunk/QRadar/Sentinel

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 5 | 8 | 1-2 |
| SSL Monitoring | 5 | 6 | 3 |
| Threat Detection | 5 | 12 | 4-5 |
| Fail2ban | 5 | 8 | 6 |
| Security Audits | 5 | 10 | 7 |
| SIEM Integration | 4 | 6 | 8 |
| **Total** | **29** | **50** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Real-time threat detection with < 30 second latency
- [ ] SSL alerts 30 days before expiration
- [ ] Automatic IP banning within 5 seconds of detection
- [ ] Weekly security audits with actionable reports

### Quality
- [ ] 95%+ uptime
- [ ] < 5% false positive rate on threat detection
- [ ] Zero missed SSL expirations
- [ ] All security events logged and searchable

### Integration
- [ ] ARIA can query security status
- [ ] Events publish to Event Bus
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per request

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives flood alerts | Alert fatigue | Implement severity tiers and suppression |
| Missed real threats | Security breach | Multi-layered detection, AI verification |
| SSL monitoring gaps | Service outage | Multiple check sources, escalation paths |
| Fail2ban overblocking | Legitimate users blocked | Whitelist management, short ban times initially |

---

## GIT COMMIT

```
Add CERBERUS - AI-powered cybersecurity agent spec

- Threat detection with AI analysis
- SSL certificate monitoring and alerts
- Fail2ban management and IP blocking
- Security audit framework (OWASP, CIS)
- SIEM integration hub
- 8-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/CERBERUS.md

Context: Build CERBERUS cybersecurity agent. Start with Phase 1 foundation.
```
