# GSD: Pipeline System - Agent Orchestration

**Priority:** MEDIUM
**Estimated Time:** 4-6 hours
**Component:** ATLAS Enhancement

---

## OVERVIEW

Wire up multi-agent pipelines that execute complex workflows automatically:
- **Agent Upgrade Pipeline**: Evaluate → Research → Plan → Build → Verify
- **Content Creation Pipeline**: Ideate → Write → Design → Review → Publish
- **Research Pipeline**: Question → Search → Analyze → Synthesize → Report

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ATLAS PIPELINE ENGINE                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Pipeline Definition                                                 │   │
│  │  - Stages (ordered)                                                 │   │
│  │  - Agent assignments                                                │   │
│  │  - Handoff rules                                                    │   │
│  │  - Error handling                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Execution Engine                                                    │   │
│  │  - Stage execution                                                  │   │
│  │  - Context passing                                                  │   │
│  │  - Progress tracking                                                │   │
│  │  - Retry logic                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────┬──────────┬────┴────┬──────────┬──────────┐           │
│         ▼          ▼          ▼         ▼          ▼          ▼           │
│      ALOY      SCHOLAR    CHIRON   HEPHAESTUS   MUSE      QUILL          │
│    (evaluate)  (research)  (plan)    (build)   (ideate)  (write)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## DATABASE SCHEMA

Already created in earlier migrations, but here's the reference:

```sql
-- Pipeline definitions
CREATE TABLE IF NOT EXISTS pipeline_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    
    stages JSONB NOT NULL,  -- Ordered array of stage definitions
    -- Stage format: {
    --   "name": "research",
    --   "agent": "SCHOLAR",
    --   "action": "deep-research",
    --   "required_inputs": ["topic"],
    --   "outputs": ["research_report"],
    --   "timeout_minutes": 30,
    --   "retry_count": 2
    -- }
    
    default_config JSONB DEFAULT '{}',
    
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'disabled', 'deprecated')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline executions
CREATE TABLE IF NOT EXISTS pipeline_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    pipeline_id UUID REFERENCES pipeline_definitions(id),
    pipeline_name TEXT NOT NULL,
    
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'paused', 'completed', 'failed', 'cancelled'
    )),
    
    -- Input/output
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- Progress
    current_stage INTEGER DEFAULT 0,
    total_stages INTEGER,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    triggered_by TEXT,  -- "user", "schedule", "agent"
    context JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stage execution logs
CREATE TABLE IF NOT EXISTS pipeline_stage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    execution_id UUID REFERENCES pipeline_executions(id) ON DELETE CASCADE,
    
    stage_index INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    agent TEXT NOT NULL,
    
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'skipped'
    )),
    
    -- Data flow
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Errors
    error_message TEXT,
    retry_attempt INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_status ON pipeline_executions(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_pipeline ON pipeline_executions(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_stage_logs_execution ON pipeline_stage_logs(execution_id);
```

---

## PIPELINE DEFINITIONS

### 1. Agent Upgrade Pipeline

```json
{
  "name": "agent-upgrade",
  "description": "Evaluate and upgrade an agent's capabilities",
  "stages": [
    {
      "name": "evaluate",
      "agent": "ALOY",
      "action": "evaluate-agent",
      "required_inputs": ["agent_name"],
      "outputs": ["evaluation_report", "improvement_areas"],
      "timeout_minutes": 15
    },
    {
      "name": "research",
      "agent": "SCHOLAR",
      "action": "deep-research",
      "required_inputs": ["improvement_areas"],
      "outputs": ["best_practices", "implementation_approaches"],
      "timeout_minutes": 30
    },
    {
      "name": "plan",
      "agent": "CHIRON",
      "action": "create-plan",
      "required_inputs": ["evaluation_report", "best_practices"],
      "outputs": ["upgrade_plan", "tasks"],
      "timeout_minutes": 20
    },
    {
      "name": "review",
      "agent": "MAGNUS",
      "action": "review-plan",
      "required_inputs": ["upgrade_plan"],
      "outputs": ["approved_plan", "timeline"],
      "timeout_minutes": 10,
      "requires_approval": true
    },
    {
      "name": "build",
      "agent": "HEPHAESTUS",
      "action": "execute-plan",
      "required_inputs": ["approved_plan"],
      "outputs": ["build_results", "changes_made"],
      "timeout_minutes": 60
    },
    {
      "name": "verify",
      "agent": "ALOY",
      "action": "verify-upgrade",
      "required_inputs": ["agent_name", "changes_made"],
      "outputs": ["verification_report", "success"],
      "timeout_minutes": 15
    },
    {
      "name": "report",
      "agent": "ARIA",
      "action": "summarize",
      "required_inputs": ["verification_report"],
      "outputs": ["summary"],
      "timeout_minutes": 5
    }
  ]
}
```

