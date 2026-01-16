# ARIA → OLYMPUS Integration

## Overview

Wire ARIA to route orchestration requests through SENTINEL. After this, you can talk naturally and ARIA will orchestrate your entire agent fleet.

**Time estimate:** 30 minutes

---

## WHAT WE'RE BUILDING

```
User: "Research compliance pain points, then make a plan"
         ↓
      ARIA (Pre-Router detects chain pattern)
         ↓
      SENTINEL /orchestrate
         ↓
      ATLAS (executes chain)
         ↓
      SCHOLAR → CHIRON
         ↓
      ARIA (formats response beautifully)
         ↓
User: Gets research + plan in one response
```

---

## IMPLEMENTATION

### Step 1: Add Pre-Router Code Node to ARIA Workflow

**Location:** DEV ARIA workflow, BEFORE the AI Agent node
**Node type:** Code
**Node name:** "Pre-Router"

```javascript
/**
 * ARIA Pre-Router - Routes to SENTINEL/OLYMPUS
 * 
 * Detects:
 * 1. Chain patterns (research...then...plan)
 * 2. Single agent patterns (ask CHIRON, research X)
 * 3. Default: ARIA handles
 */

const message = $json.message || $json.body?.message || '';
const messageLower = message.toLowerCase();

// ═══════════════════════════════════════════════════════════════════════════
// CHAIN DETECTION - Routes to SENTINEL with chain_name
// ═══════════════════════════════════════════════════════════════════════════

const chainPatterns = [
  { 
    pattern: /research .+ (then|and then|,\s*then|,\s*and) .*(plan|analyze|recommend|decide|create|make)/i, 
    chain: "research-and-plan",
    extract: (msg) => {
      const match = msg.match(/research (.+?) (then|and)/i);
      return { topic: match ? match[1].trim() : msg };
    }
  },
  { 
    pattern: /validate .+ (then|and) .*(decide|plan|recommend)/i, 
    chain: "validate-and-decide",
    extract: (msg) => {
      const match = msg.match(/validate (.+?) (then|and)/i);
      return { assumption: match ? match[1].trim() : msg };
    }
  },
  { 
    pattern: /(comprehensive|full|complete) .*(analysis|research|report)/i, 
    chain: "comprehensive-market-analysis",
    extract: (msg) => {
      const match = msg.match(/(analysis|research|report) .*(on|of|about|for) (.+)/i);
      return { market: match ? match[3].trim() : msg };
    }
  },
  { 
    pattern: /compare .*(niches|markets|industries|verticals)/i, 
    chain: "niche-evaluation",
    extract: (msg) => {
      // Try to extract list of niches
      const match = msg.match(/compare (.+)/i);
      const raw = match ? match[1] : msg;
      const niches = raw.split(/,| and | vs /i).map(n => n.trim()).filter(n => n.length > 0);
      return { niches: niches.length > 0 ? niches : [raw] };
    }
  },
  { 
    pattern: /plan (my|the|this) week/i, 
    chain: "weekly-planning",
    extract: (msg) => ({ raw_message: msg })
  },
  { 
    pattern: /i'?m (afraid|scared|nervous|anxious|avoiding)/i, 
    chain: "fear-to-action",
    extract: (msg) => {
      const match = msg.match(/(?:afraid|scared|nervous|anxious|avoiding) (?:of |about |to )?(.+)/i);
      return { situation: match ? match[1].trim() : msg };
    }
  },
  {
    pattern: /find out .+ (then|and) .*(plan|recommend|create|decide)/i,
    chain: "research-and-plan",
    extract: (msg) => {
      const match = msg.match(/find out (.+?) (then|and)/i);
      return { topic: match ? match[1].trim() : msg };
    }
  },
  {
    pattern: /look up .+ (then|and) .*(plan|strategy|recommend)/i,
    chain: "research-and-plan",
    extract: (msg) => {
      const match = msg.match(/look up (.+?) (then|and)/i);
      return { topic: match ? match[1].trim() : msg };
    }
  }
];

// Check for chain patterns
for (const { pattern, chain, extract } of chainPatterns) {
  if (pattern.test(messageLower)) {
    const input = extract(message);
    input.raw_message = message;
    
    return {
      json: {
        ...$json,
        route: 'sentinel',
        sentinel_payload: {
          source: 'aria',
          chain_name: chain,
          input: input
        },
        original_message: message
      }
    };
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// SINGLE AGENT DETECTION - Routes to SENTINEL with single step
// ═══════════════════════════════════════════════════════════════════════════

// CHIRON patterns
const chironPatterns = [
  { pattern: /\b(ask chiron|chiron,|hey chiron)/i, action: 'chat' },
  { pattern: /\b(sprint plan|plan my (day|week)|daily plan)/i, action: 'sprint-plan' },
  { pattern: /\b(pricing|how much should i charge|price this|what to charge)/i, action: 'pricing-help' },
  { pattern: /\b(fear check|what am i afraid of|why am i avoiding)/i, action: 'fear-check' },
  { pattern: /\b(weekly review|what did i accomplish|review my week)/i, action: 'weekly-review' },
  { pattern: /\b(accountability|hold me accountable|check on me)/i, action: 'accountability' },
  { pattern: /\b(hype me|motivate me|pump me up|i need motivation)/i, action: 'hype' },
  { pattern: /\b(business strategy|strategic advice|should i focus)/i, action: 'chat' },
  { pattern: /\b(adhd|staying focused|can't focus|overwhelmed|paralyzed)/i, action: 'chat' }
];

for (const { pattern, action } of chironPatterns) {
  if (pattern.test(messageLower)) {
    let params = { message: message };
    
    // Special params for specific actions
    if (action === 'sprint-plan') {
      params = { goals: [message], time_available: 'this week', energy_level: 'medium' };
    } else if (action === 'pricing-help') {
      params = { service_description: message };
    } else if (action === 'fear-check') {
      params = { situation: message, what_im_avoiding: 'unknown' };
    } else if (action === 'weekly-review') {
      params = { wins: [], losses: [], lessons: [] };
    } else if (action === 'hype') {
      params = {};
    }
    
    return {
      json: {
        ...$json,
        route: 'sentinel',
        sentinel_payload: {
          source: 'aria',
          type: 'single',
          steps: [{
            id: 'chiron_call',
            agent: 'chiron',
            action: action,
            params: params
          }],
          input: { raw_message: message }
        },
        original_message: message
      }
    };
  }
}

// SCHOLAR patterns
const scholarPatterns = [
  { pattern: /\b(ask scholar|scholar,|hey scholar)/i, action: 'deep-research' },
  { pattern: /\b(research|look up|find out about|investigate|dig into)/i, action: 'deep-research' },
  { pattern: /\b(competitor|competition|who else does|competing with)/i, action: 'competitors' },
  { pattern: /\b(market size|tam|sam|som|how big is the market)/i, action: 'market-size' },
  { pattern: /\b(icp|ideal customer|who should i target|target customer)/i, action: 'icp' },
  { pattern: /\b(niche analysis|analyze .* niche|which niche)/i, action: 'niche' },
  { pattern: /\b(pain points?|what problems|customer problems)/i, action: 'pain-discovery' },
  { pattern: /\b(validate|is it true|test assumption|assumption)/i, action: 'validate-assumption' }
];

for (const { pattern, action } of scholarPatterns) {
  if (pattern.test(messageLower)) {
    let params = { question: message };
    
    // Special params for specific actions
    if (action === 'competitors') {
      params = { niche: message };
    } else if (action === 'market-size') {
      params = { market: message };
    } else if (action === 'icp') {
      params = { niche: message };
    } else if (action === 'niche') {
      params = { niche: message };
    } else if (action === 'pain-discovery') {
      params = { role: 'compliance officer', industry: 'water utilities' };
    } else if (action === 'validate-assumption') {
      params = { assumption: message, importance: 'high' };
    }
    
    return {
      json: {
        ...$json,
        route: 'sentinel',
        sentinel_payload: {
          source: 'aria',
          type: 'single',
          steps: [{
            id: 'scholar_call',
            agent: 'scholar',
            action: action,
            params: params
          }],
          input: { raw_message: message }
        },
        original_message: message
      }
    };
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// DEFAULT: ARIA HANDLES NORMALLY
// ═══════════════════════════════════════════════════════════════════════════

return {
  json: {
    ...$json,
    route: 'aria',
    original_message: message
  }
};
```

