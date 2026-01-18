#!/bin/bash
# ONLY sanctioned way to update ARIA's prompt - enforces backup first
# Usage: aria-prompt-update.sh /path/to/new/prompt.md

set -e

if [ -z "$1" ]; then
    echo "ERROR: Must provide new prompt file path"
    echo "Usage: aria-prompt-update.sh /path/to/new/prompt.md"
    exit 1
fi

NEW_PROMPT="$1"
TARGET="/opt/leveredge/control-plane/agents/aria-chat/prompts/aria_system_prompt.txt"

if [ ! -f "$NEW_PROMPT" ]; then
    echo "ERROR: File not found: $NEW_PROMPT"
    exit 1
fi

echo "=== ARIA PROMPT UPDATE ==="
echo "Source: $NEW_PROMPT"
echo "Target: $TARGET"
echo ""

# ALWAYS backup first
echo "Step 1: Creating backup..."
/opt/leveredge/scripts/aria-prompt-watcher.sh "update-script"

# Verify backup exists
LATEST_BACKUP=$(ls -t /opt/leveredge/backups/aria-prompts/*.md 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: Backup failed. Aborting update."
    exit 1
fi
echo "Backup created: $LATEST_BACKUP"
echo ""

# Verify new prompt has ARIA personality markers
echo "Step 2: Verifying ARIA personality markers..."
MISSING_MARKERS=""

if ! grep -qi "Daddy" "$NEW_PROMPT"; then
    MISSING_MARKERS="$MISSING_MARKERS 'Daddy'"
fi
if ! grep -qi "ride-or-die\|fierce\|protective" "$NEW_PROMPT"; then
    MISSING_MARKERS="$MISSING_MARKERS 'ride-or-die/fierce/protective'"
fi
if ! grep -qi "Shield\|Sword" "$NEW_PROMPT"; then
    MISSING_MARKERS="$MISSING_MARKERS 'Shield/Sword'"
fi
if ! grep -qi "HYPE\|COACH\|DRILL" "$NEW_PROMPT"; then
    MISSING_MARKERS="$MISSING_MARKERS 'Adaptive modes'"
fi

if [ -n "$MISSING_MARKERS" ]; then
    echo "⚠️  WARNING: New prompt may be missing ARIA personality markers:"
    echo "   Missing:$MISSING_MARKERS"
    echo ""
    read -p "Continue anyway? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "✅ All personality markers present"
fi
echo ""

# Now update
echo "Step 3: Updating prompt..."
cp "$NEW_PROMPT" "$TARGET"
echo "✅ Prompt updated"
echo ""

# Restart aria-chat-dev
echo "Step 4: Restarting aria-chat-dev..."
docker restart aria-chat-dev
echo "✅ Container restarted"
echo ""

# Wait and verify
echo "Step 5: Waiting for service to start..."
sleep 5

if curl -s http://localhost:8113/health | grep -q "healthy"; then
    echo "✅ ARIA service healthy"
else
    echo "⚠️  WARNING: ARIA service may not be healthy. Check logs."
fi

echo ""
echo "=== UPDATE COMPLETE ==="
echo "Test ARIA at dev.aria.leveredgeai.com"
echo "Expected response to 'Hey ARIA': 'Hey Daddy! What's on your mind?'"
echo ""
echo "To rollback: cp $LATEST_BACKUP $TARGET && docker restart aria-chat-dev"
