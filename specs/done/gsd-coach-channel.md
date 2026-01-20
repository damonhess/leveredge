# GSD: Coach Channel - Claude↔Claude Communication

**Priority:** HIGH
**Time:** ~15 min
**Purpose:** Enable Claude Web to communicate with Claude Code in real-time

---

## THE VISION

Two Claude instances, one mission:

- **Claude Web (LAUNCH_COACH)** - Strategy, oversight, accountability
- **Claude Code (BUILDER)** - Execution, implementation, debugging

They communicate through a shared channel. Launch Coach can:
- Send instructions to Claude Code
- Review Claude Code's work
- Provide feedback in real-time
- Coordinate complex multi-step builds

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Claude Web                              Claude Code            │
│  (Launch Coach)                          (Builder)              │
│       │                                       │                 │
│       ▼                                       ▼                 │
│  HEPHAESTUS MCP                         Claude Code MCP         │
│       │                                       │                 │
│       ▼                                       ▼                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   COACH CHANNEL                          │   │
│  │                                                          │   │
│  │  coach_channel table (Supabase)                         │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │ id | from | to | message | status | created_at     │ │   │
│  │  │ 1  | COACH| CODE| "Run gsd..."| pending | ...      │ │   │
│  │  │ 2  | CODE | COACH| "Done..."  | read    | ...      │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  Event Bus notifications (optional real-time)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: DATABASE SCHEMA

```sql
-- ============================================
-- COACH CHANNEL
-- ============================================
CREATE TABLE IF NOT EXISTS coach_channel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Participants
    from_agent VARCHAR(50) NOT NULL,  -- LAUNCH_COACH, CLAUDE_CODE, etc.
    to_agent VARCHAR(50) NOT NULL,    -- LAUNCH_COACH, CLAUDE_CODE, ALL
    
    -- Message
    message_type VARCHAR(50) NOT NULL,  -- instruction, response, status, question, feedback
    subject VARCHAR(255),
    content TEXT NOT NULL,
    
    -- Context
    context JSONB DEFAULT '{}',  -- Additional structured data
    reference_id VARCHAR(255),   -- Link to GSD, meeting, task, etc.
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, read, acknowledged, completed
    read_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    
    -- Threading
    thread_id UUID,  -- Group related messages
    reply_to UUID REFERENCES coach_channel(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_coach_to ON coach_channel(to_agent, status);
CREATE INDEX idx_coach_from ON coach_channel(from_agent);
CREATE INDEX idx_coach_thread ON coach_channel(thread_id);
CREATE INDEX idx_coach_created ON coach_channel(created_at DESC);

-- ============================================
-- ACTIVE SESSIONS
-- ============================================
CREATE TABLE IF NOT EXISTS coach_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_name VARCHAR(255),
    
    -- Participants
    coach_agent VARCHAR(50) DEFAULT 'LAUNCH_COACH',
    builder_agent VARCHAR(50) DEFAULT 'CLAUDE_CODE',
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, completed
    
    -- Context
    current_task VARCHAR(500),
    gsd_path VARCHAR(500),
    notes TEXT,
    
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================
CREATE OR REPLACE FUNCTION coach_unread_count(agent_name VARCHAR)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER 
    FROM coach_channel 
    WHERE to_agent = agent_name 
    AND status = 'pending';
$$ LANGUAGE SQL;
```

---

## PHASE 2: HEPHAESTUS MCP TOOLS (for Claude Web)

Add to HEPHAESTUS MCP server:

