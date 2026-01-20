# GSD: ALOY - System-Wide Auditor

**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Created:** January 20, 2026
**Status:** Ready for execution
**Depends On:** None (can run parallel to VARYS redesign)

---

## OVERVIEW

ALOY is the Auditor - she actively investigates, scans, and finds what's wrong. While VARYS passively observes and reports what IS, ALOY hunts for what SHOULDN'T BE.

**Current State:** ALOY stuck calling non-existent `/subscribe` endpoint, completely non-functional
**Target State:** System-wide auditor that actively scans for problems across all environments

---

## PHILOSOPHY

> "I hunt machines. I find their weaknesses."

ALOY is named after the protagonist of Horizon Zero Dawn - a hunter who investigates ancient machines, understands their weaknesses, and takes them down. Our ALOY does the same for our system.

**ALOY must:**
- Roam ALL environments without restriction
- Actively scan code, configs, containers
- Find bugs BEFORE they cause incidents
- Audit deployments BEFORE they go to prod
- Report findings to ARIA and VARYS
- Block dangerous deployments (pre-deploy gate)

---

## VARYS vs ALOY

| Aspect | VARYS | ALOY |
|--------|-------|------|
| Mode | Passive observation | Active investigation |
| Question | "What IS the state?" | "What is WRONG?" |
| Trigger | Continuous monitoring | On-demand + scheduled |
| Output | Intelligence reports | Audit findings |
| Metaphor | Spider in web | Hunter on patrol |

**They work together:** VARYS detects anomaly → ALOY investigates root cause

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ALOY - SYSTEM AUDITOR                                    │
│                          (Host Network Mode)                                     │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         ALOY CORE (port 8015)                            │    │
│  │                                                                          │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │    │
│  │   │   SCANNER   │  │   DIFFER    │  │   HUNTER    │  │   GATEKEEPER│   │    │
│  │   │(Code/Config)│  │ (Dev/Prod)  │  │  (Bugs)     │  │ (Pre-deploy)│   │    │
│  │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │    │
│  │          │                │                │                │          │    │
│  └──────────┼────────────────┼────────────────┼────────────────┼──────────┘    │
│             │                │                │                │               │
│             ▼                ▼                ▼                ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                          AUDIT DATABASE                                   │  │
│  │   - Scan results                                                          │  │
│  │   - Findings history                                                      │  │
│  │   - Remediation tracking                                                  │  │
│  │   - Deployment gates                                                      │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│                              REPORTS TO                                          │
│                     ┌───────────┴───────────┐                                   │
│                     ▼                       ▼                                   │
│                   ARIA                    VARYS                                 │
│              (Human interface)      (Intelligence DB)                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: NETWORK TRANSCENDENCE

### 1.1 Host Network Mode

Like VARYS, ALOY uses `network_mode: host` to access all environments.

**Update docker-compose.fleet.yml:**

```yaml
aloy:
  image: aloy:latest
  container_name: aloy
  network_mode: host  # CRITICAL - audits all networks
  environment:
    ALOY_PORT: 8015
    VARYS_URL: "http://localhost:8112"
    ARIA_URL: "http://localhost:8114"
    LCIS_URL: "http://localhost:8050"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro  # Container inspection
    - /opt/leveredge:/opt/leveredge:ro  # Code scanning
  restart: unless-stopped
```

### 1.2 File System Access

ALOY needs to read code and configs:
- `/opt/leveredge` - All code, configs, specs
- Docker socket - Container inspection

---

## PHASE 2: AUDIT CAPABILITIES

### 2.1 Code Scanner

```python
class CodeScanner:
    """Scan code for security issues and anti-patterns."""
    
    CREDENTIAL_PATTERNS = [
        r'sk-[a-zA-Z0-9]{48}',           # OpenAI
        r'sk-proj-[a-zA-Z0-9-_]{48,}',   # OpenAI project
        r'xox[bp]-[a-zA-Z0-9-]+',        # Slack
        r'ghp_[a-zA-Z0-9]{36}',          # GitHub PAT
        r'ghs_[a-zA-Z0-9]{36}',          # GitHub App
        r'AKIA[A-Z0-9]{16}',             # AWS
        r'postgres://[^:]+:[^@]+@',      # DB connection string
        r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']',  # Generic API key
        r'secret\s*[=:]\s*["\'][^"\']+["\']',       # Generic secret
        r'token\s*[=:]\s*["\'][^"\']+["\']',        # Generic token
    ]
    
    async def scan_file(self, filepath: str) -> List[Finding]:
        """Scan a single file for issues."""
        findings = []
        
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in self.CREDENTIAL_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(Finding(
                        type="credential_exposure",
                        severity="critical",
                        file=filepath,
                        line=i + 1,
                        content=self._redact(line),
                        message="Potential credential in code"
                    ))
        
        return findings
    
    async def scan_directory(self, path: str, exclude: List[str] = None) -> AuditReport:
        """Scan entire directory tree."""
        exclude = exclude or ['node_modules', '.git', '__pycache__', 'venv', '.venv']
        findings = []
        
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in exclude]
            
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.env', '.yml', '.yaml', '.json', '.md')):
                    filepath = os.path.join(root, file)
                    file_findings = await self.scan_file(filepath)
                    findings.extend(file_findings)
        
        return AuditReport(
            scan_type="code",
            path=path,
            findings=findings,
            summary=self._summarize(findings)
        )
```

