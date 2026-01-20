# GSD: ARIA Version Awareness + Real-Time Sync Fix

**Priority:** HIGH
**Estimated Time:** 15-20 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Two fixes:
1. ARIA can tell users her version when asked
2. Cross-device messages appear instantly (no refresh needed)

---

## ENVIRONMENT

**Target:** DEV FIRST

```
Backend: /opt/leveredge/control-plane/agents/aria-chat/
Frontend: /opt/leveredge/data-plane/dev/aria-frontend/
Test URL: dev-aria.leveredgeai.com
```

⚠️ **NEVER modify /data-plane/prod/ directly.**

---

## DELIVERABLES

- [ ] Update system prompt with version 4.1.0
- [ ] Add VERSION INFO section to prompt
- [ ] Fix real-time subscription to auto-append messages
- [ ] No refresh required for cross-device sync
- [ ] Test in DEV
- [ ] Promote to PROD

---

## PHASE 1: VERSION AWARENESS (Backend)

### 1.1 Update System Prompt Header

```bash
cd /opt/leveredge/control-plane/agents/aria-chat/prompts

# Update version
sed -i 's/Version: 4.0/Version: 4.1.0 (Persistence)/g' aria_system_prompt.txt
sed -i 's/January 18, 2026/January 20, 2026/g' aria_system_prompt.txt
```

### 1.2 Add Version Section to Prompt

Add after the IDENTITY section in `aria_system_prompt.txt`:

```markdown
## VERSION INFO

**Current Version:** 4.1.0 (Persistence)
**Released:** January 20, 2026

When asked about your version, capabilities, or what's new:
- Version: 4.1.0 codename "Persistence"
- Key features: Cross-device message sync, unified threading, real-time updates
- You can dispatch tasks to 30+ specialized agents via HEPHAESTUS
- You remember facts and preferences via memory-v2
- Full changelog at /opt/leveredge/ARIA-VERSION.md

Example response: "I'm ARIA v4.1.0 'Persistence' — just updated today! I now sync our conversations across all your devices in real-time. Send me a message on your phone, it appears here instantly. 💫"
```

---

## PHASE 2: REAL-TIME SYNC FIX (Frontend DEV)

The issue: Supabase subscription receives the message but UI doesn't update without refresh.

### 2.1 Debug Current Implementation

Check if subscription is firing:

```typescript
// In src/store/useStore.ts or wherever subscription lives
// Add console.log to verify messages arrive

.on('postgres_changes', {
  event: 'INSERT',
  schema: 'public',
  table: 'aria_unified_messages',
  filter: `conversation_id=eq.${conversationId}`
}, (payload) => {
  console.log('🔔 Real-time message received:', payload.new);  // ADD THIS
  onMessage(payload.new as UnifiedMessage);
})
```

### 2.2 Fix State Update

The problem is likely that the state update isn't triggering a re-render. Fix:

```typescript
// In the subscription callback, ensure we're updating state correctly
const handleRealtimeMessage = (newMessage: UnifiedMessage) => {
  // Skip if from this device
  if (newMessage.device_id === getDeviceId()) {
    console.log('Skipping own message');
    return;
  }
  
  // CRITICAL: Use setState with callback to ensure fresh state
  setMessages((prevMessages) => {
    // Check if message already exists (prevent duplicates)
    if (prevMessages.some(m => m.id === newMessage.id)) {
      return prevMessages;
    }
    // Append new message
    return [...prevMessages, {
      id: newMessage.id,
      role: newMessage.role as 'user' | 'assistant',
      content: newMessage.content,
      timestamp: new Date(newMessage.created_at)
    }];
  });
};
```

### 2.3 Ensure Subscription Stays Alive

```typescript
// Make sure subscription is set up ONCE and persists
useEffect(() => {
  let channel: RealtimeChannel | null = null;
  
  const setupSubscription = async () => {
    const convId = await getOrCreateConversation(getUserId());
    
    channel = supabase
      .channel(`messages:${convId}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'aria_unified_messages',
        filter: `conversation_id=eq.${convId}`
      }, handleRealtimeMessage)
      .subscribe((status) => {
        console.log('Subscription status:', status);
      });
  };
  
  setupSubscription();
  
  // Cleanup on unmount
  return () => {
    if (channel) {
      supabase.removeChannel(channel);
    }
  };
}, []); // Empty deps = run once
```

### 2.4 Verify Supabase Realtime is Enabled

```sql
-- Check if table is in realtime publication
SELECT * FROM pg_publication_tables WHERE tablename = 'aria_unified_messages';

-- If not, add it
ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_messages;
```

---

## PHASE 3: TEST IN DEV

```bash
# Build DEV frontend
cd /opt/leveredge/data-plane/dev/aria-frontend
npm run build

# Restart
# (however DEV is served)

# Test:
# 1. Open dev-aria.leveredgeai.com in Chrome
# 2. Open dev-aria.leveredgeai.com in Firefox (same user_id)
# 3. Send message in Chrome
# 4. Firefox should show message INSTANTLY (no refresh)
# 5. Reply in Firefox
# 6. Chrome should show reply INSTANTLY
```

---

## PHASE 4: PROMOTE TO PROD

```bash
cd /opt/leveredge
./shared/scripts/promote-aria-to-prod.sh
```

---

## VERIFICATION

```bash
# Check version in health endpoint
curl https://dev-aria-api.leveredgeai.com/health | jq '.version'

# Check realtime is enabled
# In Supabase dashboard: Database > Replication > Check aria_unified_messages is listed

# Manual test: Open two browsers, send messages, verify instant sync
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-aria-version-realtime.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ARIA v4.1.0: Version awareness added, real-time sync fixed. Messages now appear instantly across devices.",
    "domain": "ARIA",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "aria", "version", "realtime"]
  }'
```

### 3. Update ARIA-VERSION.md
Add note about realtime fix to v4.1.0 changelog.

### 4. Git Commit
```bash
git add -A
git commit -m "feat: ARIA v4.1.0 - Version awareness + real-time sync fix

- System prompt now includes version info
- ARIA can answer 'what version are you?'
- Fixed real-time subscription state updates
- Messages appear instantly across devices (no refresh)

Tested in DEV before promotion."
```

---

## ROLLBACK

```bash
# DEV
cd /opt/leveredge/data-plane/dev/aria-frontend
git checkout HEAD~1 -- src/

# System prompt
cd /opt/leveredge/control-plane/agents/aria-chat/prompts
git checkout HEAD~1 -- aria_system_prompt.txt
```

---

*Real-time means REAL-TIME. No refresh bullshit.*
