# ATLAS AI Agent Workflow Setup

## Workflow File
Location: `/opt/leveredge/control-plane/workflows/atlas-ai-agent.json`

## Import Instructions

### Step 1: Access n8n
1. Go to https://control.n8n.leveredgeai.com (or http://localhost:5679)
2. Login with:
   - Username: `admin`
   - Password: `oMtnAe9qsrxhMe/1ROmokg==`

### Step 2: Create Anthropic Credential
Before importing the workflow, create the API credential:

1. Go to **Settings** (gear icon) → **Credentials**
2. Click **Add Credential**
3. Search for "Anthropic"
4. Select **Anthropic API**
5. Enter your Anthropic API key
6. Save as "Anthropic API"

**Alternative: OpenAI**
If using OpenAI instead:
1. Add credential for "OpenAI API"
2. After importing workflow, change the model node from Claude to OpenAI Chat Model

### Step 3: Import Workflow
1. Click **Add workflow** (+ button)
2. Select **Import from file**
3. Choose: `/opt/leveredge/control-plane/workflows/atlas-ai-agent.json`
4. Click **Import**

### Step 4: Update Credential Reference
After import, you need to link the credential:
1. Open the workflow
2. Click on **Claude 3.5 Sonnet** node
3. In **Credential to connect with**, select your "Anthropic API" credential
4. Save the workflow

### Step 5: Activate Workflow
1. Toggle the workflow to **Active** (top right)
2. The webhook will be available at: `https://control.n8n.leveredgeai.com/webhook/atlas`

## Testing

### Test via curl
```bash
# Health check
curl -X POST https://control.n8n.leveredgeai.com/webhook/atlas \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your status?"}'

# Check system status
curl -X POST https://control.n8n.leveredgeai.com/webhook/atlas \
  -H "Content-Type: application/json" \
  -d '{"message": "Check the health of the Event Bus"}'

# Local testing (bypass SSL)
curl -X POST http://localhost:5679/webhook/atlas \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello ATLAS, what can you do?"}'
```

## Workflow Structure

```
┌─────────────────┐
│ ATLAS Webhook   │ (POST /webhook/atlas)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  ATLAS Agent    │◄────│  Claude 3.5 Sonnet   │
│  (AI Agent)     │     │  (Language Model)    │
└────────┬────────┘     └──────────────────────┘
         │
         │              ┌──────────────────────┐
         │◄─────────────│  Log to Event Bus    │ (Tool)
         │              └──────────────────────┘
         │              ┌──────────────────────┐
         │◄─────────────│  Check Agent Health  │ (Tool)
         │              └──────────────────────┘
         │              ┌──────────────────────┐
         │◄─────────────│  Get Events          │ (Tool)
         │              └──────────────────────┘
         ▼
┌─────────────────┐
│ Respond to      │
│ Webhook         │
└─────────────────┘
```

## Tools Available to ATLAS

| Tool | Description | Endpoint |
|------|-------------|----------|
| log_to_event_bus | Log actions to Event Bus | POST :8099/events |
| check_agent_health | Check if an agent is responding | GET :PORT/health |
| get_event_bus_events | Retrieve recent events | GET :8099/events |

## Credentials Required

| Credential | Type | Required |
|------------|------|----------|
| Anthropic API | API Key | Yes (or OpenAI) |

## Notes

- The workflow uses `host.docker.internal` to access host services from within Docker
- Event Bus runs on port 8099
- Other agents (when deployed) will run on ports 8008-8015
- The AI Agent will automatically log all requests to the Event Bus
