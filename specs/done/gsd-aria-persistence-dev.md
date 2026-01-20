# GSD: ARIA Persistence - Cross-Device Message Sync (DEV FIRST)

**Priority:** HIGH
**Estimated Time:** 10-15 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Make ARIA conversations sync across web and mobile. **BUILD IN DEV FIRST, TEST, THEN PROMOTE.**

**Prerequisites DONE:**
- ✅ `aria_unified_conversations` table (from unified-threading)
- ✅ `aria_unified_messages` table (from unified-threading)
- ✅ `aria-memory` service at port 8114

---

## CRITICAL: DEV-FIRST WORKFLOW

```
1. All changes go to /opt/leveredge/data-plane/dev/aria-frontend/
2. Test at dev.aria.leveredgeai.com
3. Only after verification: ./promote-aria-to-prod.sh
```

**DO NOT TOUCH /data-plane/prod/ DIRECTLY.**

---

## DELIVERABLES

- [ ] DEV frontend uses Supabase instead of local state
- [ ] Real-time sync via Supabase subscriptions
- [ ] Test on dev.aria.leveredgeai.com
- [ ] Promote to prod after verification

---

## PHASE 1: DATABASE (DEV Supabase)

Apply to DEV Supabase first:

```sql
-- Add device_id to messages for duplicate prevention
ALTER TABLE aria_unified_messages 
ADD COLUMN IF NOT EXISTS device_id TEXT;

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_unified_messages_conversation 
ON aria_unified_messages(conversation_id, created_at);

-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_conversations;

-- RLS policies
ALTER TABLE aria_unified_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE aria_unified_conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own conversations" ON aria_unified_conversations
  FOR SELECT USING (true);
  
CREATE POLICY "Users can insert own conversations" ON aria_unified_conversations
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can read own messages" ON aria_unified_messages
  FOR SELECT USING (true);
  
CREATE POLICY "Users can insert own messages" ON aria_unified_messages
  FOR INSERT WITH CHECK (true);
```

---

## PHASE 2: DEV FRONTEND CHANGES

**Location: `/opt/leveredge/data-plane/dev/aria-frontend/`**

### 2.1 Add User Identity Module

Create `src/lib/userIdentity.ts`:
```typescript
export const getUserId = (): string => {
  let userId = localStorage.getItem('aria_user_id');
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem('aria_user_id', userId);
  }
  return userId;
};

export const getDeviceId = (): string => {
  let deviceId = localStorage.getItem('aria_device_id');
  if (!deviceId) {
    deviceId = crypto.randomUUID();
    localStorage.setItem('aria_device_id', deviceId);
  }
  return deviceId;
};

export const linkDevice = (existingUserId: string): void => {
  localStorage.setItem('aria_user_id', existingUserId);
};
```

### 2.2 Update Supabase Client

Add to `src/lib/supabase.ts`:
```typescript
export interface UnifiedMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  device_id?: string;
  created_at: string;
}

export const subscribeToMessages = (
  conversationId: string, 
  onMessage: (msg: UnifiedMessage) => void
) => {
  return supabase
    .channel(`messages:${conversationId}`)
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'aria_unified_messages',
      filter: `conversation_id=eq.${conversationId}`
    }, (payload) => {
      onMessage(payload.new as UnifiedMessage);
    })
    .subscribe();
};
```

### 2.3 Update Store

Modify `src/store/useStore.ts` to:
1. Load conversation from Supabase on init
2. Subscribe to real-time updates
3. Save messages to Supabase (not just local state)
4. Filter out messages from same device_id

---

## PHASE 3: TEST IN DEV

```bash
# Build DEV
cd /opt/leveredge/data-plane/dev/aria-frontend
npm install
npm run build

# Restart DEV services
docker compose restart caddy  # or however DEV is served

# Test at dev.aria.leveredgeai.com
# 1. Send message in browser
# 2. Open in incognito/different browser with same user_id
# 3. Verify message appears
# 4. Send reply, verify sync
```

---

## PHASE 4: PROMOTE TO PROD

**Only after DEV verification passes:**

```bash
cd /opt/leveredge
./shared/scripts/promote-aria-to-prod.sh
```

This script handles:
- Schema sync
- Code copy
- Build
- Smoke tests
- Rollback if failed

---

## VERIFICATION

```bash
# DEV test
curl "https://dev-supabase.leveredgeai.com/rest/v1/aria_unified_messages?select=*&limit=5" \
  -H "apikey: $DEV_SUPABASE_ANON_KEY"

# After promotion, PROD test
curl "https://supabase.leveredgeai.com/rest/v1/aria_unified_messages?select=*&limit=5" \
  -H "apikey: $SUPABASE_ANON_KEY"
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-aria-persistence-dev.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ARIA Persistence complete (DEV-FIRST): Messages sync across devices via Supabase real-time",
    "domain": "ARIA",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "aria", "persistence", "dev-first"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: ARIA persistence - cross-device sync (DEV-FIRST)

- User identity system
- Supabase real-time subscriptions  
- Device linking for multi-device
- Tested in DEV before promotion"
```

---

## ROLLBACK

```bash
# If DEV breaks
cd /opt/leveredge/data-plane/dev/aria-frontend
git checkout HEAD~1 -- src/

# If PROD breaks after promotion
curl -X POST http://localhost:8008/rollback  # HADES
```

---

*DEV FIRST. ALWAYS.*
