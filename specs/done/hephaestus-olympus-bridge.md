# HEPHAESTUS → OLYMPUS Direct Connection

## Overview

Update HEPHAESTUS MCP server so Claude Web can orchestrate agents directly through ATLAS/SENTINEL, eliminating the need for user to be a go-between.

**After this:** Claude Web says "Let me research that" → calls ATLAS → gets results → synthesizes response. Fully automated.

---

## CURRENT STATE

```python
# HEPHAESTUS call_agent currently routes through Event Bus
# Doesn't hit new ATLAS orchestrator on 8007 or SENTINEL on 8019
```

## TARGET STATE

```
Claude Web: "Research X and plan Y"
     ↓
HEPHAESTUS:orchestrate tool
     ↓
SENTINEL (8019) or ATLAS (8007)
     ↓
SCHOLAR → CHIRON (or any chain)
     ↓
Results back to Claude Web
     ↓
Claude synthesizes and responds to user
```

---

## IMPLEMENTATION

### Step 1: Add orchestrate tool to HEPHAESTUS

**File:** `/opt/leveredge/control-plane/agents/hephaestus/hephaestus.py`

Add new endpoint and tool definition:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION - Direct ATLAS/SENTINEL Integration
# ═══════════════════════════════════════════════════════════════════════════════

SENTINEL_URL = os.getenv("SENTINEL_URL", "http://sentinel:8019")
ATLAS_URL = os.getenv("ATLAS_URL", "http://atlas:8007")