### 2.2 Environment Differ

```python
class EnvironmentDiffer:
    """Compare DEV and PROD for drift."""
    
    async def compare_schemas(self) -> DiffReport:
        """Compare database schemas between environments."""
        dev_schema = await self._get_schema("supabase-db-dev")
        prod_schema = await self._get_schema("supabase-db-prod")
        
        differences = []
        
        # Tables in dev but not prod
        dev_tables = set(dev_schema['tables'].keys())
        prod_tables = set(prod_schema['tables'].keys())
        
        for table in dev_tables - prod_tables:
            differences.append(Difference(
                type="missing_table",
                location="prod",
                item=table,
                severity="high",
                message=f"Table {table} exists in DEV but not PROD"
            ))
        
        # Column differences
        for table in dev_tables & prod_tables:
            dev_cols = set(dev_schema['tables'][table]['columns'])
            prod_cols = set(prod_schema['tables'][table]['columns'])
            
            for col in dev_cols - prod_cols:
                differences.append(Difference(
                    type="missing_column",
                    location=f"prod.{table}",
                    item=col,
                    severity="medium",
                    message=f"Column {table}.{col} missing in PROD"
                ))
        
        return DiffReport(
            comparison="dev_vs_prod",
            type="schema",
            differences=differences
        )
    
    async def compare_env_vars(self) -> DiffReport:
        """Compare environment variables between containers."""
        differences = []
        
        dev_env = await self._get_container_env("aria-chat-dev")
        prod_env = await self._get_container_env("aria-chat-prod")
        
        # Check for placeholder values in prod
        for key, value in prod_env.items():
            if 'your-' in value.lower() or 'placeholder' in value.lower():
                differences.append(Difference(
                    type="placeholder_value",
                    location="prod",
                    item=key,
                    severity="critical",
                    message=f"PROD has placeholder value for {key}"
                ))
        
        return DiffReport(
            comparison="dev_vs_prod",
            type="env_vars",
            differences=differences
        )
    
    async def compare_publications(self) -> DiffReport:
        """Compare Supabase realtime publications."""
        dev_pubs = await self._get_publications("supabase-db-dev")
        prod_pubs = await self._get_publications("supabase-db-prod")
        
        differences = []
        
        for table in dev_pubs - prod_pubs:
            differences.append(Difference(
                type="missing_publication",
                location="prod",
                item=table,
                severity="high",
                message=f"Table {table} in realtime publication in DEV but not PROD"
            ))
        
        return DiffReport(
            comparison="dev_vs_prod",
            type="realtime_publications",
            differences=differences
        )
```

### 2.3 Bug Hunter

```python
class BugHunter:
    """Active bug detection through testing and analysis."""
    
    async def hunt_endpoint_bugs(self) -> List[Finding]:
        """Test all known endpoints for issues."""
        findings = []
        
        for agent, config in KNOWN_ENDPOINTS.items():
            # Test health endpoint
            try:
                resp = await self.client.get(f"http://localhost:{config['port']}/health")
                if resp.status_code != 200:
                    findings.append(Finding(
                        type="unhealthy_endpoint",
                        severity="high",
                        agent=agent,
                        message=f"{agent} health check returned {resp.status_code}"
                    ))
            except Exception as e:
                findings.append(Finding(
                    type="unreachable_endpoint",
                    severity="critical",
                    agent=agent,
                    message=f"{agent} is unreachable: {e}"
                ))
        
        return findings
    
    async def hunt_log_errors(self) -> List[Finding]:
        """Scan container logs for errors."""
        findings = []
        
        for container in self.docker.containers.list():
            logs = container.logs(tail=100).decode('utf-8')
            
            error_patterns = [
                (r'ERROR', 'error'),
                (r'Exception', 'exception'),
                (r'CRITICAL', 'critical'),
                (r'500 Internal Server Error', 'http_500'),
                (r'Connection refused', 'connection_refused'),
                (r'invalid.*key', 'invalid_key'),
            ]
            
            for pattern, error_type in error_patterns:
                if re.search(pattern, logs, re.IGNORECASE):
                    findings.append(Finding(
                        type=f"log_{error_type}",
                        severity="medium",
                        container=container.name,
                        message=f"Found {error_type} in {container.name} logs"
                    ))
        
        return findings
    
    async def hunt_data_anomalies(self) -> List[Finding]:
        """Check for data issues like disappearing records."""
        findings = []
        
        # Check conversation counts
        dev_count = await self._count_conversations("dev")
        prod_count = await self._count_conversations("prod")
        
        # Compare to last known counts
        last_counts = await self._get_last_counts()
        
        if prod_count < last_counts.get('prod', 0) * 0.9:  # 10% decrease
            findings.append(Finding(
                type="data_loss",
                severity="critical",
                location="prod",
                message=f"PROD conversations dropped from {last_counts['prod']} to {prod_count}"
            ))
        
        return findings
```