### 2. Content Creation Pipeline

```json
{
  "name": "content-creation",
  "description": "Create content from brief to publication",
  "stages": [
    {
      "name": "ideate",
      "agent": "MUSE",
      "action": "generate-concepts",
      "required_inputs": ["brief", "content_type"],
      "outputs": ["concepts", "angles"],
      "timeout_minutes": 15
    },
    {
      "name": "research",
      "agent": "SCHOLAR",
      "action": "research-topic",
      "required_inputs": ["concepts"],
      "outputs": ["research_data", "sources"],
      "timeout_minutes": 20
    },
    {
      "name": "write",
      "agent": "QUILL",
      "action": "write-content",
      "required_inputs": ["concepts", "research_data", "content_type"],
      "outputs": ["draft"],
      "timeout_minutes": 30
    },
    {
      "name": "design",
      "agent": "STAGE",
      "action": "create-visuals",
      "required_inputs": ["draft", "content_type"],
      "outputs": ["visuals", "layout"],
      "timeout_minutes": 20,
      "optional": true
    },
    {
      "name": "review",
      "agent": "CRITIC",
      "action": "review-content",
      "required_inputs": ["draft", "visuals"],
      "outputs": ["feedback", "score"],
      "timeout_minutes": 15
    },
    {
      "name": "revise",
      "agent": "QUILL",
      "action": "revise-content",
      "required_inputs": ["draft", "feedback"],
      "outputs": ["final_content"],
      "timeout_minutes": 20,
      "condition": "score < 80"
    },
    {
      "name": "publish",
      "agent": "HERMES",
      "action": "publish-content",
      "required_inputs": ["final_content", "destination"],
      "outputs": ["publication_url"],
      "timeout_minutes": 10
    }
  ]
}
```

### 3. Research Pipeline

```json
{
  "name": "deep-research",
  "description": "Comprehensive research on a topic",
  "stages": [
    {
      "name": "scope",
      "agent": "CHIRON",
      "action": "define-scope",
      "required_inputs": ["question"],
      "outputs": ["research_questions", "scope"],
      "timeout_minutes": 10
    },
    {
      "name": "search",
      "agent": "SCHOLAR",
      "action": "web-research",
      "required_inputs": ["research_questions"],
      "outputs": ["raw_data", "sources"],
      "timeout_minutes": 30
    },
    {
      "name": "analyze",
      "agent": "SCHOLAR",
      "action": "analyze-data",
      "required_inputs": ["raw_data"],
      "outputs": ["insights", "patterns"],
      "timeout_minutes": 20
    },
    {
      "name": "synthesize",
      "agent": "QUILL",
      "action": "write-report",
      "required_inputs": ["insights", "sources", "question"],
      "outputs": ["report"],
      "timeout_minutes": 25
    },
    {
      "name": "review",
      "agent": "CRITIC",
      "action": "fact-check",
      "required_inputs": ["report", "sources"],
      "outputs": ["verified_report", "confidence"],
      "timeout_minutes": 15
    }
  ]
}
```

### 4. Client Onboarding Pipeline

```json
{
  "name": "client-onboarding",
  "description": "Onboard a new client",
  "stages": [
    {
      "name": "setup",
      "agent": "MAGNUS",
      "action": "create-project",
      "required_inputs": ["client_name", "project_type"],
      "outputs": ["project_id"],
      "timeout_minutes": 5
    },
    {
      "name": "connect-pm",
      "agent": "MAGNUS",
      "action": "connect-pm-tool",
      "required_inputs": ["client_pm_tool", "credentials"],
      "outputs": ["connection_id"],
      "timeout_minutes": 10,
      "optional": true
    },
    {
      "name": "setup-billing",
      "agent": "LITTLEFINGER",
      "action": "create-client",
      "required_inputs": ["client_name", "billing_info"],
      "outputs": ["client_id"],
      "timeout_minutes": 5
    },
    {
      "name": "create-workspace",
      "agent": "HEPHAESTUS",
      "action": "setup-workspace",
      "required_inputs": ["client_name"],
      "outputs": ["workspace_path"],
      "timeout_minutes": 15
    },
    {
      "name": "notify",
      "agent": "HERMES",
      "action": "send-welcome",
      "required_inputs": ["client_name", "contact_email"],
      "outputs": ["notification_sent"],
      "timeout_minutes": 5
    }
  ]
}
```

