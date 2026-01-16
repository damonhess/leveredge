# ARIA Agent Routing V2 - Chained Orchestration

## Overview
Enable ARIA to:
1. Route single requests to CHIRON or SCHOLAR
2. **Chain requests**: SCHOLAR → CHIRON → response
3. Handle complex multi-step instructions naturally

---

## CHAIN DETECTION

### Chain Trigger Patterns
```javascript
const chainPatterns = [
  /research .+ (then|and then|,\s*then|,\s*and) .*(plan|analyze|recommend|decide|advise)/i,
  /find out .+ (then|and then|,\s*then) .*(plan|recommend)/i,
  /look up .+ (and|then) .*(create|build|make) .*(plan|strategy|roadmap)/i,
  /(scholar|research) .+ (chiron|plan|strategy)/i,
  /analyze .+ and .*(recommend|suggest|advise)/i,
  /investigate .+ report back .*(with|including) .*(plan|recommendation)/i,
];
```

### Examples That Trigger Chains
- "Research compliance pain points, then make a plan to address them"
- "Find out what competitors charge and recommend our pricing"
- "Look up water utility regulations and create a compliance checklist"
- "Investigate the market and advise on our niche"
- "SCHOLAR research X, CHIRON plan Y"

---

## ROUTING LOGIC (UPDATED)

```javascript
// Pre-Router V2: Single-hop OR chained routing
const message = $json.message;
const messageLower = message.toLowerCase();

// === CHAIN DETECTION ===
const chainPatterns = [
  /research .+ (then|and then|,\s*then|,\s*and) .*(plan|analyze|recommend|decide|advise|create|build|make)/i,
  /find out .+ (then|and then|,\s*then) .*(plan|recommend|create)/i,
  /look up .+ (and|then) .*(plan|strategy|roadmap|checklist)/i,
  /(scholar|research) .+ (chiron|plan|strategy)/i,
  /analyze .+ and .*(recommend|suggest|advise)/i,
  /investigate .+ report .*(plan|recommendation)/i,
  /what .+ (and|then) .*(should i|how do i|plan)/i,
];

const isChain = chainPatterns.some(pattern => pattern.test(messageLower));

if (isChain) {
  // Parse the chain into steps
  const parts = message.split(/,?\s*(then|and then|and)\s*/i);
  
  return {
    json: {
      ...$json,
      route: 'chain',
      chain_steps: [
        {
          agent: 'scholar',
          endpoint: '/deep-research',
          payload: { question: parts[0].trim() }
        },
        {
          agent: 'chiron', 
          endpoint: '/chat',
          payload_template: {
            message: `Based on this research:\n\n{{SCHOLAR_RESPONSE}}\n\n${parts.slice(1).join(' ').trim()}`
          }
        }
      ],
      original_message: message
    }
  };
}

// === SINGLE-HOP ROUTING (unchanged from V1) ===

// CHIRON triggers
const chironExplicit = /\b(ask chiron|have chiron|tell chiron|chiron,)/i;
const chironImplicit = /\b(sprint plan|plan my (week|day)|pricing|how much should i charge|price this|i'm afraid|i'm avoiding|fear check|weekly review|what did i accomplish|procrastinating|call me out|accountability|business strategy|should i focus|adhd|staying focused|overwhelmed)\b/i;

// SCHOLAR triggers  
const scholarExplicit = /\b(ask scholar|have scholar|tell scholar|scholar,|research this|look up|find out about)/i;
const scholarImplicit = /\b(competitor|competition|who else does|market size|tam|sam|som|how big is the market|icp|ideal customer|who should i target|niche|which industry|what vertical|pain points|what problems do they have|validate|is it true that|assumption)\b/i;

let route = 'aria';
let endpoint = null;
let payload = null;

if (chironExplicit.test(messageLower) || chironImplicit.test(messageLower)) {
  route = 'chiron';
  
  if (/sprint|plan my (week|day)/i.test(messageLower)) {
    endpoint = '/sprint-plan';
    payload = { goals: [message], time_available: 'this week' };
  } else if (/pricing|how much|charge/i.test(messageLower)) {
    endpoint = '/pricing-help';
    payload = { service_description: message };
  } else if (/afraid|avoiding|fear/i.test(messageLower)) {
    endpoint = '/fear-check';
    payload = { situation: message };
  } else if (/weekly review|accomplish/i.test(messageLower)) {
    endpoint = '/weekly-review';
    payload = { wins: [], losses: [] };
  } else {
    endpoint = '/chat';
    payload = { message: message };
  }
} else if (scholarExplicit.test(messageLower) || scholarImplicit.test(messageLower)) {
  route = 'scholar';
  
  if (/competitor|competition/i.test(messageLower)) {
    endpoint = '/deep-research';
    payload = { question: message };
  } else if (/market size|tam|sam|som/i.test(messageLower)) {
    endpoint = '/market-size';
    payload = { market: message };
  } else if (/pain point|problems/i.test(messageLower)) {
    endpoint = '/pain-discovery';
    payload = { role: 'compliance officer', industry: 'water utilities' };
  } else if (/validate|assumption/i.test(messageLower)) {
    endpoint = '/validate-assumption';
    payload = { assumption: message };
  } else {
    endpoint = '/deep-research';
    payload = { question: message };
  }
}

return {
  json: {
    ...$json,
    route: route,
    agent_endpoint: endpoint,
    agent_payload: payload,
    original_message: message
  }
};
```