### 2.4 Pre-Deploy Gatekeeper

```python
class DeploymentGatekeeper:
    """Gate deployments - block if issues found."""
    
    async def audit_deployment(self, service: str, environment: str) -> GateResult:
        """Run all pre-deployment checks."""
        
        checks = []
        
        # 1. Scan for credentials in code
        code_scan = await self.scanner.scan_directory(f"/opt/leveredge/control-plane/agents/{service}")
        if code_scan.has_critical():
            checks.append(Check(
                name="credential_scan",
                passed=False,
                message=f"Found {code_scan.critical_count} credentials in code"
            ))
        else:
            checks.append(Check(name="credential_scan", passed=True))
        
        # 2. Check env var placeholders
        if environment == "prod":
            env_diff = await self.differ.compare_env_vars()
            if env_diff.has_placeholders():
                checks.append(Check(
                    name="env_var_check",
                    passed=False,
                    message="PROD has placeholder environment variables"
                ))
            else:
                checks.append(Check(name="env_var_check", passed=True))
        
        # 3. Schema compatibility
        if environment == "prod":
            schema_diff = await self.differ.compare_schemas()
            if schema_diff.has_breaking_changes():
                checks.append(Check(
                    name="schema_check",
                    passed=False,
                    message=f"Schema has {schema_diff.breaking_count} breaking changes"
                ))
            else:
                checks.append(Check(name="schema_check", passed=True))
        
        # 4. Realtime publication check
        if "aria" in service:
            pub_diff = await self.differ.compare_publications()
            if pub_diff.has_differences():
                checks.append(Check(
                    name="realtime_check",
                    passed=False,
                    message="Realtime publications differ between DEV and PROD"
                ))
            else:
                checks.append(Check(name="realtime_check", passed=True))
        
        all_passed = all(c.passed for c in checks)
        
        return GateResult(
            service=service,
            environment=environment,
            passed=all_passed,
            checks=checks,
            recommendation="PROCEED" if all_passed else "BLOCK - Fix issues first"
        )
```

---

## PHASE 3: API ENDPOINTS

```python
# =============================================================================
# ALOY API
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "ALOY", "role": "System Auditor"}

# Scanning
@app.post("/scan/code")
async def scan_code(path: str = "/opt/leveredge"):
    """Scan code for security issues."""
    return await scanner.scan_directory(path)

@app.post("/scan/credentials")
async def scan_credentials():
    """Scan entire system for exposed credentials."""
    return await scanner.scan_for_credentials()

# Diffing
@app.get("/diff/schema")
async def diff_schema():
    """Compare DEV and PROD database schemas."""
    return await differ.compare_schemas()

@app.get("/diff/env")
async def diff_env():
    """Compare environment variables."""
    return await differ.compare_env_vars()

@app.get("/diff/publications")
async def diff_publications():
    """Compare realtime publications."""
    return await differ.compare_publications()

@app.get("/diff/full")
async def diff_full():
    """Full DEV vs PROD comparison."""
    return {
        "schema": await differ.compare_schemas(),
        "env_vars": await differ.compare_env_vars(),
        "publications": await differ.compare_publications(),
        "aloy_says": "I have compared the environments. Here is what differs."
    }

# Bug Hunting
@app.post("/hunt/endpoints")
async def hunt_endpoints():
    """Test all endpoints for issues."""
    return await hunter.hunt_endpoint_bugs()

@app.post("/hunt/logs")
async def hunt_logs():
    """Scan logs for errors."""
    return await hunter.hunt_log_errors()

@app.post("/hunt/data")
async def hunt_data():
    """Check for data anomalies."""
    return await hunter.hunt_data_anomalies()

@app.post("/hunt/all")
async def hunt_all():
    """Full bug hunt."""
    return {
        "endpoints": await hunter.hunt_endpoint_bugs(),
        "logs": await hunter.hunt_log_errors(),
        "data": await hunter.hunt_data_anomalies(),
        "aloy_says": "I have hunted through the system. Here is what I found."
    }

# Deployment Gate
@app.post("/gate/check")
async def gate_check(service: str, environment: str):
    """Check if deployment should proceed."""
    return await gatekeeper.audit_deployment(service, environment)

# APOLLO Integration
@app.post("/gate/apollo")
async def gate_apollo(request: ApolloGateRequest):
    """Called by APOLLO before deployments."""
    result = await gatekeeper.audit_deployment(request.service, request.environment)
    
    if not result.passed:
        # Alert ARIA
        await alert_aria(f"Deployment blocked: {request.service} to {request.environment}")
        # Log to LCIS
        await log_to_lcis(result)
    
    return {
        "proceed": result.passed,
        "checks": result.checks,
        "aloy_says": result.recommendation
    }

# Reports
@app.get("/report/audit")
async def audit_report():
    """Full system audit report."""
    return {
        "generated_at": datetime.now().isoformat(),
        "code_scan": await scanner.scan_directory("/opt/leveredge"),
        "env_diff": await differ.compare_full(),
        "bug_hunt": await hunter.hunt_all(),
        "recommendations": await generate_recommendations(),
        "aloy_says": "This is everything wrong with the system. Fix it."
    }
```

