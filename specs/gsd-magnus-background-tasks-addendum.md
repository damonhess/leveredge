# ADDENDUM: MAGNUS Background Tasks & Multitasking

**Add to MAGNUS Unified Command Center GSD - Insert after Phase 5, before Phase 6**

---

## PHASE 5.5: BACKGROUND TASKS & MULTITASKING

Add background task support so MAGNUS can do multiple things simultaneously.

### 5.5.1 Add BackgroundTasks Import

Update `magnus.py` imports:

```python
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
```

### 5.5.2 Update Sync Endpoints for Background Execution

Replace the sync endpoint with this version:

```python
@app.post("/connections/{connection_id}/sync")
async def trigger_sync(
    connection_id: str, 
    background_tasks: BackgroundTasks,
    direction: str = "bidirectional",
    wait: bool = False
):
    """
    Trigger sync for a connection.
    
    Args:
        wait: If True, wait for completion. If False (default), run in background.
    """
    if wait:
        # Synchronous - wait for completion
        sync_dir = SyncDirection(direction)
        project_result = await sync_engine.sync_projects(connection_id, sync_dir)
        task_result = await sync_engine.sync_tasks(connection_id, direction=sync_dir)
        return {
            "status": "completed",
            "projects": project_result,
            "tasks": task_result,
            "magnus_says": "All pieces synchronized. The board is current."
        }
    else:
        # Background - return immediately
        sync_dir = SyncDirection(direction)
        background_tasks.add_task(sync_engine.sync_projects, connection_id, sync_dir)
        background_tasks.add_task(sync_engine.sync_tasks, connection_id, None, sync_dir)
        return {
            "status": "started",
            "message": "Sync running in background. Check /sync/status for progress.",
            "magnus_says": "The pieces are moving. I'll update you when the board is set."
        }
```

### 5.5.3 Add Sync-All Endpoint

```python
@app.post("/sync/all")
async def sync_all_connections(background_tasks: BackgroundTasks):
    """
    Sync ALL connected tools simultaneously in background.
    True multitasking - all tools sync in parallel.
    """
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        connections = await conn.fetch(
            "SELECT id, tool_name FROM magnus_pm_connections WHERE sync_enabled = TRUE"
        )
    
    for connection in connections:
        background_tasks.add_task(
            sync_engine.sync_projects, 
            str(connection['id']), 
            SyncDirection.BIDIRECTIONAL
        )
        background_tasks.add_task(
            sync_engine.sync_tasks,
            str(connection['id']),
            None,
            SyncDirection.BIDIRECTIONAL
        )
    
    return {
        "status": "started",
        "connections_syncing": len(connections),
        "tools": [c['tool_name'] for c in connections],
        "magnus_says": f"Synchronizing {len(connections)} battlefields simultaneously. All pieces moving."
    }
```

### 5.5.4 Add Sync Status Endpoint

```python
@app.get("/sync/status")
async def get_sync_status():
    """Get status of recent sync operations"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        recent = await conn.fetch("""
            SELECT sl.*, pc.tool_name, pc.display_name
            FROM magnus_sync_log sl
            JOIN magnus_pm_connections pc ON sl.connection_id = pc.id
            ORDER BY sl.started_at DESC
            LIMIT 20
        """)
        
        in_progress = [r for r in recent if r['status'] == 'started']
        
        return {
            "in_progress": len(in_progress),
            "recent_syncs": [dict(r) for r in recent],
            "magnus_says": f"{len(in_progress)} sync operations in progress." if in_progress else "All syncs complete."
        }
```

### 5.5.5 Background AI Operations

```python
@app.post("/ai/breakdown-async")
async def ai_breakdown_async(
    background_tasks: BackgroundTasks,
    task_id: str
):
    """Run AI breakdown in background, store results on task"""
    background_tasks.add_task(run_ai_breakdown_and_store, task_id)
    return {
        "status": "started",
        "task_id": task_id,
        "message": "AI breakdown running. Results will be stored on task metadata."
    }


async def run_ai_breakdown_and_store(task_id: str):
    """Background task for AI breakdown"""
    async with pool.acquire() as conn:
        task = await conn.fetchrow(
            "SELECT * FROM magnus_tasks WHERE id = $1::uuid", task_id
        )
        
        if not task:
            return
        
        # Run AI breakdown
        result = await ai_task_breakdown(task_id=task_id)
        
        # Store result on task metadata
        import json
        await conn.execute("""
            UPDATE magnus_tasks 
            SET metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb,
                updated_at = NOW()
            WHERE id = $1::uuid
        """, task_id, json.dumps({"ai_breakdown": result}))
```

### 5.5.6 Add metadata column to tasks (if not exists)

```sql
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
```

---

## Key Behavior

| Endpoint | Default | With `?wait=true` |
|----------|---------|-------------------|
| `/connections/{id}/sync` | Background (returns immediately) | Waits for completion |
| `/sync/all` | Always background | N/A |
| `/ai/breakdown-async` | Always background | Use `/ai/breakdown` for sync |

**This enables MAGNUS to:**
- Sync OpenProject while simultaneously syncing Leantime
- Return control to you immediately while heavy operations run
- Process AI breakdowns without blocking
- Track progress via `/sync/status`

---

*"I move all pieces simultaneously. While you wait for one, I've already positioned the others."*