---

## ATLAS PIPELINE ENGINE

Add to ATLAS or create new service:

```python
"""
Pipeline Execution Engine
Orchestrates multi-agent workflows
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import httpx
import json

# Agent endpoint mapping
AGENT_ENDPOINTS = {
    "ALOY": "http://localhost:8015",
    "SCHOLAR": "http://localhost:8030",
    "CHIRON": "http://localhost:8031",
    "MAGNUS": "http://localhost:8019",
    "HEPHAESTUS": "http://localhost:8011",
    "MUSE": "http://localhost:8032",
    "QUILL": "http://localhost:8033",
    "STAGE": "http://localhost:8034",
    "REEL": "http://localhost:8035",
    "CRITIC": "http://localhost:8036",
    "HERMES": "http://localhost:8014",
    "LITTLEFINGER": "http://localhost:8020",
    "VARYS": "http://localhost:8018",
    "ARIA": "http://localhost:8111",
}

class PipelineEngine:
    def __init__(self, pool):
        self.pool = pool
        self.active_executions: Dict[str, asyncio.Task] = {}
    
    async def start_pipeline(
        self,
        pipeline_name: str,
        input_data: dict,
        triggered_by: str = "user"
    ) -> str:
        """Start a pipeline execution"""
        
        async with self.pool.acquire() as conn:
            # Get pipeline definition
            pipeline = await conn.fetchrow(
                "SELECT * FROM pipeline_definitions WHERE name = $1 AND status = 'active'",
                pipeline_name
            )
            
            if not pipeline:
                raise HTTPException(404, f"Pipeline '{pipeline_name}' not found")
            
            stages = pipeline['stages']
            
            # Create execution record
            execution = await conn.fetchrow("""
                INSERT INTO pipeline_executions 
                (pipeline_id, pipeline_name, input_data, total_stages, triggered_by, status, started_at)
                VALUES ($1, $2, $3, $4, $5, 'running', NOW())
                RETURNING id
            """, pipeline['id'], pipeline_name, input_data, len(stages), triggered_by)
            
            execution_id = str(execution['id'])
            
            # Start execution in background
            task = asyncio.create_task(
                self._execute_pipeline(execution_id, stages, input_data)
            )
            self.active_executions[execution_id] = task
            
            return execution_id
    
    async def _execute_pipeline(
        self,
        execution_id: str,
        stages: list,
        initial_input: dict
    ):
        """Execute pipeline stages sequentially"""
        
        context = initial_input.copy()
        
        async with self.pool.acquire() as conn:
            for i, stage in enumerate(stages):
                stage_name = stage['name']
                agent = stage['agent']
                action = stage['action']
                
                # Check if stage should be skipped (conditional)
                if 'condition' in stage:
                    if not self._evaluate_condition(stage['condition'], context):
                        await self._log_stage(conn, execution_id, i, stage_name, agent, 'skipped', {}, {})
                        continue
                
                # Update execution progress
                await conn.execute(
                    "UPDATE pipeline_executions SET current_stage = $2 WHERE id = $1",
                    execution_id, i
                )
                
                # Prepare stage input
                stage_input = {}
                for input_key in stage.get('required_inputs', []):
                    if input_key in context:
                        stage_input[input_key] = context[input_key]
                    else:
                        # Missing required input
                        await self._fail_execution(
                            conn, execution_id, 
                            f"Missing required input '{input_key}' for stage '{stage_name}'"
                        )
                        return
                
                # Log stage start
                stage_log_id = await self._log_stage(
                    conn, execution_id, i, stage_name, agent, 'running', stage_input, {}
                )
                
                # Execute stage
                try:
                    timeout = stage.get('timeout_minutes', 30) * 60
                    output = await asyncio.wait_for(
                        self._call_agent(agent, action, stage_input),
                        timeout=timeout
                    )
                    
                    # Update stage log
                    await conn.execute("""
                        UPDATE pipeline_stage_logs 
                        SET status = 'completed', output_data = $2, completed_at = NOW(),
                            duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))
                        WHERE id = $1
                    """, stage_log_id, output)
                    
                    # Merge output into context
                    context.update(output)
                    
                    # Check if approval required
                    if stage.get('requires_approval'):
                        await conn.execute(
                            "UPDATE pipeline_executions SET status = 'paused' WHERE id = $1",
                            execution_id
                        )
                        # Wait for approval (could be webhook or manual)
                        # For now, auto-approve after logging
                        await conn.execute(
                            "UPDATE pipeline_executions SET status = 'running' WHERE id = $1",
                            execution_id
                        )
                
                except asyncio.TimeoutError:
                    await self._fail_stage(conn, stage_log_id, "Stage timed out")
                    
                    # Retry logic
                    retry_count = stage.get('retry_count', 0)
                    if retry_count > 0:
                        # Implement retry
                        pass
                    else:
                        await self._fail_execution(conn, execution_id, f"Stage '{stage_name}' timed out")
                        return
                
                except Exception as e:
                    await self._fail_stage(conn, stage_log_id, str(e))
                    await self._fail_execution(conn, execution_id, f"Stage '{stage_name}' failed: {e}")
                    return
            
            # Pipeline completed successfully
            await conn.execute("""
                UPDATE pipeline_executions 
                SET status = 'completed', output_data = $2, completed_at = NOW()
                WHERE id = $1
            """, execution_id, context)
            
            # Report to LCIS
            await self._report_success(execution_id, context)
    
    async def _call_agent(self, agent: str, action: str, input_data: dict) -> dict:
        """Call an agent's action endpoint"""
        
        endpoint = AGENT_ENDPOINTS.get(agent)
        if not endpoint:
            raise Exception(f"Unknown agent: {agent}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{endpoint}/action/{action}",
                json=input_data
            )
            
            if response.status_code != 200:
                raise Exception(f"Agent returned {response.status_code}: {response.text}")
            
            return response.json()
    
    async def _log_stage(self, conn, execution_id, index, name, agent, status, input_data, output_data):
        """Log stage execution"""
        row = await conn.fetchrow("""
            INSERT INTO pipeline_stage_logs 
            (execution_id, stage_index, stage_name, agent, status, input_data, output_data, started_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            RETURNING id
        """, execution_id, index, name, agent, status, input_data, output_data)
        return row['id']
    
    async def _fail_stage(self, conn, stage_log_id, error):
        """Mark stage as failed"""
        await conn.execute("""
            UPDATE pipeline_stage_logs 
            SET status = 'failed', error_message = $2, completed_at = NOW()
            WHERE id = $1
        """, stage_log_id, error)
    
    async def _fail_execution(self, conn, execution_id, error):
        """Mark execution as failed"""
        await conn.execute("""
            UPDATE pipeline_executions 
            SET status = 'failed', error_message = $2, completed_at = NOW()
            WHERE id = $1
        """, execution_id, error)
        
        # Report to LCIS
        await self._report_failure(execution_id, error)
    
    async def _report_success(self, execution_id, output):
        """Report success to LCIS"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8050/ingest",
                    json={
                        "lesson_type": "success",
                        "title": f"Pipeline execution {execution_id} completed",
                        "content": f"Output: {json.dumps(output)[:500]}",
                        "source_agent": "ATLAS",
                        "domain": "GAIA"
                    }
                )
        except:
            pass
    
    async def _report_failure(self, execution_id, error):
        """Report failure to LCIS"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8050/ingest",
                    json={
                        "lesson_type": "failure",
                        "title": f"Pipeline execution {execution_id} failed",
                        "content": error,
                        "source_agent": "ATLAS",
                        "domain": "GAIA"
                    }
                )
        except:
            pass
    
    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a stage condition"""
        # Simple evaluation - could be expanded
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except:
            return True

# API Endpoints
@app.post("/pipelines/{pipeline_name}/execute")
async def execute_pipeline(
    pipeline_name: str,
    input_data: dict,
    background_tasks: BackgroundTasks
):
    """Start a pipeline execution"""
    execution_id = await pipeline_engine.start_pipeline(pipeline_name, input_data)
    return {"execution_id": execution_id, "status": "started"}

@app.get("/pipelines/{execution_id}/status")
async def get_pipeline_status(execution_id: str):
    """Get pipeline execution status"""
    async with pool.acquire() as conn:
        execution = await conn.fetchrow(
            "SELECT * FROM pipeline_executions WHERE id = $1",
            execution_id
        )
        
        if not execution:
            raise HTTPException(404, "Execution not found")
        
        stages = await conn.fetch(
            "SELECT * FROM pipeline_stage_logs WHERE execution_id = $1 ORDER BY stage_index",
            execution_id
        )
        
        return {
            "execution": dict(execution),
            "stages": [dict(s) for s in stages]
        }

@app.get("/pipelines/active")
async def list_active_pipelines():
    """List active pipeline executions"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM pipeline_executions 
            WHERE status IN ('running', 'paused')
            ORDER BY started_at DESC
        """)
        return [dict(row) for row in rows]

@app.post("/pipelines/{execution_id}/cancel")
async def cancel_pipeline(execution_id: str):
    """Cancel a running pipeline"""
    if execution_id in pipeline_engine.active_executions:
        pipeline_engine.active_executions[execution_id].cancel()
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE pipeline_executions SET status = 'cancelled' WHERE id = $1",
            execution_id
        )
    
    return {"status": "cancelled"}
```