@app.post("/orchestrate")
async def orchestrate(request: dict):
    """
    Execute orchestration through SENTINEL/ATLAS.
    
    Supports:
    - Pre-defined chains by name
    - Single agent calls
    - Ad-hoc chains
    """
    import httpx
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            # Route through SENTINEL for smart routing
            response = await client.post(
                f"{SENTINEL_URL}/orchestrate",
                json=request
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            # Fallback to ATLAS directly if SENTINEL is down
            response = await client.post(
                f"{ATLAS_URL}/execute",
                json=request
            )
            response.raise_for_status()
            result = response.json()
            result["_fallback"] = "atlas_direct"
            return result
        except Exception as e:
            return {"error": str(e), "status": "failed"}

@app.post("/orchestrate/chain/{chain_name}")
async def orchestrate_chain(chain_name: str, input_data: dict = {}):
    """
    Execute a pre-defined chain by name.
    
    Chains: research-and-plan, validate-and-decide, comprehensive-market-analysis,
            niche-evaluation, weekly-planning, fear-to-action
    """
    request = {
        "source": "hephaestus",
        "chain_name": chain_name,
        "input": input_data
    }
    return await orchestrate(request)

@app.post("/orchestrate/agent/{agent}/{action}")
async def orchestrate_single(agent: str, action: str, params: dict = {}):
    """
    Execute single agent action.
    
    Agents: scholar, chiron, hermes, chronos, hades, aegis, argus, aloy, athena
    """
    request = {
        "source": "hephaestus",
        "type": "single",
        "steps": [{
            "id": f"{agent}_{action}",
            "agent": agent,
            "action": action,
            "params": params
        }]
    }
    return await orchestrate(request)

@app.get("/orchestrate/chains")
async def list_chains():
    """List available orchestration chains."""
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{ATLAS_URL}/chains")
            return response.json()
        except:
            return {
                "chains": [
                    {"name": "research-and-plan", "description": "Research topic, then create action plan"},
                    {"name": "validate-and-decide", "description": "Validate assumption, then decide next steps"},
                    {"name": "comprehensive-market-analysis", "description": "Parallel research, then synthesis"},
                    {"name": "niche-evaluation", "description": "Compare niches, recommend best"},
                    {"name": "weekly-planning", "description": "Review, research blockers, plan week"},
                    {"name": "fear-to-action", "description": "Analyze fear, find evidence, create action plan"}
                ]
            }

@app.get("/orchestrate/agents")
async def list_agents():
    """List available agents for orchestration."""
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{ATLAS_URL}/agents")
            return response.json()
        except:
            return {
                "agents": [
                    {"name": "scholar", "description": "Market research with web search"},
                    {"name": "chiron", "description": "Business strategy and ADHD planning"},
                    {"name": "hermes", "description": "Notifications"},
                    {"name": "chronos", "description": "Backups"},
                    {"name": "hades", "description": "Rollback"},
                    {"name": "aegis", "description": "Credentials"},
                    {"name": "argus", "description": "Monitoring"},
                    {"name": "aloy", "description": "Audit"},
                    {"name": "athena", "description": "Documentation"}
                ]
            }
```

---

### Step 2: Update MCP Tool Definitions

**File:** `/opt/leveredge/control-plane/agents/hephaestus/mcp_tools.json` (or wherever tools are defined)

Add new tools:

```json
{
  "name": "orchestrate",
  "description": "Execute an orchestration through OLYMPUS (ATLAS/SENTINEL). Can run pre-defined chains like research-and-plan, or single agent calls. Use this to have agents do work automatically.",
  "parameters": {
    "type": "object",
    "properties": {
      "chain_name": {
        "type": "string",
        "description": "Pre-defined chain to execute: research-and-plan, validate-and-decide, comprehensive-market-analysis, niche-evaluation, weekly-planning, fear-to-action",
        "enum": ["research-and-plan", "validate-and-decide", "comprehensive-market-analysis", "niche-evaluation", "weekly-planning", "fear-to-action"]
      },
      "input": {
        "type": "object",
        "description": "Input data for the chain. For research-and-plan: {topic: '...'}. For validate-and-decide: {assumption: '...'}. For fear-to-action: {situation: '...'}"
      },
      "agent": {
        "type": "string",
        "description": "For single agent calls: scholar, chiron, hermes, chronos, hades, aegis, argus"
      },
      "action": {
        "type": "string", 
        "description": "For single agent calls: the action to perform (e.g., deep-research, sprint-plan, chat)"
      },
      "params": {
        "type": "object",
        "description": "Parameters for single agent action"
      }
    }
  }
}
```

---

### Step 3: Update HEPHAESTUS MCP Server Handler

**File:** `/opt/leveredge/control-plane/agents/hephaestus/mcp_server.py` (or equivalent)

Add tool handler:

```python
async def handle_orchestrate(arguments: dict) -> str:
    """Handle orchestrate tool calls from Claude."""
    import httpx
    
    # Determine request type
    if arguments.get("chain_name"):
        # Chain execution
        request = {
            "source": "claude_web",
            "chain_name": arguments["chain_name"],
            "input": arguments.get("input", {})
        }
    elif arguments.get("agent") and arguments.get("action"):
        # Single agent call
        request = {
            "source": "claude_web",
            "type": "single",
            "steps": [{
                "id": f"{arguments['agent']}_{arguments['action']}",
                "agent": arguments["agent"],
                "action": arguments["action"],
                "params": arguments.get("params", {})
            }]
        }
    else:
        return "Error: Must provide either chain_name or agent+action"
    
    # Execute through SENTINEL
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                "http://sentinel:8019/orchestrate",
                json=request
            )
            result = response.json()
            
            # Format response for Claude
            if result.get("status") == "failed":
                return f"Orchestration failed: {result.get('error', 'Unknown error')}"
            
            # Extract useful content
            outputs = result.get("step_outputs", result.get("step_results", {}))
            formatted_parts = []
            
            for step_id, step in outputs.items():
                output = step.get("output", step)
                content = (output.get("response") or 
                          output.get("research") or 
                          output.get("sprint_plan") or
                          output.get("pricing_strategy") or
                          output.get("fear_analysis") or
                          str(output))
                agent = step.get("agent", step_id).upper()
                formatted_parts.append(f"**{agent}:**\n{content}")
            
            response_text = "\n\n---\n\n".join(formatted_parts)
            
            # Add metadata
            cost = result.get("total_cost", 0)
            duration = result.get("duration_ms", 0)
            if cost > 0:
                response_text += f"\n\n*Cost: ${cost:.4f} | Duration: {duration}ms*"
            
            return response_text
            
        except Exception as e:
            return f"Orchestration error: {str(e)}"

