# GSD: LCIS Auto-Capture for All Sources

**Priority:** HIGH - Knowledge is being lost
**Estimated Effort:** 4-6 hours
**Created:** 2026-01-20
**Updated:** 2026-01-20 (expanded to all sources)

---

## PROBLEM

LCIS (Lessons Captured in Sessions) doesn't auto-capture lessons from multiple sources. Every debugging session, deployment, schema change, and agent error is a learning opportunity that's currently lost unless manually added.

**Evidence:** Jan 19-20 ARIA debugging session with 3+ root causes found, but LCIS only captured it after manual `POST /ingest`.

**Current State:**
- Phase 1 (Claude Hook) is DONE - `~/.claude/hooks/lcis-capture.sh` exists and is registered
- Phases 2-4 still needed

---

## ROOT CAUSE ANALYSIS

1. **LCIS is purely passive** - Only receives via POST /ingest API
2. **No Claude Code hook** - ~~Nothing analyzes transcripts for lessons~~ DONE
3. **No Event Bus integration** - LCIS doesn't subscribe to any events
4. **No agent reporting** - PANOPTES/ASCLEPIUS don't report fixes to LCIS
5. **No schema tracking** - Migrations happen without lesson capture
6. **No deployment tracking** - promote-to-prod.sh doesn't report to LCIS

---

## SOLUTION: Multi-Source Lesson Capture

### 1. Claude Code Stop Hook (PRIMARY) - DONE

Created `~/.claude/hooks/lcis-capture.sh`:

```bash
#!/bin/bash
# LCIS Auto-Capture Hook for Claude Code Sessions
# Detects debugging sessions and sends lessons to LCIS
#
# Triggers: Claude Code Stop event
# Receives: JSON with session_id, cwd, transcript_path

input=$(cat)
transcript_path=$(echo "$input" | jq -r '.transcript_path // empty')
session_id=$(echo "$input" | jq -r '.session_id // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')

# Exit if no transcript
[[ -z "$transcript_path" || ! -f "$transcript_path" ]] && exit 0

# Quick heuristics to detect debugging sessions
debug_patterns="(fixed|resolved|root cause|the issue was|found the problem|that was it|now working|problem was|bug was|caused by)"

if grep -qiE "$debug_patterns" "$transcript_path" 2>/dev/null; then
  project=$(basename "$cwd" 2>/dev/null || echo "unknown")
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  fix_context=$(grep -iE "$debug_patterns" "$transcript_path" 2>/dev/null | tail -5 | head -c 500)

  curl -s -X POST http://localhost:8050/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"pattern\",
      \"source_agent\": \"CLAUDE_SESSION\",
      \"title\": \"Debug session in $project ($timestamp)\",
      \"content\": \"Auto-captured debugging session. Context: $fix_context\\n\\nFull transcript: $transcript_path\",
      \"domain\": \"DEBUGGING\",
      \"severity\": \"medium\",
      \"tags\": [\"auto-captured\", \"claude-session\", \"needs-review\", \"$project\"]
    }" &>/dev/null &
fi
exit 0
```

Registered in `~/.claude/settings.json` under `hooks.Stop`.

---

### 2. Agent Errors/Fixes Capture (NEW)

Track agent errors and their resolutions automatically.

**Event Bus Subscriptions:**
```python
AGENT_EVENTS = [
    "agent.error",           # Any agent throws an error
    "agent.restart",         # Agent container/service restarted
    "agent.health.failed",   # Health check failed
    "agent.health.recovered",# Health check recovered after failure
]
```