---

### Step 2: Add Switch Node After Pre-Router

**Node type:** Switch
**Node name:** "Route Switch"
**Conditions:**

| Output | Condition |
|--------|-----------|
| SENTINEL | `{{ $json.route }}` equals `sentinel` |
| ARIA | Default (fallback) |

---

### Step 3: Add HTTP Request Node for SENTINEL

**Node type:** HTTP Request
**Node name:** "SENTINEL Orchestrate"
**Connect from:** Switch node "SENTINEL" output

**Configuration:**
```
Method: POST
URL: http://sentinel:8019/orchestrate
Authentication: None
Body Content Type: JSON
Body:
  {{ JSON.stringify($json.sentinel_payload) }}
Headers:
  Content-Type: application/json
Timeout: 180000 (3 minutes for chains)
```

---

### Step 4: Add Response Formatter Code Node

**Node type:** Code
**Node name:** "Format Orchestration Response"
**Connect from:** SENTINEL Orchestrate node

```javascript
/**
 * Format SENTINEL/ATLAS orchestration results for human-friendly display
 */

const result = $json;
const originalMessage = $('Pre-Router').first().json.original_message || 'your request';

// Check for errors
if (result.status === 'failed') {
  const errorMsg = result.errors?.map(e => e.error).join('\n') || result.error || 'Unknown error';
  return {
    json: {
      message: `❌ **Orchestration Failed**\n\nI tried to help with "${originalMessage}" but encountered an error:\n\n${errorMsg}\n\nWant me to try a different approach?`,
      mode: 'DEFAULT',
      orchestration_failed: true
    }
  };
}

// Get step outputs
const stepOutputs = result.step_outputs || result.step_results || {};
const stepsCompleted = Object.keys(stepOutputs).length;
const routedTo = result._routed_to || 'atlas';
const totalCost = result.total_cost || 0;
const durationMs = result.duration_ms || 0;

let formatted = '';

// ─────────────────────────────────────────────────────────────────────────────
// SINGLE AGENT RESULT
// ─────────────────────────────────────────────────────────────────────────────

if (stepsCompleted === 1) {
  const [stepId, step] = Object.entries(stepOutputs)[0];
  const agent = (step.agent || stepId).toUpperCase();
  const output = step.output || step;
  
  // Extract the main content
  const content = output.response || 
                  output.research || 
                  output.sprint_plan ||
                  output.daily_priorities ||
                  output.pricing_strategy || 
                  output.price_recommendation ||
                  output.fear_analysis ||
                  output.fear_named ||
                  output.message ||
                  (typeof output === 'object' ? JSON.stringify(output, null, 2) : String(output));
  
  // Agent-specific icons
  const icons = {
    'CHIRON': '🎯',
    'SCHOLAR': '📚',
    'HERMES': '📨',
    'CHRONOS': '⏰',
    'HADES': '🔄',
    'AEGIS': '🔐',
    'ARGUS': '👁️',
    'ATHENA': '📝',
    'ALOY': '🔍'
  };
  const icon = icons[agent] || '🤖';
  
  formatted = `${icon} **${agent}:**\n\n${content}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// CHAIN RESULT (Multiple Steps)
