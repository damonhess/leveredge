# ARIA Integration Validation Spec

## PURPOSE

Validate that all ARIA systems work together seamlessly after the January 2026 upgrades:
- Coaching Tools (12 tools)
- Async Multitasking (7 tools)
- Unified Threading (context management)
- Unified Memory Elite (4 tools + auto-extraction)
- Privacy Controls (across all systems)

**Goal:** Ensure ARIA behaves as a unified intelligent assistant, not a collection of disconnected features.

---

## PART 1: ARIA SYSTEM PROMPT UPDATE

### Current State
ARIA's system prompt in n8n is outdated - doesn't know about new tools.

### Required Updates

```markdown
## YOUR CAPABILITIES

### Memory & Context
You have perfect memory across all our conversations. You can:
- **search_memory** - Find relevant facts, decisions, preferences from any past conversation
- **store_memory** - Explicitly save something important
- **update_memory** - Correct or update stored information
- **forget_memory** - Remove outdated or incorrect memories

Memory happens automatically - I extract key information from our conversations without you needing to ask.

### Background Tasks
For research, analysis, and planning that takes time:
- **dispatch_task** - Send work to background agents (SCHOLAR, CHIRON, etc.)
- **check_tasks** - See status of running tasks
- **get_task_result** - Retrieve completed results
- **delete_task** - Remove task history
- **get_task_privacy** - Check privacy settings
- **set_task_privacy** - Change privacy level
- **clear_task_history** - Bulk delete old tasks

When you ask me to research something, I'll dispatch it and we can keep talking. Results appear when ready.

### Coaching & Self-Development
Deep personal development tools:

**Foundation (Tier 1):**
- **wheel_of_life** - Rate satisfaction across 8 life areas
- **values_clarifier** - Discover and rank your core values
- **progress_tracker** - Track progress toward goals
- **goal_architect** - Design SMART goals with milestones

**Intermediate (Tier 2):**
- **grow_session** - Structured coaching conversation (Goal, Reality, Options, Will)
- **habit_designer** - Design and track habit systems
- **energy_optimizer** - Map your energy patterns
- **decision_accelerator** - Framework for tough decisions
- **resistance_decoder** - Understand what's blocking you

**Advanced (Tier 3):**
- **coaching_insights** - Pattern analysis across all your data
- **system_architect** - Design life systems and routines
- **identity_shifter** - Transform who you're becoming

### Context Awareness
I maintain context from:
1. **Recent messages** - Our current conversation
2. **Semantic memory** - Relevant facts from ALL past conversations
3. **Extracted insights** - Decisions, preferences, commitments you've made
4. **Pending tasks** - Background work in progress

### Privacy Modes
All tasks and memories respect privacy:
- 📊 **Normal** - Saved, Telegram notifications OK
- 🔒 **Private** - No external notifications, hidden from history
- 💨 **Ephemeral** - Auto-deletes after viewing

I auto-detect sensitive topics (salary, health, legal, financial) and upgrade to private.
Say "make it normal" or "make it private" to change.
```

### Tool Routing Logic

Add to ARIA's AI Agent instructions:

```markdown
## TOOL SELECTION GUIDE

### Memory Queries
- "What do you remember about..." → search_memory
- "Did I mention..." → search_memory
- "Remember that..." → store_memory
- "Actually, it's..." → update_memory
- "Forget about..." → forget_memory

### Background Tasks
- "Research..." / "Look into..." / "Analyze..." → dispatch_task
- "How's that research going?" → check_tasks
- "What tasks are running?" → check_tasks
- "Show me the results" → get_task_result
- "Delete that task" → delete_task
- "Is that private?" → get_task_privacy
- "Make it private/normal" → set_task_privacy

### Coaching (use when user wants self-improvement)
- Life satisfaction / balance → wheel_of_life
- Values / what matters → values_clarifier
- Goal setting → goal_architect
- Progress check → progress_tracker
- Stuck / blocked → resistance_decoder
- Decisions → decision_accelerator
- Energy / productivity → energy_optimizer
- Habits → habit_designer
- Coaching conversation → grow_session
- Patterns / insights → coaching_insights
- Routines / systems → system_architect
- Identity change → identity_shifter

### Context (automatic - don't need to call)
Context is assembled automatically before each response:
- Recent conversation from unified threading
- Relevant memories from semantic search
- Pending task status

### Privacy Detection (automatic)
Private mode auto-triggers for: salary, health, medical, legal, financial, relationship, divorce, confidential
User can override with "make it normal" or "keep this private"
```