---

## MCP TOOLS

```python
@mcp_tool(name="pipeline_execute")
async def pipeline_execute(pipeline_name: str, input_data: dict) -> dict:
    """Execute a pipeline"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/pipelines/{pipeline_name}/execute",
            json=input_data
        )
        return response.json()

@mcp_tool(name="pipeline_status")
async def pipeline_status(execution_id: str) -> dict:
    """Get pipeline execution status"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/pipelines/{execution_id}/status"
        )
        return response.json()

@mcp_tool(name="pipeline_list")
async def pipeline_list() -> dict:
    """List active pipelines"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/pipelines/active")
        return response.json()
```

---

## SEED PIPELINES

```sql
-- Seed pipeline definitions
INSERT INTO pipeline_definitions (name, description, stages) VALUES
(
    'agent-upgrade',
    'Evaluate and upgrade an agent',
    '[
        {"name": "evaluate", "agent": "ALOY", "action": "evaluate-agent", "required_inputs": ["agent_name"], "outputs": ["evaluation_report"], "timeout_minutes": 15},
        {"name": "research", "agent": "SCHOLAR", "action": "deep-research", "required_inputs": ["evaluation_report"], "outputs": ["best_practices"], "timeout_minutes": 30},
        {"name": "plan", "agent": "CHIRON", "action": "create-plan", "required_inputs": ["evaluation_report", "best_practices"], "outputs": ["upgrade_plan"], "timeout_minutes": 20},
        {"name": "build", "agent": "HEPHAESTUS", "action": "execute-plan", "required_inputs": ["upgrade_plan"], "outputs": ["build_results"], "timeout_minutes": 60},
        {"name": "verify", "agent": "ALOY", "action": "verify-upgrade", "required_inputs": ["agent_name", "build_results"], "outputs": ["verification_report"], "timeout_minutes": 15}
    ]'::jsonb
),
(
    'content-creation',
    'Create content from brief to publication',
    '[
        {"name": "ideate", "agent": "MUSE", "action": "generate-concepts", "required_inputs": ["brief", "content_type"], "outputs": ["concepts"], "timeout_minutes": 15},
        {"name": "write", "agent": "QUILL", "action": "write-content", "required_inputs": ["concepts"], "outputs": ["draft"], "timeout_minutes": 30},
        {"name": "review", "agent": "CRITIC", "action": "review-content", "required_inputs": ["draft"], "outputs": ["feedback", "score"], "timeout_minutes": 15}
    ]'::jsonb
),
(
    'deep-research',
    'Comprehensive research on a topic',
    '[
        {"name": "scope", "agent": "CHIRON", "action": "define-scope", "required_inputs": ["question"], "outputs": ["research_questions"], "timeout_minutes": 10},
        {"name": "search", "agent": "SCHOLAR", "action": "web-research", "required_inputs": ["research_questions"], "outputs": ["raw_data", "sources"], "timeout_minutes": 30},
        {"name": "synthesize", "agent": "QUILL", "action": "write-report", "required_inputs": ["raw_data", "question"], "outputs": ["report"], "timeout_minutes": 25}
    ]'::jsonb
)
ON CONFLICT (name) DO NOTHING;
```

---

## BUILD & VERIFY

```bash
# Add to GAIA or create ATLAS service
# Run migration for pipeline definitions

# Seed pipelines
psql $DEV_DATABASE_URL -c "$(cat seed_pipelines.sql)"

# Test pipeline execution
curl -X POST http://localhost:8000/pipelines/deep-research/execute \
  -H "Content-Type: application/json" \
  -d '{"question": "What are best practices for AI agent architectures?"}'

# Check status
curl http://localhost:8000/pipelines/{execution_id}/status
```

---

## GIT COMMIT

```bash
git add .
git commit -m "Pipeline System: Agent Orchestration

- Pipeline execution engine
- Multi-stage workflow support
- Context passing between agents
- Retry and error handling
- LCIS integration for success/failure reporting
- Seed pipelines: agent-upgrade, content-creation, deep-research
- MCP tools for pipeline management

Agents working together, automatically."
```

---

*"One agent is powerful. Many agents orchestrated? Unstoppable."*