// ─────────────────────────────────────────────────────────────────────────────

else if (stepsCompleted > 1) {
  formatted = `🔗 **Multi-Agent Analysis Complete** *(${stepsCompleted} steps)*\n\n`;
  
  // Use formatted_output if available (from chain template)
  if (result.formatted_output) {
    formatted += result.formatted_output;
  } else {
    // Build from step outputs
    for (const [stepId, step] of Object.entries(stepOutputs)) {
      const agent = (step.agent || stepId).toUpperCase();
      const output = step.output || step;
      
      // Handle parallel step (nested outputs)
      if (output && typeof output === 'object' && !output.response && !output.research) {
        // Check if this is a parallel result with substeps
        const hasSubsteps = Object.values(output).some(v => v && typeof v === 'object');
        if (hasSubsteps) {
          formatted += `### Parallel Research\n\n`;
          for (const [subId, subOutput] of Object.entries(output)) {
            if (subOutput && typeof subOutput === 'object') {
              const subContent = subOutput.research || subOutput.response || 
                                JSON.stringify(subOutput, null, 2).substring(0, 800);
              formatted += `**${subId.toUpperCase()}:**\n${subContent}\n\n`;
            }
          }
          formatted += `---\n\n`;
          continue;
        }
      }
      
      // Regular step output
      const content = output.response || 
                      output.research || 
                      output.sprint_plan ||
                      output.pricing_strategy ||
                      output.fear_analysis ||
                      (typeof output === 'object' ? JSON.stringify(output, null, 2).substring(0, 1500) : String(output));
      
      const icons = { 'CHIRON': '🎯', 'SCHOLAR': '📚' };
      const icon = icons[agent] || '🤖';
      
      formatted += `### ${icon} ${agent}\n\n${content}\n\n---\n\n`;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ADD FOOTER
// ─────────────────────────────────────────────────────────────────────────────

// Only add cost footer if there was a cost
if (totalCost > 0.001) {
  const durationSec = (durationMs / 1000).toFixed(1);
  formatted += `\n\n*💰 $${totalCost.toFixed(4)} | ⚡ ${routedTo} | ⏱️ ${durationSec}s*`;
}

return {
  json: {
    message: formatted,
    orchestration_result: result,
    mode: stepsCompleted > 1 ? 'STRATEGY' : 'FOCUS',
    agent_used: stepsCompleted === 1 ? Object.values(stepOutputs)[0]?.agent : 'multiple'
  }
};
```

---

### Step 5: Merge Back to Response Handler

**Connect:** "Format Orchestration Response" → Your existing response/output node

The formatted message should go to wherever ARIA normally sends responses.

---

## WORKFLOW STRUCTURE

```
[Webhook/Chat Input]
         ↓
    [Pre-Router]  ←── New Code node
         ↓
    [Route Switch] ←── New Switch node
         ↓
    ├── SENTINEL branch:
    │        ↓
    │   [SENTINEL Orchestrate] ←── New HTTP Request
    │        ↓
    │   [Format Orchestration Response] ←── New Code node
    │        ↓
    │   [Merge] ──────────────────────────────┐
    │                                         │
    └── ARIA branch:                          │
             ↓                                │
        [Existing ARIA AI Agent]              │
             ↓                                │
        [Merge] ←─────────────────────────────┘
             ↓
      [Response Handler]
```

---

## NETWORK CONFIGURATION

Ensure ARIA's n8n can reach SENTINEL:

**Option A:** If ARIA workflow is in `stack_net`:
```yaml
# SENTINEL needs to be on stack_net
networks:
  - control-plane-net
  - stack_net
```

**Option B:** Use Docker bridge IP:
```
URL: http://172.17.0.1:8019/orchestrate
```

**Option C:** Use host.docker.internal (if on Docker Desktop):
```
URL: http://host.docker.internal:8019/orchestrate
```

---

## TESTING

### Test 1: Chain Detection
```
User: "Research compliance automation pricing, then recommend our pricing strategy"
Expected: Routes to SENTINEL → research-and-plan chain → SCHOLAR → CHIRON
```

### Test 2: Single Agent (CHIRON)
```
User: "I'm feeling overwhelmed about outreach"
Expected: Routes to SENTINEL → single step → CHIRON fear-check
```

### Test 3: Single Agent (SCHOLAR)
```
User: "Research water utility compliance pain points"
Expected: Routes to SENTINEL → single step → SCHOLAR deep-research
```

### Test 4: Default (ARIA handles)
```
User: "What's on my calendar today?"
Expected: Routes to ARIA (no SENTINEL)
```

### Test 5: Comprehensive Analysis
```
User: "Give me a comprehensive analysis of the compliance automation market"
Expected: Routes to SENTINEL → comprehensive-market-analysis chain → Parallel SCHOLAR calls → CHIRON synthesis
```

---

## EXAMPLE INTERACTIONS

### Before (without OLYMPUS)
```
You: "Research compliance pain points, then make a plan"
ARIA: "I'd be happy to help! What specific compliance area..."
[You have to manually ask SCHOLAR, then manually ask CHIRON]
```

### After (with OLYMPUS)
```
You: "Research compliance pain points, then make a plan"

🔗 **Multi-Agent Analysis Complete** (2 steps)

### 📚 SCHOLAR

Water utility compliance officers face significant pain points:

1. **Regulatory Complexity** - EPA, state, and local regulations overlap...
2. **Documentation Burden** - Average 40+ hours/month on paperwork...
3. **Audit Anxiety** - 73% report stress about upcoming audits...
[continued research...]

---

### 🎯 CHIRON

Based on this research, here's your action plan:

**This Week's Priority:** Address Documentation Burden (highest pain, clearest value)

**Day 1-2:** Create automated report template...
**Day 3-4:** Build proof-of-concept workflow...
**Day 5:** Reach out to 3 compliance officers...

*💰 $0.2034 | ⚡ fastapi | ⏱️ 45.2s*
```

---

## SUCCESS CRITERIA

- [ ] Pre-Router correctly detects chain patterns
- [ ] Pre-Router correctly detects single agent patterns
- [ ] Switch routes to SENTINEL vs ARIA correctly
- [ ] SENTINEL HTTP request succeeds
- [ ] Response formatter handles single agent results
- [ ] Response formatter handles chain results
- [ ] Response formatter handles errors gracefully
- [ ] Default messages still handled by ARIA
- [ ] Cost and timing displayed in footer

---

## TROUBLESHOOTING

### "Connection refused" to SENTINEL
- Check SENTINEL is running: `curl http://localhost:8019/health`
- Check network connectivity from n8n container
- Try Docker bridge IP: `http://172.17.0.1:8019`

### "Timeout" on chains
- Increase HTTP Request timeout to 180000ms (3 min)
- Check SCHOLAR/CHIRON are running
- Check Event Bus isn't bottlenecking

### "undefined" in response
- Check step output paths in formatter
- Add console.log to debug actual response structure
- Verify ATLAS is returning expected format

---

## GIT COMMIT MESSAGE

```
Wire ARIA to OLYMPUS orchestration system

- Add Pre-Router for intent detection
- Route chains and agent calls through SENTINEL
- Format multi-agent responses beautifully
- Display cost and timing in footer
- Fallback to ARIA for normal chat
```