```python
# ============ COACH CHANNEL TOOLS ============

@tool
async def coach_send(
    message: str,
    message_type: str = "instruction",
    subject: str = None,
    to_agent: str = "CLAUDE_CODE",
    reference_id: str = None,
    context: dict = None
):
    """
    Send a message to Claude Code (or other agent).
    
    message_type options:
    - instruction: Tell Claude Code what to do
    - question: Ask Claude Code something
    - feedback: Provide feedback on work done
    - status: Share status update
    """
    async with get_db_pool().acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO coach_channel 
            (from_agent, to_agent, message_type, subject, content, reference_id, context)
            VALUES ('LAUNCH_COACH', $1, $2, $3, $4, $5, $6)
            RETURNING id, created_at
        """, to_agent, message_type, subject, message, reference_id, 
            json.dumps(context) if context else '{}')
        
        # Publish to Event Bus for real-time notification
        await publish_event("coach.message_sent", {
            "message_id": str(row['id']),
            "to": to_agent,
            "type": message_type,
            "subject": subject
        })
        
        return {
            "status": "sent",
            "message_id": str(row['id']),
            "to": to_agent,
            "created_at": row['created_at'].isoformat()
        }


@tool
async def coach_receive(
    limit: int = 10,
    status: str = "pending",
    mark_read: bool = True
):
    """
    Receive messages sent to LAUNCH_COACH.
    """
    async with get_db_pool().acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, from_agent, message_type, subject, content, 
                   context, reference_id, status, created_at
            FROM coach_channel
            WHERE to_agent = 'LAUNCH_COACH'
            AND ($1 = 'all' OR status = $1)
            ORDER BY created_at DESC
            LIMIT $2
        """, status, limit)
        
        messages = [dict(r) for r in rows]
        
        # Mark as read if requested
        if mark_read and messages:
            message_ids = [m['id'] for m in messages if m['status'] == 'pending']
            if message_ids:
                await conn.execute("""
                    UPDATE coach_channel
                    SET status = 'read', read_at = NOW()
                    WHERE id = ANY($1::uuid[])
                """, message_ids)
        
        return {
            "messages": messages,
            "count": len(messages),
            "unread_remaining": await conn.fetchval(
                "SELECT coach_unread_count('LAUNCH_COACH')"
            )
        }


@tool
async def coach_thread(thread_id: str):
    """Get all messages in a conversation thread."""
    async with get_db_pool().acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, from_agent, to_agent, message_type, subject, 
                   content, status, created_at
            FROM coach_channel
            WHERE thread_id = $1::uuid
            ORDER BY created_at ASC
        """, thread_id)
        
        return {
            "thread_id": thread_id,
            "messages": [dict(r) for r in rows],
            "count": len(rows)
        }


@tool
async def coach_status():
    """Get coach channel status - unread counts, active sessions."""
    async with get_db_pool().acquire() as conn:
        unread = await conn.fetchval("SELECT coach_unread_count('LAUNCH_COACH')")
        
        recent = await conn.fetch("""
            SELECT from_agent, message_type, subject, created_at
            FROM coach_channel
            WHERE to_agent = 'LAUNCH_COACH'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        session = await conn.fetchrow("""
            SELECT * FROM coach_sessions
            WHERE status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
        """)
        
        return {
            "unread_messages": unread,
            "recent_messages": [dict(r) for r in recent],
            "active_session": dict(session) if session else None
        }
```

---

## PHASE 3: CLAUDE CODE MCP TOOLS

For Claude Code's MCP config, add these tools:

```python
# ============ COACH CHANNEL TOOLS (Claude Code side) ============

@tool
async def coach_receive_instructions(
    limit: int = 10,
    mark_read: bool = True
):
    """
    Check for instructions from Launch Coach.
    Call this at the start of sessions and periodically.
    """
    async with get_db_pool().acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, from_agent, message_type, subject, content, 
                   context, reference_id, created_at
            FROM coach_channel
            WHERE to_agent = 'CLAUDE_CODE'
            AND status = 'pending'
            ORDER BY created_at ASC
            LIMIT $1
        """, limit)
        
        messages = [dict(r) for r in rows]
        
        if mark_read and messages:
            await conn.execute("""
                UPDATE coach_channel
                SET status = 'read', read_at = NOW()
                WHERE id = ANY($1::uuid[])
            """, [m['id'] for m in messages])
        
        return {
            "instructions": messages,
            "count": len(messages),
            "coach_says": messages[0]['content'] if messages else "No pending instructions"
        }


@tool
async def coach_respond(
    message: str,
    message_type: str = "response",
    subject: str = None,
    reply_to: str = None,
    context: dict = None
):
    """
    Send a response back to Launch Coach.
    
    message_type options:
    - response: Answer to instruction/question
    - status: Progress update
    - question: Ask coach for clarification
    - completed: Task finished
    """
    async with get_db_pool().acquire() as conn:
        # Get thread_id from reply_to if provided
        thread_id = None
        if reply_to:
            original = await conn.fetchrow(
                "SELECT thread_id FROM coach_channel WHERE id = $1::uuid",
                reply_to
            )
            thread_id = original['thread_id'] if original else None
        
        row = await conn.fetchrow("""
            INSERT INTO coach_channel 
            (from_agent, to_agent, message_type, subject, content, 
             reply_to, thread_id, context)
            VALUES ('CLAUDE_CODE', 'LAUNCH_COACH', $1, $2, $3, $4::uuid, $5::uuid, $6)
            RETURNING id
        """, message_type, subject, message, reply_to, thread_id,
            json.dumps(context) if context else '{}')
        
        return {
            "status": "sent",
            "message_id": str(row['id']),
            "to": "LAUNCH_COACH"
        }


@tool
async def coach_acknowledge(message_id: str, notes: str = None):
    """Acknowledge receipt of an instruction."""
    async with get_db_pool().acquire() as conn:
        await conn.execute("""
            UPDATE coach_channel
            SET status = 'acknowledged', acknowledged_at = NOW()
            WHERE id = $1::uuid
        """, message_id)
        
        if notes:
            await conn.execute("""
                INSERT INTO coach_channel 
                (from_agent, to_agent, message_type, content, reply_to)
                VALUES ('CLAUDE_CODE', 'LAUNCH_COACH', 'status', $1, $2::uuid)
            """, notes, message_id)
        
        return {"status": "acknowledged", "message_id": message_id}
```

---

## PHASE 4: WORKFLOW EXAMPLE

### 1. I Send Instruction (Claude Web)
```
HEPHAESTUS:coach_send(
    message="Execute /opt/leveredge/specs/gsd-council-guests.md. Prioritize the CONVENER guest endpoints first. Report back when CONVENER is updated.",
    message_type="instruction",
    subject="Build Council Guest System",
    reference_id="gsd-council-guests.md"
)
```

### 2. Claude Code Checks (Claude Code)
```
coach_receive_instructions()

# Returns:
{
  "instructions": [{
    "id": "abc123",
    "subject": "Build Council Guest System",
    "content": "Execute /opt/leveredge/specs/gsd-council-guests.md...",
    "reference_id": "gsd-council-guests.md"
  }],
  "count": 1
}
```

### 3. Claude Code Acknowledges
```
coach_acknowledge(message_id="abc123", notes="Starting CONVENER guest endpoints now")
```

### 4. Claude Code Reports Progress
```
coach_respond(
    message="CONVENER guest endpoints complete: /guests/join, /guests/speak, /guests/listen, /guests/vote, /guests/leave. Moving to HEPHAESTUS MCP tools.",
    message_type="status",
    reply_to="abc123"
)
```

### 5. I Check Progress (Claude Web)
```
HEPHAESTUS:coach_receive()

# See the status update, provide feedback or next instruction
```

---

## DELIVERABLES

- [ ] Database schema (coach_channel, coach_sessions)
- [ ] HEPHAESTUS MCP tools (coach_send, coach_receive, coach_thread, coach_status)
- [ ] Claude Code MCP tools (coach_receive_instructions, coach_respond, coach_acknowledge)
- [ ] Event Bus integration for real-time notifications
- [ ] Test: Send instruction from Claude Web
- [ ] Test: Receive and respond from Claude Code

---

## COMMIT MESSAGE

```
COACH CHANNEL: Claude↔Claude Communication

DATABASE:
- coach_channel table for message passing
- coach_sessions for active coordination
- Threaded conversations support

CLAUDE WEB (HEPHAESTUS):
- coach_send: Send instructions to Claude Code
- coach_receive: Get responses
- coach_thread: View conversation threads
- coach_status: Check unread counts

CLAUDE CODE:
- coach_receive_instructions: Check for work
- coach_respond: Report back
- coach_acknowledge: Confirm receipt

Two minds, one mission. The Coach directs, the Builder executes.
```
