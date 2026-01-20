# ARIA Agent Routing - Talk to CHIRON/SCHOLAR via ARIA

## Overview
Enable ARIA to route requests to CHIRON and SCHOLAR automatically, so you can have natural conversations without curl commands.

---

## ROUTING LOGIC

### Detect CHIRON Requests (Business Mentor)
**Explicit triggers:**
- "ask CHIRON", "have CHIRON", "tell CHIRON"
- "CHIRON, ..."

**Implicit triggers (auto-detect):**
- "sprint plan", "plan my week", "plan my day"
- "pricing", "how much should I charge", "price this"
- "I'm afraid", "I'm avoiding", "fear check", "what am I afraid of"
- "weekly review", "what did I accomplish"
- "am I procrastinating", "call me out", "accountability"
- "business strategy", "should I focus on"
- "ADHD", "staying focused", "overwhelmed"

**Route to:** `http://chiron:8017/chat` (or appropriate endpoint)

### Detect SCHOLAR Requests (Market Research)
**Explicit triggers:**
- "ask SCHOLAR", "have SCHOLAR", "tell SCHOLAR"
- "SCHOLAR, ..."
- "research this", "look up", "find out about"

**Implicit triggers (auto-detect):**
- "competitor", "competition", "who else does"
- "market size", "TAM", "SAM", "SOM", "how big is the market"
- "ICP", "ideal customer", "who should I target"
- "niche", "which industry", "what vertical"
- "pain points", "what problems do they have"
- "validate", "is it true that", "assumption"
- "pricing in the market", "what do others charge"

**Route to:** `http://scholar:8018/research` (or appropriate endpoint)

### Default: ARIA handles it
If no routing triggers detected, ARIA processes normally.

---

## IMPLEMENTATION

### Option 1: Pre-Router Node in ARIA Workflow

Add a Code node BEFORE the AI Agent that checks for routing:

```javascript
// Pre-Router: Check if request should go to CHIRON or SCHOLAR
const message = $json.message.toLowerCase();

// CHIRON triggers
const chironExplicit = /\b(ask chiron|have chiron|tell chiron|chiron,)/i;
const chironImplicit = /\b(sprint plan|plan my (week|day)|pricing|how much should i charge|price this|i'm afraid|i'm avoiding|fear check|weekly review|what did i accomplish|procrastinating|call me out|accountability|business strategy|should i focus|adhd|staying focused|overwhelmed)\b/i;

// SCHOLAR triggers  
const scholarExplicit = /\b(ask scholar|have scholar|tell scholar|scholar,|research this|look up|find out about)/i;
const scholarImplicit = /\b(competitor|competition|who else does|market size|tam|sam|som|how big is the market|icp|ideal customer|who should i target|niche|which industry|what vertical|pain points|what problems do they have|validate|is it true that|assumption)\b/i;

let route = 'aria'; // default
let endpoint = null;
let payload = null;

if (chironExplicit.test(message) || chironImplicit.test(message)) {
  route = 'chiron';
  
  // Determine which CHIRON endpoint
  if (/sprint|plan my (week|day)/i.test(message)) {
    endpoint = '/sprint-plan';
    payload = { goals: [message], time_available: 'this week' };
  } else if (/pricing|how much|charge/i.test(message)) {
    endpoint = '/pricing-help';
    payload = { service_description: message };
  } else if (/afraid|avoiding|fear/i.test(message)) {
    endpoint = '/fear-check';
    payload = { situation: message };
  } else if (/weekly review|accomplish/i.test(message)) {
    endpoint = '/weekly-review';
    payload = { wins: [], losses: [], lessons: [] }; // User fills in
  } else {
    endpoint = '/chat';
    payload = { message: message };
  }
} else if (scholarExplicit.test(message) || scholarImplicit.test(message)) {
  route = 'scholar';
  
  // Determine which SCHOLAR endpoint
  if (/competitor|competition/i.test(message)) {
    endpoint = '/competitors';
    payload = { niche: message };
  } else if (/market size|tam|sam|som/i.test(message)) {
    endpoint = '/market-size';
    payload = { market: message };
  } else if (/icp|ideal customer|target/i.test(message)) {
    endpoint = '/icp';
    payload = { niche: message };
  } else if (/niche|industry|vertical/i.test(message)) {
    endpoint = '/niche';
    payload = { niche: message };
  } else if (/pain point|problems/i.test(message)) {
    endpoint = '/pain-discovery';
    payload = { role: 'compliance officer', industry: 'water utilities' };
  } else if (/validate|assumption|is it true/i.test(message)) {
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
    original_message: $json.message
  }
};
```