---

## CHAIN EXECUTION NODE

After Pre-Router, add a Code node for chain execution:

```javascript
// Chain Executor: Runs multi-step agent chains
const routeInfo = $json;

if (routeInfo.route !== 'chain') {
  // Not a chain, pass through
  return { json: routeInfo };
}

const steps = routeInfo.chain_steps;
let previousResponse = '';

// This would need to be async with HTTP requests
// For n8n, we'll use a Loop + HTTP Request pattern instead

return {
  json: {
    ...routeInfo,
    chain_ready: true,
    current_step: 0,
    total_steps: steps.length,
    accumulated_context: ''
  }
};
```

---

## WORKFLOW STRUCTURE FOR CHAINS

### Using n8n Loop Pattern

```
Pre-Router
    ↓
Switch Node
    ├── route = "chain" → Chain Handler Branch
    ├── route = "chiron" → CHIRON HTTP Request
    ├── route = "scholar" → SCHOLAR HTTP Request  
    └── route = "aria" → ARIA AI Agent

Chain Handler Branch:
    ↓
Step 1: SCHOLAR HTTP Request
    URL: http://scholar:8018{{ $json.chain_steps[0].endpoint }}
    Body: {{ $json.chain_steps[0].payload }}
    ↓
Capture SCHOLAR Response
    ↓
Step 2: CHIRON HTTP Request
    URL: http://chiron:8017{{ $json.chain_steps[1].endpoint }}
    Body: {
      "message": "Based on this research:\n\n{{ $('SCHOLAR HTTP').item.json.research }}\n\nNow: {{ $json.chain_steps[1].payload_template.message.split('{{SCHOLAR_RESPONSE}}')[1] }}"
    }
    ↓
Format Chain Response
    ↓
Merge to Output
```

---

## ALTERNATIVE: SIMPLER CHAIN EXECUTOR (Recommended)

Instead of complex loop logic, use a dedicated **Chain Executor Code Node** that makes sequential HTTP calls:

```javascript
// Chain Executor - makes HTTP calls in sequence
const { chain_steps, original_message } = $json;

// Helper to make HTTP request (n8n's built-in fetch)
async function callAgent(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return await response.json();
}

// Step 1: Call SCHOLAR
const scholarUrl = `http://scholar:8018${chain_steps[0].endpoint}`;
const scholarResult = await callAgent(scholarUrl, chain_steps[0].payload);
const scholarResponse = scholarResult.research || scholarResult.response || JSON.stringify(scholarResult);

// Step 2: Call CHIRON with SCHOLAR's output
const chironPayload = {
  message: chain_steps[1].payload_template.message.replace('{{SCHOLAR_RESPONSE}}', scholarResponse)
};
const chironUrl = `http://chiron:8017${chain_steps[1].endpoint}`;
const chironResult = await callAgent(chironUrl, chironPayload);
const chironResponse = chironResult.response || chironResult.sprint_plan || JSON.stringify(chironResult);