**Error → Fix Correlation:**
```python
class ErrorTracker:
    """Track errors and correlate with fixes"""
    pending_errors: Dict[str, ErrorEvent] = {}  # agent_name -> error

    async def on_error(self, event: dict):
        """Store error, waiting for fix"""
        agent = event["agent"]
        self.pending_errors[agent] = ErrorEvent(
            agent=agent,
            error=event["error"],
            timestamp=datetime.utcnow(),
            source=event.get("source", "UNKNOWN")
        )

    async def on_recovery(self, event: dict):
        """Error was fixed - create lesson"""
        agent = event["agent"]
        if agent in self.pending_errors:
            error = self.pending_errors.pop(agent)
            duration = datetime.utcnow() - error.timestamp

            await ingest_lesson(LessonInput(
                type=LessonType.FAILURE,
                source_agent="EVENT_BUS",
                title=f"{agent} error resolved ({duration.seconds}s)",
                content=f"Error: {error.error}\nRecovery: {event.get('details', 'Unknown')}\nDuration: {duration}",
                domain="AGENT_HEALTH",
                severity="medium" if duration.seconds < 300 else "high",
                tags=["auto-captured", "agent-error", agent.lower()]
            ))
```

**Sources:**
- HERMES alerts (agent down notifications)
- ARGUS metrics (error rate spikes)
- Agent health endpoints (`/health` returning non-200)
- Docker events (container restart)

---

### 3. Schema Changes Capture (NEW)

Track all database schema changes automatically.

**Migration Hook:**
Add to migrate wrapper scripts (`migrate-dev`, `migrate-prod`):

```bash
#!/bin/bash
# Wrapper for golang-migrate with LCIS capture

ENV=$1  # dev or prod
shift
RESULT=$(migrate -path ./migrations -database "$DATABASE_URL" "$@" 2>&1)
EXIT_CODE=$?

# Get current version
VERSION=$(migrate -path ./migrations -database "$DATABASE_URL" version 2>&1)

# Report to LCIS
if [[ $EXIT_CODE -eq 0 ]]; then
    curl -s -X POST http://localhost:8050/ingest \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"success\",
            \"source_agent\": \"SCHEMA_WATCHER\",
            \"title\": \"Schema migration $ENV: $VERSION\",
            \"content\": \"Migration applied successfully.\\n\\nOutput:\\n$RESULT\",
            \"domain\": \"SCHEMA\",
            \"severity\": \"low\",
            \"tags\": [\"auto-captured\", \"schema\", \"$ENV\", \"migration\"]
        }" &>/dev/null &
else
    curl -s -X POST http://localhost:8050/ingest \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"failure\",
            \"source_agent\": \"SCHEMA_WATCHER\",
            \"title\": \"Schema migration FAILED $ENV: $VERSION\",
            \"content\": \"Migration failed!\\n\\nError:\\n$RESULT\",
            \"domain\": \"SCHEMA\",
            \"severity\": \"high\",
            \"tags\": [\"auto-captured\", \"schema\", \"$ENV\", \"migration-failed\"]
        }" &>/dev/null &
fi

echo "$RESULT"
exit $EXIT_CODE
```

**Schema Drift Detection:**
Add to PANOPTES or create standalone watcher:

```python
async def check_schema_drift():
    """Compare DEV and PROD schemas, create lesson if drift detected"""
    dev_tables = await get_tables("dev")
    prod_tables = await get_tables("prod")

    missing_in_prod = dev_tables - prod_tables
    missing_in_dev = prod_tables - dev_tables

    if missing_in_prod or missing_in_dev:
        await ingest_lesson(LessonInput(
            type=LessonType.PATTERN,
            source_agent="SCHEMA_WATCHER",
            title=f"Schema drift detected: {len(missing_in_prod)} tables missing in PROD",
            content=f"Tables in DEV but not PROD: {missing_in_prod}\nTables in PROD but not DEV: {missing_in_dev}",
            domain="SCHEMA",
            severity="high",
            tags=["auto-captured", "schema-drift", "needs-action"]
        ))
```

**What to Capture:**
- New tables created
- Altered columns (type changes, nullable changes)
- New RLS policies
- New functions/triggers
- DDL statements with reason (from commit message or GSD)

---

### 4. Deployment Events Capture (EXPANDED)

**Hook into promote-to-prod.sh:**
Add at end of script:

```bash
# ============================================================================
# LCIS REPORTING
# ============================================================================

report_to_lcis() {
    local status=$1
    local summary=$2
    local severity=$3

    curl -s -X POST http://localhost:8050/ingest \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"$([[ $status == 'success' ]] && echo 'success' || echo 'failure')\",
            \"source_agent\": \"DEPLOY_SCRIPT\",
            \"title\": \"ARIA PROD deployment: $status\",
            \"content\": \"$summary\\n\\nChecks: $CHECKS_PASSED passed, $CHECKS_FAILED failed\\nWarnings: $WARNINGS\\nTime: ${ELAPSED}s\",
            \"domain\": \"DEPLOYMENT\",
            \"severity\": \"$severity\",
            \"tags\": [\"auto-captured\", \"deployment\", \"aria\", \"prod\", \"$status\"]
        }" &>/dev/null &
}

# Call at end of script
if [[ $ERRORS -eq 0 ]]; then
    report_to_lcis "success" "Deployment completed successfully" "low"
else
    report_to_lcis "failed" "Deployment blocked: $ERRORS errors" "high"
fi
```

**Container Restart Tracking:**
```bash
# Add to /opt/leveredge/shared/scripts/docker-restart-hook.sh
#!/bin/bash
# Called by Docker event watcher when container restarts

CONTAINER=$1
REASON=$2

curl -s -X POST http://localhost:8050/ingest \
    -H "Content-Type: application/json" \
    -d "{
        \"type\": \"pattern\",
        \"source_agent\": \"DOCKER_EVENTS\",
        \"title\": \"Container restarted: $CONTAINER\",
        \"content\": \"Container $CONTAINER was restarted.\\nReason: $REASON\\nTimestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"domain\": \"INFRASTRUCTURE\",
        \"severity\": \"medium\",
        \"tags\": [\"auto-captured\", \"container-restart\", \"$CONTAINER\"]
    }" &>/dev/null &
```

**Deployment-Error Correlation:**
```python
async def correlate_deployment_errors():
    """Flag errors that occur within 30 min of deployment"""
    recent_deployments = await get_lessons(
        source_agent="DEPLOY_SCRIPT",
        since=timedelta(minutes=30)
    )

    if recent_deployments:
        deployment = recent_deployments[0]
        # Tag current error as potentially deployment-related
        return {"correlation": "post-deployment", "deployment_id": deployment.id}
```

---

### 5. LCIS Transcript Analyzer Endpoint

Add to `librarian.py`:

```python
@app.post("/analyze-transcript")
async def analyze_transcript(req: TranscriptRequest):
    """
    Analyze a Claude Code transcript for lessons.
    Uses LLM to extract:
    - Problem symptoms
    - Root causes found
    - Fixes applied
    - Prevention recommendations
    """
    transcript = read_transcript(req.transcript_path)

    # Use OpenAI to extract lessons
    prompt = """Analyze this debugging transcript and extract lessons:
    1. What broke? (symptom)
    2. Why? (root cause)
    3. How was it fixed?
    4. How to prevent in future?

    Return JSON: {lessons: [{title, symptom, cause, fix, prevention, severity, domain}]}

    Transcript:
    {transcript}
    """

    response = await openai_extract(prompt, transcript)

    for lesson in response.lessons:
        await ingest_lesson(LessonInput(
            type=LessonType.FAILURE,
            source_agent="CLAUDE_SESSION",
            title=lesson.title,
            content=f"Symptom: {lesson.symptom}\nCause: {lesson.cause}\nFix: {lesson.fix}",
            domain=lesson.domain or "DEBUGGING",
            severity=lesson.severity or "medium",
            tags=["auto-captured", "claude-session"]
        ))

    return {"lessons_captured": len(response.lessons)}
```

---

### 6. Event Bus Integration (EXPANDED)

Add to `librarian.py` startup:

```python
# Full list of topics to subscribe to
LCIS_EVENT_TOPICS = [
    # Agent health
    "agent.error",
    "agent.restart",
    "agent.health.failed",
    "agent.health.recovered",

    # Deployments
    "deployment.started",
    "deployment.completed",
    "deployment.failed",
    "deployment.rollback",

    # Schema
    "schema.migration.applied",
    "schema.migration.failed",
    "schema.drift.detected",

    # GSD workflow
    "gsd.completed",
    "gsd.failed",
    "gsd.phase.completed",

    # Legacy events (keep for compatibility)
    "error.resolved",
    "issue.healed",
    "integrity.restored",
]

async def subscribe_to_events():
    """Subscribe to Event Bus for automatic lesson capture"""
    for topic in LCIS_EVENT_TOPICS:
        await event_bus.subscribe(topic, handle_event)
        logger.info(f"LCIS subscribed to: {topic}")

async def handle_event(event: dict):
    """Convert events to lessons with smart categorization"""
    event_type = event.get("type", "unknown")

    # Determine lesson type
    if "failed" in event_type or "error" in event_type:
        lesson_type = LessonType.FAILURE
        severity = "high"
    elif "rollback" in event_type:
        lesson_type = LessonType.FAILURE
        severity = "critical"
    else:
        lesson_type = LessonType.SUCCESS
        severity = "low"

    # Determine domain
    domain_map = {
        "agent": "AGENT_HEALTH",
        "deployment": "DEPLOYMENT",
        "schema": "SCHEMA",
        "gsd": "WORKFLOW",
    }
    domain = next((v for k, v in domain_map.items() if k in event_type), "INFRASTRUCTURE")

    await ingest_lesson(LessonInput(
        type=lesson_type,
        source_agent=event.get("source", "EVENT_BUS"),
        title=event.get("summary", event_type),
        content=json.dumps(event.get("details", {}), indent=2),
        domain=domain,
        severity=severity,
        tags=["auto-captured", "event-bus", event_type]
    ))
```

---

### 7. Git Commit Hook

Add to `/opt/leveredge/.git/hooks/post-commit`:

```bash
#!/bin/bash
# Extract lessons from fix commits

msg=$(git log -1 --pretty=%B)
files=$(git diff HEAD~1 --name-only 2>/dev/null | head -20)
stats=$(git diff HEAD~1 --stat 2>/dev/null | tail -1)

# Only process fix commits
if echo "$msg" | grep -qiE "^(fix|hotfix|bugfix|resolve):"; then
  # Send to LCIS
  curl -s -X POST http://localhost:8050/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"success\",
      \"source_agent\": \"GIT_HOOK\",
      \"title\": \"$(echo "$msg" | head -1 | sed 's/"/\\"/g')\",
      \"content\": \"Commit: $(git rev-parse --short HEAD)\\n\\nFiles changed:\\n$files\\n\\nStats: $stats\",
      \"domain\": \"DEPLOYMENT\",
      \"severity\": \"low\",
      \"tags\": [\"auto-captured\", \"git-commit\", \"fix\"]
    }" &>/dev/null &
fi

exit 0
```

---

## IMPLEMENTATION ORDER

1. **Phase 1: Claude Hook** (30 min) - **DONE**
   - ~~Create `lcis-capture.sh`~~
   - ~~Register in settings.json~~
   - ~~Test with simple heuristics~~

2. **Phase 2: Transcript Analyzer** (1 hour)
   - Add `/analyze-transcript` endpoint
   - Implement LLM-based extraction
   - Handle rate limiting

3. **Phase 3: Event Bus Integration** (1 hour)
   - Add Event Bus client to LCIS
   - Subscribe to all relevant topics
   - Handle reconnection
   - Add error tracking correlation

4. **Phase 4: Git Hook** (15 min)
   - Create post-commit hook
   - Test with fix commits

5. **Phase 5: Schema Watcher** (1 hour) - **NEW**
   - Create migrate wrapper with LCIS reporting
   - Add schema drift detection
   - Test with DEV/PROD comparison

6. **Phase 6: Deployment Integration** (30 min) - **NEW**
   - Add LCIS reporting to promote-to-prod.sh
   - Add container restart tracking
   - Add deployment-error correlation

---

## ACCEPTANCE CRITERIA BY SOURCE

### Claude Sessions
- [ ] Debug session with "fixed" keyword → lesson created automatically
- [ ] Lesson includes: project name, timestamp, context snippet, transcript path
- [ ] Tagged with: `auto-captured`, `claude-session`, `needs-review`

### Git Commits
- [ ] Commit with "fix:" prefix → lesson created
- [ ] Lesson includes: commit hash, files changed, stats
- [ ] Tagged with: `auto-captured`, `git-commit`, `fix`