### Option 2: Switch Node After Pre-Router

After the Code node, add a Switch node:
- If `route` = "chiron" → HTTP Request to CHIRON
- If `route` = "scholar" → HTTP Request to SCHOLAR  
- If `route` = "aria" → Continue to ARIA AI Agent

### Option 3: HTTP Request Nodes for Agents

**CHIRON HTTP Request:**
```
URL: http://chiron:8017{{ $json.agent_endpoint }}
Method: POST
Body: {{ JSON.stringify($json.agent_payload) }}
```

**SCHOLAR HTTP Request:**
```
URL: http://scholar:8018{{ $json.agent_endpoint }}
Method: POST
Body: {{ JSON.stringify($json.agent_payload) }}
```

### Option 4: Format Agent Response for ARIA Output

After getting CHIRON/SCHOLAR response, format it for ARIA's voice:

```javascript
// Post-Router: Format agent response
const route = $('Pre-Router').first().json.route;
const agentResponse = $json.response || $json.research || $json.sprint_plan || $json.pricing_strategy || $json.fear_analysis;

if (route === 'chiron') {
  return {
    json: {
      message: `**CHIRON says:**\n\n${agentResponse}`,
      agent_used: 'CHIRON',
      mode: 'STRATEGY'
    }
  };
} else if (route === 'scholar') {
  return {
    json: {
      message: `**SCHOLAR's research:**\n\n${agentResponse}`,
      agent_used: 'SCHOLAR', 
      mode: 'FOCUS'
    }
  };
}

return $json; // ARIA response passthrough
```

---

## WORKFLOW MODIFICATIONS

### In DEV ARIA Workflow:

1. **Add Pre-Router Code Node**
   - Position: After "Web Interface Handler", before "Model Router"
   - Contains: Routing logic above

2. **Add Switch Node**
   - Position: After Pre-Router
   - Conditions:
     - `{{ $json.route }}` equals "chiron" → CHIRON branch
     - `{{ $json.route }}` equals "scholar" → SCHOLAR branch
     - Default → ARIA branch (existing flow)

3. **Add CHIRON HTTP Request Node**
   - URL: `http://chiron:8017{{ $json.agent_endpoint }}`
   - Method: POST
   - Headers: Content-Type: application/json
   - Body: `{{ JSON.stringify($json.agent_payload) }}`

4. **Add SCHOLAR HTTP Request Node**
   - URL: `http://scholar:8018{{ $json.agent_endpoint }}`
   - Method: POST
   - Headers: Content-Type: application/json
   - Body: `{{ JSON.stringify($json.agent_payload) }}`

5. **Add Response Formatter Code Node**
   - Position: After CHIRON/SCHOLAR HTTP nodes
   - Contains: Response formatting logic above

6. **Merge Back to Output**
   - All three branches (CHIRON, SCHOLAR, ARIA) merge to response handler

---

## DOCKER NETWORK

Ensure ARIA workflow can reach CHIRON and SCHOLAR:

```yaml
# ARIA's n8n needs to be on same network as control plane agents
networks:
  - stack_net
  - control-plane-net  # Add this if not already present
```

Or use full URLs:
- `http://chiron:8017` (if on same network)
- `http://172.17.0.1:8017` (Docker bridge fallback)

---

## TESTING

After implementation:

**Test CHIRON routing:**
```
ARIA: "I'm feeling overwhelmed and avoiding outreach"
Expected: Routes to CHIRON /fear-check, returns analysis
```

**Test SCHOLAR routing:**
```
ARIA: "Research the top compliance automation competitors"
Expected: Routes to SCHOLAR /deep-research, returns research with sources
```

**Test ARIA default:**
```
ARIA: "What's on my calendar today?"
Expected: ARIA handles normally (no routing)
```

---

## SUCCESS CRITERIA

- [ ] "ask CHIRON..." routes to CHIRON
- [ ] "research..." routes to SCHOLAR
- [ ] Implicit triggers work (pricing, competitors, fear, etc.)
- [ ] Responses formatted with agent attribution
- [ ] Default messages still handled by ARIA
- [ ] Cost tracking logs which agent was used
- [ ] Works from aria.leveredgeai.com

---

## GIT COMMIT MESSAGE

```
Add CHIRON/SCHOLAR routing to ARIA workflow

- Pre-Router detects business/research intent
- Explicit triggers: "ask CHIRON", "research this"
- Implicit triggers: pricing, competitors, fear, market size, etc.
- Routes to appropriate agent endpoint
- Formats response with agent attribution
- Maintains ARIA personality wrapper
```
