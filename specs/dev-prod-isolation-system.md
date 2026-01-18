# DEV/PROD ISOLATION SYSTEM

**Priority:** CRITICAL
**Owner:** System-level enforcement
**Created:** January 18, 2026

---

## Problem Statement

Claude Code accidentally modified production last night. We need hard guardrails that:
1. Default to DEV always
2. Require explicit unlock for PROD
3. Log all PROD access with reason
4. Auto-relock after timeout
5. Work for both Claude Code AND Claude Web (via HEPHAESTUS)

---

## Solution: Three-Layer Protection

### Layer 1: Environment Lock File

**File:** `/opt/leveredge/.environment-lock`

```ini
# LeverEdge Environment Lock
# DO NOT EDIT MANUALLY - Use unlock-prod.sh

CURRENT_ENV=dev
PROD_LOCKED=true
PROD_UNLOCK_UNTIL=
PROD_UNLOCK_REASON=
PROD_UNLOCK_BY=
LAST_MODIFIED=2026-01-18T22:00:00Z
```

**Rules:**
- All scripts check this file FIRST
- If `PROD_LOCKED=true`, refuse any operation targeting:
  - `/opt/leveredge/data-plane/prod/`
  - `n8n.leveredgeai.com` (without `dev.` prefix)
  - `studio.leveredgeai.com` (without `dev.` prefix)
  - `aria.leveredgeai.com` (without `dev.` prefix)
  - Production database direct connections

### Layer 2: Unlock Script

**File:** `/opt/leveredge/shared/scripts/unlock-prod.sh`

```bash
#!/bin/bash
# Temporarily unlock production access

set -e

LOCK_FILE="/opt/leveredge/.environment-lock"
LOG_FILE="/opt/leveredge/logs/prod-access.log"
MAX_DURATION=7200  # 2 hours max

usage() {
    echo "Usage: unlock-prod.sh <duration_minutes> <reason>"
    echo "  duration: 1-120 minutes"
    echo "  reason: Why you need prod access (quoted string)"
    echo ""
    echo "Example: unlock-prod.sh 30 'Deploying ARIA V3.2 hotfix'"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

DURATION=$1
REASON="${@:2}"

# Validate duration
if [ "$DURATION" -lt 1 ] || [ "$DURATION" -gt 120 ]; then
    echo "ERROR: Duration must be 1-120 minutes"
    exit 1
fi

# Calculate unlock expiry
UNLOCK_UNTIL=$(date -d "+${DURATION} minutes" -Iseconds)
CURRENT_USER=$(whoami)
TIMESTAMP=$(date -Iseconds)

# Update lock file
cat > "$LOCK_FILE" << EOF
# LeverEdge Environment Lock
# DO NOT EDIT MANUALLY - Use unlock-prod.sh

CURRENT_ENV=prod
PROD_LOCKED=false
PROD_UNLOCK_UNTIL=$UNLOCK_UNTIL
PROD_UNLOCK_REASON=$REASON
PROD_UNLOCK_BY=$CURRENT_USER
LAST_MODIFIED=$TIMESTAMP
EOF

# Log the access
echo "[$TIMESTAMP] PROD UNLOCKED by $CURRENT_USER for ${DURATION}m: $REASON" >> "$LOG_FILE"

echo "✅ Production UNLOCKED until $UNLOCK_UNTIL"
echo "⚠️  Remember to run 'lock-prod.sh' when done!"
echo ""
echo "Access logged to: $LOG_FILE"
```

**File:** `/opt/leveredge/shared/scripts/lock-prod.sh`

```bash
#!/bin/bash
# Re-lock production access

LOCK_FILE="/opt/leveredge/.environment-lock"
LOG_FILE="/opt/leveredge/logs/prod-access.log"
TIMESTAMP=$(date -Iseconds)

cat > "$LOCK_FILE" << EOF
# LeverEdge Environment Lock
# DO NOT EDIT MANUALLY - Use unlock-prod.sh

CURRENT_ENV=dev
PROD_LOCKED=true
PROD_UNLOCK_UNTIL=
PROD_UNLOCK_REASON=
PROD_UNLOCK_BY=
LAST_MODIFIED=$TIMESTAMP
EOF

echo "[$TIMESTAMP] PROD LOCKED" >> "$LOG_FILE"
echo "🔒 Production LOCKED. Default environment: DEV"
```

**File:** `/opt/leveredge/shared/scripts/check-env.sh`

```bash
#!/bin/bash
# Check current environment and lock status

LOCK_FILE="/opt/leveredge/.environment-lock"

if [ ! -f "$LOCK_FILE" ]; then
    echo "dev"  # Default to dev if no lock file
    exit 0
fi

source "$LOCK_FILE"

# Check if unlock has expired
if [ -n "$PROD_UNLOCK_UNTIL" ]; then
    EXPIRY=$(date -d "$PROD_UNLOCK_UNTIL" +%s 2>/dev/null || echo 0)
    NOW=$(date +%s)
    
    if [ "$NOW" -gt "$EXPIRY" ]; then
        # Auto-relock
        /opt/leveredge/shared/scripts/lock-prod.sh > /dev/null
        echo "dev"
        exit 0
    fi
fi

if [ "$PROD_LOCKED" = "true" ]; then
    echo "dev"
else
    echo "prod"
fi
```

