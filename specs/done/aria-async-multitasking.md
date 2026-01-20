# ARIA ASYNC MULTITASKING - Specification

## OVERVIEW

Enable ARIA to dispatch long-running tasks (research, planning, analysis) to background workers while continuing conversation with the user. ARIA can provide progress updates and seamlessly present results when ready.

**User Experience:**
```
User: "Research compliance automation market and plan an approach"

ARIA: "On it! I'm dispatching SCHOLAR for research and CHIRON for planning.
       This will take 2-3 minutes. We can keep talking - I'll update you when ready.
       
       What else is on your mind?"

User: "How's the VARYS build going?"

ARIA: "VARYS is deployed and running daily briefs at 6 AM..."

[2 minutes later]

ARIA: "📊 Research complete! Here's what I found..."
```

**Why This Matters:**
- No blocking on long operations (research takes 60-180 seconds)
- Natural conversation flow maintained
- Multiple tasks can run in parallel
- Progress visibility reduces anxiety
- Results delivered when ready, not when requested

---

## PRIVACY & DATA CONTROLS

### Privacy Levels
```yaml
privacy_levels:
  normal:
    # Default behavior
    - Stored in database
    - Telegram notifications allowed
    - Appears in task history
    - Retained until manually deleted or expired
    
  private:
    # Sensitive tasks
    - Stored in database (encrypted input/output)
    - NO external notifications (Telegram, etc.)
    - Hidden from task history unless explicitly requested
    - Auto-delete after delivery (configurable)
    
  ephemeral:
    # Maximum privacy
    - Minimal database footprint (just task_id + status)
    - NO external notifications
    - Auto-delete immediately after delivery
    - Input/output never persisted
```

### Privacy Triggers
```yaml
# Auto-detect sensitive topics
sensitive_patterns:
  - "private"
  - "confidential"
  - "don't share"
  - "keep this between us"
  - "personal"
  - "salary"
  - "health"
  - "medical"
  - "legal"
  - "financial"
  - "relationship"
  
# User can explicitly set
explicit_commands:
  - "privately research..."
  - "keep this private"
  - "delete after showing me"
  - "don't save this"
```

### ARIA TOOL: `delete_task`
```yaml
name: delete_task
description: "Permanently delete a task and its results"

params:
  task_id:
    type: string
    required: true
    
  confirm:
    type: boolean
    required: true
    description: "Must be true to delete"

returns:
  deleted: boolean
  message: string

triggers:
  - "delete that research"
  - "remove the last task"
  - "forget about that"
  - "clear my task history"
```