### Agent Events
- [ ] Agent restart → lesson created
- [ ] Agent health failure + recovery → lesson with duration
- [ ] Tagged with: `auto-captured`, `agent-error`, `<agent-name>`

### Deployments
- [ ] promote-to-prod.sh completes → lesson created with summary
- [ ] Deployment failure → high severity lesson
- [ ] Container restart → lesson with reason
- [ ] Tagged with: `auto-captured`, `deployment`, `aria`, `prod`

### Schema Changes
- [ ] Migration applied → lesson with version and output
- [ ] Migration failed → high severity lesson
- [ ] Schema drift detected → high severity lesson with diff
- [ ] Tagged with: `auto-captured`, `schema`, `<env>`

### GSD Workflow
- [ ] GSD completed → lesson with phase summary
- [ ] GSD failed → lesson with failure reason
- [ ] Tagged with: `auto-captured`, `gsd`

---

## VERIFICATION

**Check LCIS is capturing from all sources:**
```bash
# View recent lessons with source breakdown
curl -s "http://localhost:8050/lessons?limit=20" | jq '.[] | {title, source_agent, domain, created_at}'

# Expected sources:
# - CLAUDE_SESSION  (debug sessions)
# - GIT_HOOK        (fix commits)
# - EVENT_BUS       (agent events)
# - DEPLOY_SCRIPT   (deployments)
# - SCHEMA_WATCHER  (migrations)
# - DOCKER_EVENTS   (container restarts)

# Count by source
curl -s "http://localhost:8050/lessons?limit=100" | jq 'group_by(.source_agent) | map({source: .[0].source_agent, count: length})'
```

**Trigger each source manually for testing:**
```bash
# 1. Claude session - end a session with "fixed" in conversation
# 2. Git commit
git commit --allow-empty -m "fix: Test LCIS capture"

# 3. Schema migration
migrate-dev up 1

# 4. Deployment
/opt/leveredge/shared/scripts/promote-aria-to-prod.sh --dry-run

# 5. Container restart
docker restart aria-chat-dev
```

---

## SUCCESS CRITERIA

- [ ] LCIS captures lessons from 80%+ of debugging sessions automatically
- [ ] No manual POST /ingest needed for typical debug-and-fix flows
- [ ] Lessons include: symptom, cause, fix, prevention
- [ ] Event Bus events create lessons within 5 seconds
- [ ] Git fix commits captured with diff context
- [ ] Schema changes captured with DDL and version
- [ ] Deployments captured with success/failure and metrics
- [ ] All sources visible in `/lessons` endpoint

---

## QUICK WIN (Implement Now) - DONE

Phase 1 is complete. The Claude hook exists at `~/.claude/hooks/lcis-capture.sh` and is registered in `~/.claude/settings.json`.

**Next Quick Win: Git Hook**
```bash
# Create the hook
cat > /opt/leveredge/.git/hooks/post-commit << 'EOF'
#!/bin/bash
msg=$(git log -1 --pretty=%B)
if echo "$msg" | grep -qiE "^(fix|hotfix|bugfix|resolve):"; then
  curl -s -X POST http://localhost:8050/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"success\",
      \"source_agent\": \"GIT_HOOK\",
      \"title\": \"$(echo "$msg" | head -1 | sed 's/"/\\"/g')\",
      \"content\": \"$(git diff HEAD~1 --stat | tail -5)\",
      \"domain\": \"DEPLOYMENT\",
      \"severity\": \"low\",
      \"tags\": [\"auto-captured\", \"git-commit\"]
    }" &>/dev/null &
fi
exit 0
EOF
chmod +x /opt/leveredge/.git/hooks/post-commit
```

---

## NOTES

- Transcript analysis requires OpenAI API calls - budget ~$0.01 per session
- Event Bus integration requires HERMES Event Bus to support subscriptions
- Git hook only captures commits to /opt/leveredge repo
- Schema watcher requires migrate CLI wrapper scripts
- Container restart tracking requires Docker event listener (can use `docker events --filter`)
- Consider rate limiting on high-frequency events (agent health checks every 30s)