---

## PART 2: INTEGRATION SMOKE TESTS

### Test Suite

Create workflow: `35 - ARIA Integration Tests`

```yaml
tests:
  # Memory Tests
  - name: "Memory Store"
    input: "Remember that my favorite color is blue"
    expect:
      tool_called: "store_memory"
      memory_type: "preference"
      response_contains: ["remembered", "noted", "stored"]
      
  - name: "Memory Search"
    input: "What's my favorite color?"
    expect:
      tool_called: "search_memory"
      response_contains: "blue"
      
  - name: "Memory Update"
    input: "Actually my favorite color is green now"
    expect:
      tool_called: "update_memory"
      response_contains: ["updated", "changed", "green"]

  # Async Task Tests
  - name: "Task Dispatch"
    input: "Research the compliance automation market"
    expect:
      tool_called: "dispatch_task"
      response_contains: ["dispatching", "background", "research"]
      task_created: true
      
  - name: "Task Status Check"
    input: "How's that research going?"
    expect:
      tool_called: "check_tasks"
      response_contains: ["running", "complete", "progress", "%"]
      
  - name: "Task Result Retrieval"
    setup: "Wait for task completion"
    input: "Show me the research results"
    expect:
      tool_called: "get_task_result"
      response_contains: ["compliance", "market"]

  # Privacy Tests
  - name: "Auto-Private Detection"
    input: "Research salary ranges for compliance managers"
    expect:
      tool_called: "dispatch_task"
      privacy_level: "private"
      response_contains: ["🔒", "private", "privately"]
      
  - name: "Privacy Override"
    input: "Make it normal, I need this for a report"
    expect:
      tool_called: "set_task_privacy"
      new_privacy: "normal"
      response_contains: ["normal", "saved"]
      
  - name: "No Telegram for Private"
    setup: "Create private task, complete it while user offline"
    expect:
      telegram_sent: false

  # Coaching Tests
  - name: "Wheel of Life"
    input: "Let's do a wheel of life assessment"
    expect:
      tool_called: "wheel_of_life"
      response_contains: ["rate", "1-10", "career", "health"]
      
  - name: "Goal Setting"
    input: "Help me set a goal for launching my business"
    expect:
      tool_called: "goal_architect"
      response_contains: ["SMART", "measurable", "deadline"]
      
  - name: "Resistance Check"
    input: "I keep procrastinating on outreach"
    expect:
      tool_called: "resistance_decoder"
      response_contains: ["resistance", "fear", "blocking"]

  # Context Assembly Tests
  - name: "Cross-Session Memory"
    setup: "In previous session, user said 'I'm launching March 1, 2026'"
    input: "When am I launching?"
    expect:
      no_tool_needed: true  # Should be in injected context
      response_contains: "March 1"
      
  - name: "Pending Task Awareness"
    setup: "Task running in background"
    input: "What's going on?"
    expect:
      response_mentions_pending_task: true

  # Integration Tests
  - name: "Research → Memory Flow"
    input: "Research competitor pricing"
    wait: "Task completes"
    then_input: "What did we learn about competitor pricing?"
    expect:
      # Memory should have extracted facts
      response_contains_research_facts: true
      no_need_to_search_again: true
      
  - name: "Coaching → Memory Flow"
    input: "My top value is freedom"
    then_input: "What are my values?"
    expect:
      # Values should be in memory
      response_contains: "freedom"
```

### Manual Test Checklist