### ARIA TOOL: `set_task_privacy`
```yaml
name: set_task_privacy
description: "Change privacy level of a task"

params:
  task_id:
    type: string
    required: true
    
  privacy_level:
    type: string
    enum: [normal, private, ephemeral]
    required: true
    
  auto_delete_after:
    type: string
    description: "Duration after delivery (e.g., '1h', '24h', 'immediately')"

returns:
  updated: boolean
  new_settings: object
```

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                         ARIA                                     │
│                                                                  │
│  User Message ──► Intent Detector ──► Is this async-worthy?     │
│                         │                    │                   │
│                         ▼                    │                   │
│                  Privacy Detector            │                   │
│                  (sensitive topic?)          │                   │
│                         │                    │                   │
│                         ▼                    ▼                   │
│                   [YES: Dispatch]    [NO: Handle Directly]       │
│                         │                                        │
│                         ▼                                        │
│              ┌──────────────────┐                                │
│              │  TASK DISPATCHER │                                │
│              │                  │                                │
│              │  • Create task   │                                │
│              │  • Apply privacy │                                │
│              │  • Store in DB   │                                │
│              │  • Call OLYMPUS  │                                │
│              │  • Return ticket │                                │
│              └────────┬─────────┘                                │
│                       │                                          │
│                       ▼                                          │
│              ┌──────────────────┐                                │
│              │   EVENT BUS      │                                │
│              │   (port 8099)    │                                │
│              │                  │                                │
│              │  • task_started  │                                │
│              │  • task_progress │                                │
│              │  • task_complete │                                │
│              │  • task_failed   │                                │
│              └────────┬─────────┘                                │
│                       │                                          │
│                       ▼                                          │
│              ┌──────────────────┐                                │
│              │ RESULT PRESENTER │                                │
│              │                  │                                │
│              │  • Check privacy │                                │
│              │  • Format output │                                │
│              │  • Auto-delete?  │                                │
│              └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## TASK LIFECYCLE

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌───────────┐     ┌─────────┐
│ PENDING │ ──► │ RUNNING │ ──► │ COMPLETE │ ──► │ DELIVERED │ ──► │ DELETED │
└─────────┘     └─────────┘     └──────────┘     └───────────┘     └─────────┘
     │               │                │                │
     │               │                │                │
     ▼               ▼                ▼                ▼
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌───────────┐
│ EXPIRED │     │ FAILED  │     │ DISMISSED│     │(auto-del) │
└─────────┘     └─────────┘     └──────────┘     └───────────┘
```

**States:**
- `PENDING` - Task created, waiting to execute
- `RUNNING` - Task executing in OLYMPUS
- `COMPLETE` - Task finished, results ready
- `DELIVERED` - Results presented to user
- `FAILED` - Task errored out
- `EXPIRED` - Task timed out (default: 10 min)
- `DISMISSED` - User dismissed without viewing
- `DELETED` - Permanently removed (privacy)

---

## DATABASE SCHEMA

```sql
-- Async tasks dispatched by ARIA
CREATE TABLE aria_async_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    
    -- Task definition
    task_type TEXT NOT NULL,  -- research, plan, analyze, chain
    chain_name TEXT,  -- If using OLYMPUS chain
    agent TEXT,  -- If single agent call
    action TEXT,
    input JSONB NOT NULL,  -- Encrypted if private
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending',
    progress INT DEFAULT 0,  -- 0-100
    progress_message TEXT,
    
    -- Results
    output JSONB,  -- Encrypted if private
    error TEXT,
    
    -- PRIVACY CONTROLS
    privacy_level TEXT NOT NULL DEFAULT 'normal',  -- normal, private, ephemeral
    is_sensitive BOOLEAN DEFAULT FALSE,  -- Auto-detected sensitive content
    hide_from_history BOOLEAN DEFAULT FALSE,
    notify_external BOOLEAN DEFAULT TRUE,  -- Allow Telegram etc.
    auto_delete_after_delivery BOOLEAN DEFAULT FALSE,
    delete_at TIMESTAMPTZ,  -- Scheduled deletion time
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,  -- Soft delete timestamp
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '10 minutes',
    
    -- Context
    conversation_context JSONB,
    trigger_message TEXT,
    
    -- Metadata
    estimated_duration_ms INT,
    actual_duration_ms INT,
    cost FLOAT DEFAULT 0
);