---

## PHASE 4: APOLLO INTEGRATION

### 4.1 Pre-Deploy Hook

**Update APOLLO to call ALOY before deployments:**

```python
# In apollo.py /promote/aria endpoint

async def promote_aria(request: PromoteRequest):
    # ... existing code ...
    
    # NEW: Call ALOY gate check
    aloy_result = await httpx.post(
        "http://localhost:8015/gate/check",
        json={"service": "aria-chat", "environment": "prod"}
    )
    
    if not aloy_result.json()["proceed"]:
        return {
            "success": False,
            "blocked_by": "ALOY",
            "reason": aloy_result.json()["aloy_says"],
            "checks": aloy_result.json()["checks"]
        }
    
    # ... continue with deployment ...
```

---

## PHASE 5: SCHEDULED AUDITS

```python
# Scheduled audit jobs

AUDIT_SCHEDULE = [
    {"name": "hourly_health", "interval": 3600, "job": "hunt_endpoints"},
    {"name": "hourly_logs", "interval": 3600, "job": "hunt_logs"},
    {"name": "daily_code_scan", "interval": 86400, "job": "scan_code"},
    {"name": "daily_diff", "interval": 86400, "job": "diff_full"},
    {"name": "daily_data_check", "interval": 86400, "job": "hunt_data"},
]

async def run_scheduled_audits():
    """Run audits on schedule."""
    while True:
        for audit in AUDIT_SCHEDULE:
            if should_run(audit):
                result = await run_audit(audit["job"])
                if result.has_critical_findings():
                    await alert_aria(result)
                    await alert_varys(result)
        await asyncio.sleep(60)
```

---

## PHASE 6: VERIFICATION

```bash
# Test ALOY endpoints
curl http://localhost:8015/health

# Scan for credentials
curl -X POST http://localhost:8015/scan/credentials

# Compare DEV vs PROD
curl http://localhost:8015/diff/full

# Hunt for bugs
curl -X POST http://localhost:8015/hunt/all

# Check deployment gate
curl -X POST "http://localhost:8015/gate/check?service=aria-chat&environment=prod"

# Full audit report
curl http://localhost:8015/report/audit
```

---

## ON COMPLETION

### 1. Move Spec
```bash
mv /opt/leveredge/specs/gsd-aloy-system-auditor.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons -H "Content-Type: application/json" -d '{
  "content": "ALOY redesigned as System-Wide Auditor. Host network mode, code scanning, env diffing, bug hunting, pre-deploy gating. ALOY finds what is WRONG.",
  "domain": "ALOY",
  "type": "success",
  "tags": ["gsd", "aloy", "auditor", "security"]
}'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: ALOY System-Wide Auditor

- Host network mode for full system access
- Code scanner for credential exposure
- Environment differ (DEV vs PROD)
- Bug hunter (endpoints, logs, data)
- Pre-deploy gatekeeper for APOLLO
- Scheduled audits

ALOY hunts machines. She finds their weaknesses."
```

---

## ALOY'S VOICE

```python
ALOY_PHRASES = [
    "I hunt machines. I find their weaknesses.",
    "The Old Ones built without understanding. We must do better.",
    "Every system has a vulnerability. I will find it.",
    "Trust is earned through verification.",
    "The machine thinks it's hidden. It's wrong.",
    "I don't guess. I scan, I diff, I know.",
    "Fix it now, or I'll be back.",
]
```

---

*"I hunt machines. I find their weaknesses. This system will be clean, or I will know why."*