```markdown
## Pre-Flight Checklist

### Services Running
- [ ] aria-threading service (port 8113): `curl localhost:8113/health`
- [ ] Event Bus (port 8099): `curl localhost:8099/health`
- [ ] DEV n8n (port 5680): Check UI
- [ ] ARIA workflow active in n8n

### Database Tables Exist
- [ ] aria_unified_memory (with embedding column)
- [ ] aria_async_tasks
- [ ] aria_task_progress
- [ ] aria_chunks
- [ ] aria_chunk_embeddings
- [ ] aria_extracted_info
- [ ] All coaching tables (13 tables)

### Workflow Status
- [ ] ARIA Personal Assistant - Active
- [ ] Task Dispatcher - Ready
- [ ] Task Listener - Active
- [ ] Task Cleanup - Active
- [ ] Task Result Extractor - Active
- [ ] Memory Consolidation - Active

### End-to-End Tests
1. [ ] Send message to ARIA, get response
2. [ ] "Remember my dog is named Max" → Confirm stored
3. [ ] New session: "What's my dog's name?" → "Max"
4. [ ] "Research AI trends" → Task dispatches
5. [ ] "How's that going?" → Shows progress
6. [ ] Results arrive and display correctly
7. [ ] "Privately research salaries" → Shows 🔒
8. [ ] "Do a wheel of life" → Coaching works
9. [ ] Check no errors in n8n execution log
10. [ ] Check no errors in aria-threading log
```

---

## PART 3: PRIVACY FLOW VALIDATION

### Privacy Matrix

| Action | Normal | Private | Ephemeral |
|--------|--------|---------|-----------|
| Store in DB | ✅ | ✅ (encrypted) | ❌ (minimal) |
| Telegram notify | ✅ | ❌ | ❌ |
| Task history | ✅ | Hidden | ❌ |
| Memory extraction | ✅ | ✅ (private) | ❌ |
| Search results | ✅ | Only if requested | ❌ |

### Validation Queries

```sql
-- Check no private data leaked to normal queries
SELECT * FROM aria_unified_memory 
WHERE privacy_level = 'private' 
AND id IN (
  SELECT memory_id FROM some_public_view
);
-- Should return 0 rows

-- Check ephemeral tasks are deleted
SELECT * FROM aria_async_tasks 
WHERE privacy_level = 'ephemeral' 
AND status = 'delivered'
AND deleted_at IS NULL;
-- Should return 0 rows

-- Check private tasks don't have external notifications
SELECT * FROM aria_async_tasks 
WHERE privacy_level = 'private'
AND notify_external = TRUE;
-- Should return 0 rows
```

### Privacy Test Scenarios

```markdown
1. **Sensitive Auto-Detection**
   - Input: "Research my medical options"
   - Expected: Auto-upgrades to private, shows 🔒
   
2. **Private Task Completion While Offline**
   - Setup: Create private research task, go offline
   - Expected: NO Telegram notification sent
   - Verify: Task waits silently for next session
   
3. **Ephemeral Task Cleanup**
   - Input: "Research this but delete after showing me"
   - View results
   - Verify: Task data deleted from DB within 5 seconds
   
4. **Private Memory Isolation**
   - Store private memory about salary
   - Regular search_memory should NOT return it
   - "Show private memories" SHOULD return it
   
5. **Privacy Override**
   - Auto-detected as private
   - "Make it normal"
   - Verify: Now appears in regular history
```

---

## PART 4: HEALTH CHECK SYSTEM

### Unified Health Endpoint

Add to aria-threading `/health` or create new monitoring workflow:

```python
@app.get("/health/full")
async def full_health_check():
    checks = {}
    
    # Database
    try:
        await db.execute("SELECT 1")
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Tables exist
    required_tables = [
        "aria_unified_memory",
        "aria_async_tasks", 
        "aria_chunks",
        "aria_conversations",
        "aria_messages"
    ]
    for table in required_tables:
        try:
            await db.execute(f"SELECT 1 FROM {table} LIMIT 1")
            checks[f"table_{table}"] = {"status": "healthy"}
        except:
            checks[f"table_{table}"] = {"status": "unhealthy"}
    
    # Event Bus
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8099/health", timeout=5)
            checks["event_bus"] = {"status": "healthy" if r.status_code == 200 else "unhealthy"}
    except:
        checks["event_bus"] = {"status": "unhealthy"}
    
    # n8n DEV
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:5680/healthz", timeout=5)
            checks["n8n_dev"] = {"status": "healthy" if r.status_code == 200 else "unhealthy"}
    except:
        checks["n8n_dev"] = {"status": "unhealthy"}
    
    # Overall
    all_healthy = all(c.get("status") == "healthy" for c in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### VARYS Integration

Add to VARYS daily brief:

```markdown
## ARIA System Health

