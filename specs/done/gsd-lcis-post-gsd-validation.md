# GSD: LCIS Post-GSD Validation Rules

**Priority:** MEDIUM
**Estimated Time:** 15-20 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Add automatic validation to LCIS that enforces "ON COMPLETION" steps after every GSD execution:

1. **Spec moved to done/** - Verify spec file no longer in `/specs/`
2. **LCIS lesson logged** - Verify lesson was created for the GSD
3. **Git committed** - Verify recent commit mentions the GSD

---

## THE PROBLEM

Claude Code frequently skips cleanup steps after long builds:
- Specs stay in `/specs/` instead of `/specs/done/`
- No LCIS lesson logged
- Changes uncommitted

This breaks:
- Spec tracking (what's done vs pending)
- Knowledge capture (lessons lost)
- Version control (uncommitted changes)

---

## SOLUTION

Add to LCIS:
1. **Post-GSD validation endpoint** - Called after GSD completion
2. **Blocker rule** - Block next GSD if previous cleanup incomplete
3. **Auto-reminder** - Alert via HERMES if cleanup pending

---

## PHASE 1: ADD LCIS RULES

Insert these rules into the database:

```sql
-- Post-GSD validation rules
INSERT INTO lcis_rules (rule_type, pattern, action, message, severity, active) VALUES
-- Warn if specs not moved after GSD
('warn', 'gsd.*complete', 'remind', 
 'GSD completed - verify: 1) Spec moved to done/ 2) LCIS lesson logged 3) Git committed', 
 'medium', true),

-- Block new GSD if previous spec still in /specs/
('require', 'gsd.*start', 'validate_previous_gsd_cleanup',
 'Previous GSD spec still in /specs/. Move to done/ before starting new GSD.',
 'high', true);
```

---

## PHASE 2: ADD VALIDATION ENDPOINT

Add to `/opt/leveredge/control-plane/agents/lcis-librarian/librarian.py`:

```python
# =============================================================================
# POST-GSD VALIDATION
# =============================================================================

import subprocess
from pathlib import Path

SPECS_DIR = Path("/opt/leveredge/specs")
SPECS_DONE_DIR = Path("/opt/leveredge/specs/done")

@app.post("/validate/gsd-completion")
async def validate_gsd_completion(spec_name: str):
    """
    Validate that a GSD was properly completed:
    1. Spec moved to done/
    2. LCIS lesson logged
    3. Git committed
    """
    issues = []
    passed = []
    
    # 1. Check spec location
    spec_in_active = SPECS_DIR / spec_name
    spec_in_done = SPECS_DONE_DIR / spec_name
    
    if spec_in_active.exists():
        issues.append({
            "check": "spec_moved",
            "status": "failed",
            "message": f"Spec still in /specs/: {spec_name}",
            "fix": f"mv /opt/leveredge/specs/{spec_name} /opt/leveredge/specs/done/"
        })
    elif spec_in_done.exists():
        passed.append({"check": "spec_moved", "status": "passed"})
    else:
        issues.append({
            "check": "spec_moved",
            "status": "warning",
            "message": f"Spec not found in either location: {spec_name}"
        })
    
    # 2. Check LCIS lesson
    if pool:
        row = await pool.fetchrow("""
            SELECT id, created_at FROM lcis_lessons 
            WHERE content ILIKE $1 
            AND created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC LIMIT 1
        """, f"%{spec_name.replace('.md', '').replace('gsd-', '')}%")
        
        if row:
            passed.append({"check": "lcis_logged", "status": "passed", "lesson_id": str(row["id"])})
        else:
            issues.append({
                "check": "lcis_logged",
                "status": "failed",
                "message": "No LCIS lesson found for this GSD in the last hour",
                "fix": "Log completion lesson to LCIS"
            })
    
    # 3. Check git status
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5,
            cwd="/opt/leveredge"
        )
        recent_commits = result.stdout.lower()
        gsd_keywords = spec_name.replace(".md", "").replace("gsd-", "").replace("-", " ").split()
        
        # Check if any keyword appears in recent commits
        found_commit = any(kw in recent_commits for kw in gsd_keywords if len(kw) > 3)
        
        if found_commit:
            passed.append({"check": "git_committed", "status": "passed"})
        else:
            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
                cwd="/opt/leveredge"
            )
            if status_result.stdout.strip():
                issues.append({
                    "check": "git_committed",
                    "status": "failed",
                    "message": "Uncommitted changes detected",
                    "fix": "git add -A && git commit -m 'feat: <GSD description>'"
                })
            else:
                passed.append({"check": "git_committed", "status": "passed"})
    except Exception as e:
        issues.append({
            "check": "git_committed",
            "status": "error",
            "message": f"Could not check git: {str(e)}"
        })
    
    # Overall result
    all_passed = len(issues) == 0
    
    # Alert if issues found
    if issues:
        await alert_incomplete_gsd(spec_name, issues)
    
    return {
        "spec": spec_name,
        "complete": all_passed,
        "passed": passed,
        "issues": issues,
        "fix_commands": [i.get("fix") for i in issues if i.get("fix")]
    }


async def alert_incomplete_gsd(spec_name: str, issues: list):
    """Alert via HERMES about incomplete GSD cleanup"""
    try:
        issue_list = "\n".join([f"- {i['check']}: {i['message']}" for i in issues])
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://hermes:8014/alert",
                json={
                    "severity": "warning",
                    "source": "LCIS",
                    "title": f"GSD Cleanup Incomplete: {spec_name}",
                    "message": f"The following cleanup steps are pending:\n{issue_list}"
                }
            )
    except:
        pass


@app.get("/validate/pending-cleanups")
async def get_pending_cleanups():
    """List all specs that appear to be completed but not moved to done/"""
    pending = []
    
    # Find specs that look completed (mentioned in recent LCIS lessons or git)
    for spec_file in SPECS_DIR.glob("gsd-*.md"):
        if spec_file.name.startswith("gsd-"):
            # Check if there's a recent lesson mentioning completion
            if pool:
                row = await pool.fetchrow("""
                    SELECT id FROM lcis_lessons 
                    WHERE (content ILIKE '%complete%' OR content ILIKE '%deployed%' OR content ILIKE '%success%')
                    AND content ILIKE $1
                    AND created_at > NOW() - INTERVAL '24 hours'
                """, f"%{spec_file.stem.replace('gsd-', '')}%")
                
                if row:
                    pending.append({
                        "spec": spec_file.name,
                        "status": "likely_complete",
                        "fix": f"mv {spec_file} /opt/leveredge/specs/done/"
                    })
    
    return {
        "pending_cleanups": pending,
        "count": len(pending),
        "batch_fix": "cd /opt/leveredge && " + " && ".join([f"mv specs/{p['spec']} specs/done/" for p in pending]) if pending else None
    }
```

---

## PHASE 3: ADD CONSULTATION RULE

Add to LCIS rules to block new GSD if cleanup pending:

```python
# Add to consult() function in librarian.py

async def check_gsd_cleanup_before_new_gsd(action: str, target: str) -> dict:
    """Check if previous GSD cleanup is complete before starting new one"""
    
    if "gsd" not in target.lower():
        return {"proceed": True}
    
    # Check for incomplete cleanups
    pending = []
    for spec_file in SPECS_DIR.glob("gsd-*.md"):
        # Check if this spec was recently worked on (has matching LCIS entries)
        if pool:
            row = await pool.fetchrow("""
                SELECT id FROM lcis_lessons 
                WHERE content ILIKE $1
                AND created_at > NOW() - INTERVAL '4 hours'
            """, f"%{spec_file.stem}%")
            
            if row:
                pending.append(spec_file.name)
    
    if pending:
        return {
            "proceed": False,
            "blockers": [f"Previous GSD specs not moved to done/: {', '.join(pending)}"],
            "warnings": [],
            "recommendations": [
                f"Run: mv /opt/leveredge/specs/{pending[0]} /opt/leveredge/specs/done/",
                "Then retry the new GSD"
            ]
        }
    
    return {"proceed": True}
```

---

## PHASE 4: ADD HERMES REMINDER SCHEDULE

Add to VARYS scheduler or create dedicated reminder:

```python
# In varys_scheduler.py or new file

async def check_gsd_cleanups():
    """Periodic check for incomplete GSD cleanups - runs every 2 hours"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://lcis-librarian:8050/validate/pending-cleanups")
            data = response.json()
            
            if data.get("count", 0) > 0:
                specs = [p["spec"] for p in data["pending_cleanups"]]
                await client.post(
                    "http://hermes:8014/alert",
                    json={
                        "severity": "info",
                        "source": "LCIS",
                        "title": f"GSD Cleanup Reminder: {len(specs)} specs pending",
                        "message": f"Move to done/: {', '.join(specs)}"
                    }
                )
    except:
        pass
```

---

## VERIFICATION

```bash
# 1. Check current pending cleanups
curl http://localhost:8050/validate/pending-cleanups | jq

# 2. Validate a specific GSD
curl -X POST "http://localhost:8050/validate/gsd-completion?spec_name=gsd-omniscient-mesh.md" | jq

# 3. Move the pending specs now
mv /opt/leveredge/specs/gsd-omniscient-watchers.md /opt/leveredge/specs/done/
mv /opt/leveredge/specs/gsd-omniscient-mesh.md /opt/leveredge/specs/done/

# 4. Verify cleanup
curl http://localhost:8050/validate/pending-cleanups | jq
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-lcis-post-gsd-validation.md /opt/leveredge/specs/done/
```

### 2. Also Move the Pending Specs
```bash
mv /opt/leveredge/specs/gsd-omniscient-watchers.md /opt/leveredge/specs/done/
mv /opt/leveredge/specs/gsd-omniscient-mesh.md /opt/leveredge/specs/done/
```

### 3. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "LCIS Post-GSD Validation: Auto-validates spec moved, lesson logged, git committed. Blocks new GSD if previous cleanup incomplete. 2-hour reminder via HERMES.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "lcis", "validation", "cleanup"]
  }'
```

### 4. Git Commit
```bash
git add -A
git commit -m "feat: LCIS Post-GSD Validation - Enforce cleanup steps

- /validate/gsd-completion: Check spec moved, lesson logged, git committed
- /validate/pending-cleanups: List specs that need moving
- Auto-alert via HERMES for incomplete cleanups
- Block new GSD if previous cleanup pending

Never skip ON COMPLETION steps again."
```

---

## SUMMARY

| Check | What It Validates |
|-------|------------------|
| `spec_moved` | Spec file moved from `/specs/` to `/specs/done/` |
| `lcis_logged` | Completion lesson exists in LCIS |
| `git_committed` | Changes committed with relevant message |

**Enforcement:**
- Warns immediately after GSD completion
- Blocks new GSD if cleanup pending
- Reminds every 2 hours via HERMES

---

*"A GSD is not complete until it's cleaned up. LCIS remembers."*