-- Indexes
CREATE INDEX idx_tasks_user_status ON aria_async_tasks(user_id, status);
CREATE INDEX idx_tasks_pending ON aria_async_tasks(status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_tasks_expires ON aria_async_tasks(expires_at) WHERE status = 'pending';
CREATE INDEX idx_tasks_delete_scheduled ON aria_async_tasks(delete_at) WHERE delete_at IS NOT NULL;
CREATE INDEX idx_tasks_not_deleted ON aria_async_tasks(user_id, status) WHERE deleted_at IS NULL;

-- Task progress updates (for detailed tracking)
CREATE TABLE aria_task_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES aria_async_tasks(id) ON DELETE CASCADE,
    step_name TEXT,
    step_status TEXT,  -- started, complete, failed
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_progress_task ON aria_task_progress(task_id);

-- Function to auto-delete expired tasks
CREATE OR REPLACE FUNCTION aria_cleanup_tasks() RETURNS void AS $$
BEGIN
    -- Delete tasks scheduled for deletion
    UPDATE aria_async_tasks 
    SET status = 'deleted', 
        deleted_at = NOW(),
        input = NULL,
        output = NULL,
        conversation_context = NULL,
        trigger_message = NULL
    WHERE delete_at IS NOT NULL 
      AND delete_at <= NOW()
      AND deleted_at IS NULL;
    
    -- Delete ephemeral tasks after delivery
    UPDATE aria_async_tasks 
    SET status = 'deleted',
        deleted_at = NOW(),
        input = NULL,
        output = NULL,
        conversation_context = NULL,
        trigger_message = NULL
    WHERE privacy_level = 'ephemeral'
      AND status = 'delivered'
      AND deleted_at IS NULL;
      
    -- Delete progress records for deleted tasks
    DELETE FROM aria_task_progress 
    WHERE task_id IN (
        SELECT id FROM aria_async_tasks WHERE deleted_at IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql;
```

---

## PRIVACY DETECTION LOGIC

```python
SENSITIVE_PATTERNS = [
    r'\b(private|confidential|secret)\b',
    r'\b(salary|compensation|pay)\b',
    r'\b(health|medical|diagnosis|symptom)\b',
    r'\b(legal|lawsuit|attorney)\b',
    r'\b(financial|debt|loan|credit)\b',
    r'\b(relationship|divorce|dating)\b',
    r'\bdon\'t (share|tell|save)\b',
    r'\bkeep.*(between us|private)\b',
    r'\bdelete.*(after|when done)\b',
]

PRIVACY_COMMANDS = {
    r'^privately\s': 'private',
    r'\bkeep this private\b': 'private',
    r'\bdon\'t save\b': 'ephemeral',
    r'\bdelete after\b': 'auto_delete',
    r'\bforget this\b': 'ephemeral',
}

def detect_privacy_level(message: str, context: dict) -> dict:
    """Detect appropriate privacy level for a task."""
    
    result = {
        'privacy_level': 'normal',
        'is_sensitive': False,
        'notify_external': True,
        'auto_delete_after_delivery': False,
        'delete_after': None
    }
    
    message_lower = message.lower()
    
    # Check for explicit privacy commands
    for pattern, level in PRIVACY_COMMANDS.items():
        if re.search(pattern, message_lower):
            if level == 'private':
                result['privacy_level'] = 'private'
                result['notify_external'] = False
            elif level == 'ephemeral':
                result['privacy_level'] = 'ephemeral'
                result['notify_external'] = False
                result['auto_delete_after_delivery'] = True
            elif level == 'auto_delete':
                result['auto_delete_after_delivery'] = True
                # Parse duration if specified
                duration = extract_duration(message)
                if duration:
                    result['delete_after'] = duration
    
    # Check for sensitive content patterns
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, message_lower):
            result['is_sensitive'] = True
            if result['privacy_level'] == 'normal':
                result['privacy_level'] = 'private'
                result['notify_external'] = False
            break
    
    # User preferences override
    if context.get('default_privacy') == 'private':
        result['privacy_level'] = 'private'
        result['notify_external'] = False
    
    return result
```

---

## ARIA TOOLS

### `dispatch_task` (Updated)
```yaml
name: dispatch_task
description: "Dispatch a long-running task to background processing"

params:
  task_type:
    type: string
    enum: [research, plan, analyze, chain, custom]
    required: true
    
  chain_name:
    type: string
    description: "OLYMPUS chain to execute"
    
  agent:
    type: string
    description: "Single agent to call"
    
  action:
    type: string
    description: "Agent action"
    
  input:
    type: object
    description: "Input data for the task"
    required: true
    
  notify_on_complete:
    type: boolean
    default: true
    
  estimated_duration:
    type: string
    description: "Human-readable estimate"
    
  # PRIVACY OPTIONS
  privacy_level:
    type: string
    enum: [normal, private, ephemeral]
    default: "normal"
    description: "Privacy level for this task"
    
  auto_delete:
    type: boolean
    default: false
    description: "Delete task data after delivery"
    
  delete_after:
    type: string
    description: "Duration to keep results (e.g., '1h', '24h')"

returns:
  task_id: string
  estimated_completion: timestamp
  privacy_level: string
```

### `check_tasks` (Updated)
```yaml
name: check_tasks
description: "Check status of pending/running background tasks"

params:
  task_id:
    type: string
    description: "Specific task to check (optional)"
    
  status_filter:
    type: array
    items: string
    default: ["pending", "running", "complete"]
    
  include_private:
    type: boolean
    default: false
    description: "Include private/hidden tasks"

returns:
  tasks: array
  has_ready_results: boolean
```

### `delete_task`
```yaml
name: delete_task
description: "Permanently delete a task and its results"

params:
  task_id:
    type: string
    required: true
    
  confirm:
    type: boolean
    required: true
    description: "Must be true to delete"

returns:
  deleted: boolean
  message: string

triggers:
  - "delete that research"
  - "remove the last task"
  - "forget about that"
  - "clear that task"
```

### `clear_task_history`
```yaml
name: clear_task_history
description: "Delete all completed tasks from history"

params:
  confirm:
    type: boolean
    required: true
    
  older_than:
    type: string
    description: "Only delete tasks older than (e.g., '7d', '30d')"

returns:
  deleted_count: int
  message: string

triggers:
  - "clear my task history"
  - "delete all old tasks"
```

---

## NOTIFICATION FLOW (Privacy-Aware)

```python
async def on_task_complete(task_id: str):
    task = await get_task(task_id)
    
    # Check privacy settings
    if task.privacy_level == 'ephemeral':
        # Deliver result, then immediately delete
        await inject_result_message(task)
        await delete_task_data(task_id)
        return
    
    if task.notify_external and task.privacy_level == 'normal':
        # Check if user is in active conversation
        if user_is_active(task.user_id):
            await inject_result_message(task)
        else:
            # Send via HERMES (Telegram) - only for non-private
            await hermes_notify(
                user_id=task.user_id,
                message=f"📊 Your {task.task_type} is ready! Check ARIA for results.",
                priority="normal"
            )
    else:
        # Private task - only inject in conversation, no external notify
        if user_is_active(task.user_id):
            await inject_result_message(task)
        # If user not active, result waits silently
    
    # Schedule auto-delete if configured
    if task.auto_delete_after_delivery:
        delete_time = task.delete_after or '1h'
        await schedule_deletion(task_id, delete_time)
    
    await update_task_status(task_id, "delivered")
```

---

## EXAMPLE FLOWS

### Flow 1: Private Research
```
User: "Privately research salary ranges for compliance managers"

ARIA: [Detects "privately" + "salary" = private + sensitive]
      [Calls dispatch_task with privacy_level: "private"]
      
      "🔒 Running this privately - no notifications will be sent outside our chat.
       SCHOLAR is researching salary data now. ~2 minutes.
       
       This won't appear in your normal task history."

[2 minutes later - only in conversation, no Telegram]

ARIA: "🔒 Private research complete:
       
       **Compliance Manager Salary Ranges (US):**
       - Entry: $65-85K
       - Mid: $85-120K  
       - Senior: $120-160K
       
       This data won't be saved. Want me to keep it or delete now?"
```

### Flow 2: Auto-Delete After Viewing
```
User: "Research my competitor's pricing, delete after showing me"

ARIA: [Detects "delete after" = auto_delete]
      
      "Got it - I'll research and then delete the data after you've seen it.
       Working on it now..."

[Later]

ARIA: "📊 Here's the competitor pricing analysis:
       [shows results]
       
       ✓ Task data deleted as requested."
```

### Flow 3: User Deletes Task
```
User: "Delete that last research task"

ARIA: [Calls delete_task]
      
      "Deleted the compliance market research task and all associated data.
       It's been permanently removed from your history."
```

---

## CONFIGURATION

```yaml
aria_async:
  default_timeout_ms: 600000  # 10 minutes
  max_concurrent_tasks: 5
  progress_update_interval_ms: 30000
  
  # Privacy defaults
  privacy:
    default_level: "normal"
    auto_detect_sensitive: true
    sensitive_patterns_enabled: true
    
    # Auto-delete schedules
    ephemeral_delete_delay_ms: 5000  # 5 seconds after delivery
    private_default_retention: "24h"
    normal_default_retention: "30d"
    
    # Cleanup job
    cleanup_interval_ms: 3600000  # Run cleanup every hour
  
  notification:
    in_conversation: true
    telegram_fallback: true
    telegram_for_private: false  # Never notify externally for private
    
  chains_always_async:
    - research-and-plan
    - comprehensive-market-analysis
    - niche-evaluation
```

---

## IMPLEMENTATION ORDER

### Phase 1: Foundation (2 hours)
| # | Task | Effort |
|---|------|--------|
| 1 | Database schema + migrations (with privacy fields) | 30 min |
| 2 | Task Dispatcher workflow | 45 min |
| 3 | Basic Event Bus integration | 45 min |

### Phase 2: OLYMPUS Integration (2 hours)
| # | Task | Effort |
|---|------|--------|
| 4 | Async OLYMPUS call (fire-and-forget) | 30 min |
| 5 | Task Listener workflow | 45 min |
| 6 | Progress tracking | 45 min |

### Phase 3: ARIA Integration (2 hours)
| # | Task | Effort |
|---|------|--------|
| 7 | dispatch_task tool (with privacy) | 30 min |
| 8 | check_tasks tool | 20 min |
| 9 | get_task_result tool | 20 min |
| 10 | delete_task tool | 15 min |
| 11 | Privacy detection logic | 25 min |
| 12 | Testing | 20 min |

### Phase 4: Cleanup & Polish (1 hour)
| # | Task | Effort |
|---|------|--------|
| 13 | Auto-delete scheduler | 30 min |
| 14 | Clear history tool | 15 min |
| 15 | Privacy-aware notifications | 15 min |

**Total Effort:** ~7 hours

---

## SUCCESS METRICS

- [ ] Tasks dispatch without blocking conversation
- [ ] Progress updates every 30 seconds for long tasks
- [ ] Results injected within 5 seconds of completion
- [ ] User can continue chatting while tasks run
- [ ] Failed tasks notify user with clear error
- [ ] Task history queryable
- [ ] **Private tasks never leak to external channels**
- [ ] **Auto-delete works reliably**
- [ ] **Sensitive content auto-detected**

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/aria-async-multitasking.md

Context: Build ARIA async multitasking with privacy controls. Enables background task dispatch while conversation continues. Includes privacy levels (normal/private/ephemeral), auto-delete, and sensitive content detection.

Phases:
1. Database schema (aria_async_tasks with privacy fields, aria_task_progress)
2. Task Dispatcher n8n workflow with privacy detection
3. Task Listener n8n workflow (subscribes to Event Bus)
4. ARIA tools: dispatch_task, check_tasks, get_task_result, delete_task
5. Privacy-aware notification flow
6. Auto-delete scheduler
7. Integration with ARIA Personal Assistant

N8N MCP TOOLS: Use n8n-troubleshooter MCP for DEV data plane workflows.
```

---

## PRIVACY VISIBILITY & CONTROL

### Visual Indicators
ARIA uses consistent icons to show privacy status at a glance:

| Icon | Level | Meaning |
|------|-------|---------|
| 📊 | `normal` | Standard task - saved, notifications enabled |
| 🔒 | `private` | Private task - no external notifications, hidden from history |
| 💨 | `ephemeral` | Ephemeral task - auto-deletes after viewing |
| ⚠️ | auto-detected | ARIA detected sensitive content and upgraded privacy |

### How You'll Know

**When dispatching (auto-detection):**
```
User: "Research salary ranges"

ARIA: "⚠️🔒 I detected sensitive content (salary) - running this privately.
       No Telegram notifications, won't appear in task history.
       
       Say 'make it normal' if you want this saved."
```

**When checking status:**
```
User: "What tasks are running?"

ARIA: "📋 Your tasks:

       **Running:**
       📊 Market research - 67% complete
       
       **Completed (not yet viewed):**
       🔒 Salary research - ready (PRIVATE, auto-deletes in 1h)
       
       **Hidden:** 1 private task
       Say 'show all tasks' to include private ones."
```

**When results arrive:**
```
ARIA: "🔒 Private research complete:
       [results]
       
       Privacy: 🔒 Private | Auto-delete: 1 hour
       Say 'keep this' to save or 'make normal' to add to history."
```

### Commands to Check & Change Privacy

| Say This | Result |
|----------|--------|
| "what's the privacy on that task?" | Shows current privacy level |
| "make it normal" / "save this task" | Changes to normal (saved, notifications OK) |
| "make it private" | Changes to private (no notifications, hidden) |
| "delete this when done" | Sets auto-delete after delivery |
| "keep this" / "don't delete" | Removes auto-delete, keeps in history |
| "show private tasks" / "show all tasks" | Lists hidden/private tasks |

### ARIA TOOL: `get_task_privacy`
```yaml
name: get_task_privacy
description: "Check the current privacy settings of a task"

params:
  task_id:
    type: string
    description: "Task to check (optional - defaults to most recent)"

returns:
  task_id: string
  privacy_level: string  # normal, private, ephemeral
  is_sensitive: boolean  # Was auto-detected as sensitive
  notify_external: boolean
  auto_delete: boolean
  delete_at: timestamp or null
  hidden_from_history: boolean

triggers:
  - "what's the privacy on that"
  - "is that task private"
  - "will that be saved"
```

### Example: Overriding Auto-Detection

```
User: "Research salary benchmarks for my industry report"

ARIA: "⚠️🔒 I detected 'salary' and set this to private automatically.
       SCHOLAR is researching now. ~2 minutes.
       
       Want me to keep it private, or save normally for your report?"

User: "Make it normal, I need this for the report"

ARIA: "📊 Got it - changed to normal mode.
       • Will appear in task history
       • Telegram notification when ready
       • Saved until you delete it
       
       Researching now..."
```

### Example: Checking What's Running

```
User: "What tasks do I have?"

ARIA: "📋 Your tasks:

       **Running:**
       📊 Competitor analysis - 67% complete
       
       **Completed (not yet viewed):**
       🔒 Salary research - ready (PRIVATE, auto-deletes in 1h)
       
       **Hidden:** 1 private task
       Say 'show all tasks' to include private ones."

User: "Show all tasks"

ARIA: "📋 All tasks including private:
       
       📊 Competitor analysis - 67%
       🔒 Salary research - ready
       💨 Health insurance comparison - delivered, deleted"
```