### Layer 3: Claude Code EXECUTION_RULES.md Update

Add to `/home/damon/.claude/EXECUTION_RULES.md`:

```markdown
## ENVIRONMENT SAFETY RULES

### MANDATORY: Check Environment Before Operations

Before ANY operation that could affect production, you MUST:

1. Run: `source /opt/leveredge/.environment-lock`
2. Check: Is `PROD_LOCKED=true`?
3. If YES → Only operate on DEV paths
4. If NO → Check `PROD_UNLOCK_UNTIL` hasn't expired

### Protected Production Paths

NEVER modify these without explicit unlock:
- /opt/leveredge/data-plane/prod/*
- Any URL without "dev." prefix (n8n, studio, aria, api)
- Production database connections

### Safe DEV Paths

Always safe to modify:
- /opt/leveredge/data-plane/dev/*
- dev.*.leveredgeai.com
- Development database

### If User Requests Production Work

1. Check environment lock status
2. If locked, respond: "Production is locked. Run `unlock-prod.sh <minutes> '<reason>'` first."
3. NEVER bypass this check

### Visual Confirmation

When environment is DEV: ✅ DEV MODE (safe)
When environment is PROD: ⚠️ PROD MODE (expires: <time>)

Include this in responses when relevant.
```

### Layer 4: VS Code Workspace Separation

**File:** `/opt/leveredge/leveredge-dev.code-workspace`

```json
{
  "folders": [
    {
      "name": "DEV Data Plane",
      "path": "data-plane/dev"
    },
    {
      "name": "Control Plane",
      "path": "control-plane"
    },
    {
      "name": "Shared",
      "path": "shared"
    },
    {
      "name": "Docs",
      "path": "docs"
    },
    {
      "name": "Specs",
      "path": "specs"
    }
  ],
  "settings": {
    "terminal.integrated.env.linux": {
      "LEVEREDGE_ENV": "dev"
    },
    "window.title": "LeverEdge DEV - ${activeEditorShort}"
  }
}
```

**File:** `/opt/leveredge/leveredge-prod.code-workspace`

```json
{
  "folders": [
    {
      "name": "⚠️ PROD Data Plane ⚠️",
      "path": "data-plane/prod"
    }
  ],
  "settings": {
    "terminal.integrated.env.linux": {
      "LEVEREDGE_ENV": "prod"
    },
    "window.title": "⚠️ LeverEdge PROD ⚠️ - ${activeEditorShort}",
    "workbench.colorCustomizations": {
      "titleBar.activeBackground": "#8B0000",
      "titleBar.activeForeground": "#FFFFFF"
    }
  }
}
```

---

## HEPHAESTUS MCP Update

HEPHAESTUS must also enforce these rules. Update to:

1. Check `/opt/leveredge/.environment-lock` before any file operation
2. Refuse operations on prod paths if locked
3. Include environment status in responses

---

## Cron: Auto-Relock Check

Add to crontab:
```cron
# Check and auto-relock prod every 5 minutes
*/5 * * * * /opt/leveredge/shared/scripts/check-env.sh > /dev/null
```

---

## Usage Examples

### Normal DEV work (default)
```bash
# No unlock needed - DEV is always available
cd /opt/leveredge/data-plane/dev/aria-frontend
git pull && npm run build
```

### PROD deployment
```bash
# Step 1: Unlock with reason
unlock-prod.sh 30 "Deploying ARIA V3.2 to production"

# Step 2: Do the work
cd /opt/leveredge/data-plane/prod/aria-frontend
./promote-from-dev.sh

# Step 3: Relock immediately
lock-prod.sh
```

### Check current status
```bash
check-env.sh
# Output: dev  (or: prod)

cat /opt/leveredge/.environment-lock
# Shows full status including unlock reason
```

---

## Implementation GSD

```bash
# Create directory structure
mkdir -p /opt/leveredge/logs

# Create lock file (locked by default)
cat > /opt/leveredge/.environment-lock << 'EOF'
CURRENT_ENV=dev
PROD_LOCKED=true
PROD_UNLOCK_UNTIL=
PROD_UNLOCK_REASON=
PROD_UNLOCK_BY=
LAST_MODIFIED=$(date -Iseconds)
EOF

# Create scripts
# (Copy content from above into each file)

# Make executable
chmod +x /opt/leveredge/shared/scripts/unlock-prod.sh
chmod +x /opt/leveredge/shared/scripts/lock-prod.sh
chmod +x /opt/leveredge/shared/scripts/check-env.sh

# Create VS Code workspaces
# (Copy workspace files from above)

# Add cron job
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/leveredge/shared/scripts/check-env.sh > /dev/null") | crontab -

# Update EXECUTION_RULES.md
# (Add environment safety section)
```

---

## Success Criteria

- [ ] Lock file exists and defaults to DEV
- [ ] unlock-prod.sh requires reason and duration
- [ ] Auto-relock works after timeout
- [ ] Claude Code checks lock before operations
- [ ] HEPHAESTUS checks lock before operations
- [ ] VS Code workspaces created
- [ ] Prod workspace has red title bar
- [ ] All prod access is logged
