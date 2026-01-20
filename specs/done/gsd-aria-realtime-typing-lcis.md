# GSD: Fix ARIA Real-Time + Typing Indicator + Start LCIS

**Priority:** CRITICAL
**Estimated Time:** 20-30 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Three fixes:
1. **Real-time sync actually works** (no refresh needed)
2. **Typing indicator** shows when ARIA is responding
3. **Start LCIS** so system learns from issues

---

## ENVIRONMENT

**Target:** DEV FIRST

```
Frontend: /opt/leveredge/data-plane/dev/aria-frontend/
Test URL: dev-aria.leveredgeai.com
```

---

## PART 1: START LCIS AND FLEET

LCIS isn't running. Nothing is being learned.

```bash
cd /opt/leveredge

# Start the fleet (or at minimum, LCIS)
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d lcis-librarian lcis-oracle event-bus

# Verify
docker ps | grep -E "lcis|event-bus"

# Check health
curl http://localhost:8050/health
curl http://localhost:8052/health
```

---

## PART 2: FIX REAL-TIME SYNC

The subscription fires but React doesn't re-render. Common causes:
1. State mutation instead of new array
2. Subscription outside React lifecycle
3. Supabase realtime not enabled on table

### 2.1 Verify Supabase Realtime (Database)

```sql
-- Connect to DEV Supabase and run:

-- Check if realtime is enabled
SELECT schemaname, tablename 
FROM pg_publication_tables 
WHERE pubname = 'supabase_realtime';

-- If aria_unified_messages NOT listed, add it:
ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_messages;

-- Verify RLS allows reads
SELECT * FROM pg_policies WHERE tablename = 'aria_unified_messages';
```

### 2.2 Fix React State Update

The issue is likely mutating state instead of creating new array. Update `useStore.ts`:

```typescript
// WRONG - mutates existing array
messages.push(newMessage);
setMessages(messages);

// RIGHT - creates new array, triggers re-render
setMessages(prev => [...prev, newMessage]);
```

**Full fix for real-time handler:**

```typescript
// In useStore.ts - the real-time message handler

const handleRealtimeMessage = useCallback((payload: any) => {
  const newMessage = payload.new as UnifiedMessage;
  
  console.log('🔔 Real-time received:', newMessage);
  
  // Skip if from this device (we already have it)
  const myDeviceId = localStorage.getItem('aria_device_id');
  if (newMessage.device_id === myDeviceId) {
    console.log('⏭️ Skipping own message');
    return;
  }
  
  // CRITICAL: Use functional update to ensure fresh state
  set((state) => {
    // Check for duplicates
    const exists = state.messages.some(m => m.id === newMessage.id);
    if (exists) {
      console.log('⏭️ Duplicate, skipping');
      return state;
    }
    
    console.log('✅ Adding message to state');
    return {
      ...state,
      messages: [...state.messages, {
        id: newMessage.id,
        role: newMessage.role as 'user' | 'assistant',
        content: newMessage.content,
        timestamp: new Date(newMessage.created_at)
      }]
    };
  });
}, [set]);
```

### 2.3 Ensure Subscription Persists

```typescript
// subscription setup - must be in useEffect with proper cleanup

useEffect(() => {
  let channel: RealtimeChannel | null = null;
  let mounted = true;

  const setup = async () => {
    const userId = getUserId();
    const convId = await getOrCreateConversation(userId);
    
    if (!mounted) return;
    
    channel = supabase
      .channel(`realtime:messages:${convId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'aria_unified_messages',
          filter: `conversation_id=eq.${convId}`
        },
        handleRealtimeMessage
      )
      .subscribe((status, err) => {
        console.log('📡 Subscription status:', status);
        if (err) console.error('Subscription error:', err);
      });
  };

  setup();

  return () => {
    mounted = false;
    if (channel) {
      console.log('🔌 Cleaning up subscription');
      supabase.removeChannel(channel);
    }
  };
}, [handleRealtimeMessage]);
```

---

## PART 3: TYPING INDICATOR

### 3.1 Add Typing State

```typescript
// In store or component state
const [isTyping, setIsTyping] = useState(false);
```

### 3.2 Create Typing Bubble Component

Create `src/components/TypingIndicator.tsx`:

```tsx
import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-start gap-3 mb-4">
      {/* ARIA avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-sm font-bold">
        A
      </div>
      
      {/* Typing dots */}
      <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-none px-4 py-3">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
};
```

### 3.3 Add CSS Animation (if not using Tailwind animate)

```css
/* In globals.css */
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

.animate-bounce {
  animation: bounce 1s infinite;
}
```

### 3.4 Use in Chat Component

```tsx
// In the chat messages list
{messages.map(msg => (
  <MessageBubble key={msg.id} message={msg} />
))}

{/* Show typing indicator when waiting for response */}
{isTyping && <TypingIndicator />}
```

### 3.5 Toggle Typing State

```typescript
// When sending message
const sendMessage = async (content: string) => {
  // Add user message
  addMessage({ role: 'user', content });
  
  // Show typing indicator
  setIsTyping(true);
  
  try {
    // Call ARIA API
    const response = await fetch('/api/chat', { ... });
    const data = await response.json();
    
    // Add ARIA response
    addMessage({ role: 'assistant', content: data.response });
  } finally {
    // Hide typing indicator
    setIsTyping(false);
  }
};
```

---

## PART 4: LOG THIS ISSUE TO LCIS

After LCIS is running, log this lesson:

```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "React real-time sync failure: State mutation instead of new array. WRONG: messages.push(x); setMessages(messages). RIGHT: setMessages(prev => [...prev, x]). Must use functional update for React to detect change.",
    "domain": "FRONTEND",
    "type": "failure",
    "source_agent": "CLAUDE_CODE",
    "tags": ["react", "realtime", "supabase", "state"],
    "prevention": "Always use functional state updates with spread operator for arrays"
  }'
```

---

## VERIFICATION

```bash
# 1. LCIS running
docker ps | grep lcis

# 2. Open dev-aria in Chrome, open Console
# 3. Open dev-aria in Firefox (same user_id)
# 4. Send message in Chrome
# 5. Watch Firefox console for "🔔 Real-time received"
# 6. Message should appear WITHOUT refresh
# 7. When sending, typing indicator should show
```

---

## PHASE 5: PROMOTE TO PROD

```bash
# Only after DEV verification
cd /opt/leveredge
./shared/scripts/promote-aria-to-prod.sh
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-aria-realtime-typing-lcis.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ARIA real-time sync fixed: functional state updates, typing indicator added, LCIS started",
    "domain": "ARIA",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "aria", "realtime", "typing"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "fix: ARIA real-time sync + typing indicator

- Fixed React state mutation bug (use functional updates)
- Added typing indicator component
- Started LCIS for learning
- Verified Supabase realtime enabled

Messages now sync INSTANTLY across devices."
```

---

## ROLLBACK

```bash
cd /opt/leveredge/data-plane/dev/aria-frontend
git checkout HEAD~1 -- src/
```

---

*Real-time means instant. Not refresh. Not eventually. INSTANT.*