# Add to tool handlers
TOOL_HANDLERS = {
    # ... existing handlers ...
    "orchestrate": handle_orchestrate
}
```

---

### Step 4: Update Docker Environment

**File:** `/opt/leveredge/control-plane/agents/hephaestus/Dockerfile` or `docker-compose.yml`

Ensure HEPHAESTUS can reach SENTINEL and ATLAS:

```yaml
hephaestus:
  # ... existing config ...
  environment:
    - SENTINEL_URL=http://sentinel:8019
    - ATLAS_URL=http://atlas:8007
  networks:
    - control-plane-net
    - stack_net
```

---

### Step 5: Rebuild HEPHAESTUS

```bash
cd /opt/leveredge/control-plane
docker-compose build hephaestus
docker-compose up -d hephaestus
```

---

## USAGE EXAMPLES

### Claude Web orchestrating research + plan:
```
User: "I need to understand the compliance market"

Claude: Let me research that and create a plan for you.

[Calls HEPHAESTUS:orchestrate with chain_name="research-and-plan", input={topic: "compliance automation market"}]

Based on the research and analysis from my agents:

**SCHOLAR found:**
- Market size is $X billion...
- Key competitors include...
- Main pain points are...

**CHIRON recommends:**
- Focus on water utilities first because...
- Week 1 priorities: ...
- Key risk to watch: ...

This cost $0.21 and took 45 seconds to gather. Want me to dig deeper on any area?
```

### Claude Web single agent call:
```
User: "What should I focus on today?"

Claude: Let me check with CHIRON.

[Calls HEPHAESTUS:orchestrate with agent="chiron", action="sprint-plan", params={goals: ["launch prep"], time_available: "today"}]

CHIRON says your ONE priority today is: ...
```

### Claude Web parallel research:
```
User: "Give me a full market analysis"

Claude: Running comprehensive analysis - this will take about a minute.

[Calls HEPHAESTUS:orchestrate with chain_name="comprehensive-market-analysis", input={market: "compliance automation"}]

Here's the full analysis with competitor research, market sizing, and pain point discovery all synthesized together...
```

---

## TESTING

### Test 1: Chain via HEPHAESTUS
```bash
curl -X POST http://localhost:8011/orchestrate/chain/research-and-plan \
  -H "Content-Type: application/json" \
  -d '{"topic": "AEGIS credential management best practices"}'
```

### Test 2: Single agent via HEPHAESTUS
```bash
curl -X POST http://localhost:8011/orchestrate/agent/chiron/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What should I focus on today?"}'
```

### Test 3: List chains
```bash
curl http://localhost:8011/orchestrate/chains
```

### Test 4: MCP tool call (simulate)
```bash
# This would be called by Claude via MCP
curl -X POST http://localhost:8011/mcp/tools/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"chain_name": "fear-to-action", "input": {"situation": "cold outreach"}}'
```

---

## SUCCESS CRITERIA

- [ ] `/orchestrate` endpoint works on HEPHAESTUS
- [ ] Chain execution works via HEPHAESTUS
- [ ] Single agent calls work via HEPHAESTUS
- [ ] MCP tool `orchestrate` available to Claude Web
- [ ] Claude Web can execute chains without user intervention
- [ ] Fallback to ATLAS works if SENTINEL is down
- [ ] Response formatted nicely for Claude to synthesize

---

## WHAT CLAUDE WEB GAINS

| Before | After |
|--------|-------|
| "User, please run this curl command" | "Let me do that for you" |
| Wait for user to paste results | Get results directly |
| Manual back-and-forth | Automated orchestration |
| User is the go-between | Claude orchestrates directly |

---

## GIT COMMIT MESSAGE

```
Add HEPHAESTUS → OLYMPUS orchestration bridge

- Add /orchestrate endpoint to HEPHAESTUS
- Add /orchestrate/chain/{name} for named chains
- Add /orchestrate/agent/{agent}/{action} for single calls
- Add MCP tool definition for orchestrate
- Enable Claude Web to call ATLAS/SENTINEL directly
- Automatic fallback if SENTINEL is down
```