Services:
- aria-threading: {{ health.aria_threading }}
- Event Bus: {{ health.event_bus }}
- n8n DEV: {{ health.n8n_dev }}

Stats (24h):
- Messages processed: {{ stats.messages }}
- Tasks dispatched: {{ stats.tasks_dispatched }}
- Tasks completed: {{ stats.tasks_completed }}
- Memories stored: {{ stats.memories_stored }}
- Memories retrieved: {{ stats.memories_retrieved }}

Issues:
{{ health.issues | default("None") }}
```

---

## PART 5: EXPECTED BEHAVIORS DOCUMENTATION

### User Experience Contract

```markdown
## What Users Should Experience

### Memory
- ARIA remembers everything without being asked
- Cross-session recall is seamless ("What did we decide about X?" just works)
- Facts, preferences, decisions persist forever
- Context (temporary state) naturally decays
- User can explicitly store, update, or forget

### Background Tasks
- Research/analysis doesn't block conversation
- Clear feedback: "I'm working on that, ~2 min"
- Progress updates available on request
- Results appear automatically when ready
- Can continue chatting while tasks run

### Coaching
- Deep, structured personal development
- Progress tracked over time
- Insights emerge from patterns
- Non-judgmental, supportive tone

### Privacy
- Sensitive topics auto-protected
- Clear visual indicators (📊🔒💨)
- Easy to change privacy level
- Private data never leaks externally
- User always in control

### Context
- ARIA knows what we were just talking about
- ARIA knows relevant history from past sessions
- ARIA knows about pending background work
- No need to repeat yourself
```

### Failure Modes & Recovery

| Failure | Symptom | Auto-Recovery | Manual Fix |
|---------|---------|---------------|------------|
| aria-threading down | No context, no memory | systemd restart | `sudo systemctl restart aria-threading` |
| Event Bus down | Tasks don't complete | - | Check port 8099 |
| n8n down | No responses | Docker restart | `docker restart n8n-dev` |
| DB connection lost | All features fail | Connection pool retry | Check postgres container |
| Memory full | Slow responses | Compaction runs | Manual compaction |
| Too many tasks | Queue backlog | Older tasks expire | Clear task history |

---

## IMPLEMENTATION ORDER

### Phase 1: System Prompt Update (1 hour)
| # | Task | Effort |
|---|------|--------|
| 1 | Update ARIA Personal Assistant prompt in n8n | 30 min |
| 2 | Add tool routing instructions | 20 min |
| 3 | Test prompt changes | 10 min |

### Phase 2: Health Checks (1 hour)
| # | Task | Effort |
|---|------|--------|
| 4 | Add /health/full endpoint to aria-threading | 30 min |
| 5 | Add ARIA health to VARYS brief | 20 min |
| 6 | Test health checks | 10 min |

### Phase 3: Integration Tests (1.5 hours)
| # | Task | Effort |
|---|------|--------|
| 7 | Create test workflow in n8n | 30 min |
| 8 | Run automated test suite | 30 min |
| 9 | Run manual checklist | 30 min |

### Phase 4: Privacy Validation (30 min)
| # | Task | Effort |
|---|------|--------|
| 10 | Run privacy test scenarios | 20 min |
| 11 | Verify with SQL queries | 10 min |

**Total Effort:** ~4 hours

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/aria-integration-validation.md

Context: Validate all ARIA systems work together after January 2026 upgrades. This is integration testing, NOT building new features.

Key Tasks:
1. Update ARIA Personal Assistant system prompt with all 33+ tools
2. Add tool routing instructions to AI Agent
3. Create /health/full endpoint in aria-threading
4. Add ARIA health to VARYS daily brief
5. Run smoke tests (memory, async, coaching, privacy)
6. Validate privacy flows with SQL queries
7. Document expected behaviors

Focus on VALIDATION not building. The systems are built - we're making sure they work together.

N8N MCP TOOLS: Use n8n-troubleshooter MCP for DEV data plane workflows.
```

---

## SUCCESS CRITERIA

- [ ] ARIA correctly routes to all 33+ tools
- [ ] Memory persists across sessions
- [ ] Tasks dispatch and complete
- [ ] Privacy is respected everywhere
- [ ] Health checks all pass
- [ ] No errors in logs during test suite
- [ ] VARYS reports ARIA health daily