// Format combined response
return {
  json: {
    message: `## Research (SCHOLAR)\n\n${scholarResponse}\n\n---\n\n## Analysis & Plan (CHIRON)\n\n${chironResponse}`,
    chain_executed: true,
    agents_used: ['SCHOLAR', 'CHIRON'],
    original_message: original_message
  }
};
```

**Note:** n8n Code nodes support async/await and fetch in newer versions. If not available, use sequential HTTP Request nodes instead.

---

## RESPONSE FORMATTER (UPDATED)

```javascript
// Post-Router V2: Format single or chained responses
const route = $('Pre-Router').first().json.route;

if (route === 'chain') {
  // Chain response already formatted by executor
  const chainResult = $json;
  return {
    json: {
      message: `🔗 **Multi-Agent Analysis Complete**\n\n${chainResult.message}`,
      agents_used: chainResult.agents_used,
      mode: 'STRATEGY'
    }
  };
}

// Single-hop responses (unchanged)
const agentResponse = $json.response || $json.research || $json.sprint_plan || $json.pricing_strategy || $json.fear_analysis;

if (route === 'chiron') {
  return {
    json: {
      message: `🎯 **CHIRON:**\n\n${agentResponse}`,
      agent_used: 'CHIRON',
      mode: 'STRATEGY'
    }
  };
} else if (route === 'scholar') {
  return {
    json: {
      message: `📚 **SCHOLAR:**\n\n${agentResponse}`,
      agent_used: 'SCHOLAR', 
      mode: 'FOCUS'
    }
  };
}

return $json;
```

---

## EXAMPLE INTERACTIONS

### Single-Hop (unchanged)
```
User: "What are compliance pain points?"
ARIA: Routes to SCHOLAR /deep-research
Response: "📚 SCHOLAR: [research results]"
```

### Chained
```
User: "Research water utility compliance gaps, then make a plan to address them"
ARIA: 
  1. Routes to SCHOLAR /deep-research
  2. Takes SCHOLAR response
  3. Routes to CHIRON /chat with research context
  4. Returns combined response

Response: 
"🔗 Multi-Agent Analysis Complete

## Research (SCHOLAR)
[SCHOLAR's findings about compliance gaps]

---

## Analysis & Plan (CHIRON)  
[CHIRON's strategic plan based on the research]"
```

### Complex Chain
```
User: "Find out what competitors charge for compliance automation, then recommend our pricing strategy"
ARIA:
  1. SCHOLAR researches competitor pricing
  2. CHIRON analyzes and recommends pricing

Response: Combined research + pricing recommendation
```

---

## COST TRACKING FOR CHAINS

Update cost logging to track both agents:

```javascript
// Log chain costs
if (route === 'chain') {
  // Log SCHOLAR usage
  await log_llm_usage('SCHOLAR', '/deep-research', 'claude-sonnet', scholarResult._usage);
  
  // Log CHIRON usage  
  await log_llm_usage('CHIRON', '/chat', 'claude-sonnet', chironResult._usage);
  
  // Log chain event
  await logToEventBus({
    event_type: 'agent_chain',
    agents: ['SCHOLAR', 'CHIRON'],
    total_cost: scholarCost + chironCost
  });
}
```

---

## TESTING

### Test Single-Hop
```
"What are my competitors doing?" → SCHOLAR only
"Plan my week" → CHIRON only
"What time is it?" → ARIA only
```

### Test Chains
```
"Research compliance software market, then advise on our positioning" → SCHOLAR → CHIRON
"Find water utility pain points and create a plan to address them" → SCHOLAR → CHIRON
"Look up AEGIS best practices and recommend enhancements" → SCHOLAR → CHIRON
```

---

## SUCCESS CRITERIA

- [ ] Single-hop routing works (V1 functionality)
- [ ] Chain detection triggers on "research X, then plan Y"
- [ ] SCHOLAR executes first in chain
- [ ] SCHOLAR output feeds into CHIRON prompt
- [ ] Combined response formatted clearly
- [ ] Cost tracking logs both agents
- [ ] Works from aria.leveredgeai.com

---

## GIT COMMIT

```
ARIA Agent Routing V2 - Chained orchestration

- Single-hop: ARIA → CHIRON or SCHOLAR
- Chained: ARIA → SCHOLAR → CHIRON → response
- Pattern: "research X, then plan Y" triggers chain
- Combined response with clear agent attribution
- Cost tracking for both agents in chain
```
