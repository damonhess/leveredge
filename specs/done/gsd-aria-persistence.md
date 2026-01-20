# GSD: ARIA Persistence - Cross-Device Message Sync

**Priority:** HIGH
**Estimated Time:** 2-4 hours (unified-threading did the heavy lifting)
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Make ARIA conversations sync across web and mobile. When you send a message on your phone, it appears on web. When you respond on web, it appears on phone.

**Prerequisites DONE:**
- ✅ `aria_unified_conversations` table (from unified-threading)
- ✅ `aria_unified_messages` table (from unified-threading)
- ✅ `aria-memory` service at port 8114

---

## DELIVERABLES

- [ ] User identification (device fingerprint or simple auth)
- [ ] Web frontend uses Supabase instead of local state
- [ ] Mobile frontend uses Supabase instead of local state
- [ ] Real-time sync via Supabase subscriptions
- [ ] Conversation list loads from database
- [ ] Messages persist and sync instantly

---

## PHASE 1: USER IDENTIFICATION

We need to know it's the same user on both devices. Options:

### Option A: Simple Device Linking (Recommended for MVP)
Generate a user_id, store in localStorage/AsyncStorage. User manually enters same ID on both devices once.

```typescript
// On first launch, generate or prompt for user_id
const getUserId = () => {
  let userId = localStorage.getItem('aria_user_id');
  if (!userId) {
    userId = prompt('Enter your ARIA user ID (or leave blank for new):');
    if (!userId) {
      userId = crypto.randomUUID();
    }
    localStorage.setItem('aria_user_id', userId);
  }
  return userId;
};
```

### Option B: Magic Link Auth
Use Supabase Auth with magic links - more secure, more setup.

**DECISION: Start with Option A, upgrade later if needed.**

---

## PHASE 2: WEB FRONTEND CHANGES

Location: `/opt/leveredge/data-plane/prod/aria-frontend/`

### 2.1 Add Supabase Client

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

### 2.2 Replace Local State with Supabase

Update the store to load/save from database:

```typescript
// In useStore.ts or equivalent

// Load conversations on init
const loadConversations = async (userId: string) => {
  const { data } = await supabase
    .from('aria_unified_conversations')
    .select('*')
    .eq('user_id', userId)
    .order('updated_at', { ascending: false });
  return data;
};

// Load messages for a conversation
const loadMessages = async (conversationId: string) => {
  const { data } = await supabase
    .from('aria_unified_messages')
    .select('*')
    .eq('conversation_id', conversationId)
    .order('created_at', { ascending: true });
  return data;
};

// Save message (called after sending)
const saveMessage = async (conversationId: string, role: string, content: string) => {
  const { data } = await supabase
    .from('aria_unified_messages')
    .insert({
      conversation_id: conversationId,
      role,
      content,
      created_at: new Date().toISOString()
    })
    .select()
    .single();
  return data;
};
```

### 2.3 Add Real-Time Subscription

```typescript
// Subscribe to new messages
const subscribeToMessages = (conversationId: string, onMessage: (msg) => void) => {
  return supabase
    .channel(`messages:${conversationId}`)
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'aria_unified_messages',
      filter: `conversation_id=eq.${conversationId}`
    }, (payload) => {
      onMessage(payload.new);
    })
    .subscribe();
};
```

### 2.4 Update Chat Component

```typescript
// On mount
useEffect(() => {
  const userId = getUserId();
  loadConversations(userId).then(setConversations);
  
  // Subscribe to conversation updates
  const channel = subscribeToMessages(currentConversationId, (msg) => {
    // Add message to local state if not from this device
    if (msg.device_id !== getDeviceId()) {
      addMessageToState(msg);
    }
  });
  
  return () => channel.unsubscribe();
}, [currentConversationId]);
```

---

## PHASE 3: MOBILE FRONTEND CHANGES

Location: `/opt/leveredge/data-plane/prod/aria-mobile/` (or wherever mobile code is)

Same changes as web:
1. Add Supabase client
2. Replace AsyncStorage with Supabase calls
3. Add real-time subscription
4. Handle offline gracefully (queue messages, sync when online)

---

## PHASE 4: ARIA-MEMORY SERVICE INTEGRATION

The `aria-memory` service (port 8114) already handles the database. Ensure frontends call it OR go direct to Supabase.

**Option A: Direct Supabase** (simpler, recommended)
- Frontends talk directly to Supabase
- Real-time works out of the box

**Option B: Through aria-memory API**
- More control, can add business logic
- Need to add WebSocket support for real-time

**DECISION: Direct Supabase for MVP.**

---

## PHASE 5: ENVIRONMENT VARIABLES

Add to both frontends:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

For PROD:
```env
NEXT_PUBLIC_SUPABASE_URL=https://supabase.leveredgeai.com
NEXT_PUBLIC_SUPABASE_ANON_KEY=<from AEGIS>
```

---

## PHASE 6: DATABASE ADJUSTMENTS

Add device tracking to prevent duplicate display:

```sql
-- Add device_id to messages
ALTER TABLE aria_unified_messages 
ADD COLUMN IF NOT EXISTS device_id TEXT;

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_unified_messages_conversation 
ON aria_unified_messages(conversation_id, created_at);

-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_conversations;
```

---

## VERIFICATION

```bash
# 1. Open ARIA on web, send "test message 1"
# 2. Open ARIA on phone, should see "test message 1"
# 3. Reply on phone with "test message 2"
# 4. Web should show "test message 2" in real-time

# Check database has messages
curl "https://supabase.leveredgeai.com/rest/v1/aria_unified_messages?select=*&limit=5" \
  -H "apikey: $SUPABASE_ANON_KEY"
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-aria-persistence.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ARIA Persistence complete: Messages now sync across web and mobile via Supabase real-time subscriptions",
    "domain": "ARIA",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "aria", "persistence", "sync"]
  }'
```

### 3. Update GSD-TRACKER.md
```markdown
| `gsd-aria-persistence.md` | Cross-device message sync | Supabase real-time + frontend rewrites |
```

### 4. Git Commit
```bash
git add -A
git commit -m "feat: ARIA persistence - cross-device message sync

- Web frontend uses Supabase instead of local storage
- Mobile frontend uses Supabase
- Real-time sync via Supabase subscriptions
- User linking via shared user_id

Messages now appear on all devices instantly."
```

---

## ROLLBACK

```bash
# Revert frontend to local storage
git checkout HEAD~1 -- data-plane/prod/aria-frontend/
git checkout HEAD~1 -- data-plane/prod/aria-mobile/

# Rebuild
cd /opt/leveredge/data-plane/prod/aria-frontend && npm run build
```

---

*Unified-threading did 80% of this work. Now we just wire it up.*
