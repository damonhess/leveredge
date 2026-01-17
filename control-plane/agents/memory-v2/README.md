# ARIA Memory V2 - Long-Term Memory Enhancement

**Port:** 8066

ARIA Memory V2 enhances ARIA's capabilities with structured long-term memory, going beyond chat history to provide intelligent fact extraction, preference learning, and decision tracking.

## Features

### 1. Long-term Fact Extraction
Automatically extracts memorable facts from conversations:
- Personal information (name, location, family)
- Professional context (job, company, skills)
- Health information (handled with sensitivity)
- Technical preferences (tools, languages)
- Project context (deadlines, goals)

### 2. Preference Learning
Learns user preferences over time with confidence tracking:
- Explicit preferences ("I prefer bullet points")
- Implicit preferences (inferred from behavior)
- Confirmation/contradiction tracking
- Confidence adjustment based on evidence

### 3. Decision History
Tracks decisions for future reference:
- What was decided
- Context and reasoning
- Options considered
- Outcomes (when recorded)

### 4. "Remember when..." Queries
Natural language memory recall:
- Full-text search across all memory
- AI-powered summarization
- Cross-references facts, preferences, and decisions

## API Endpoints

### Health
```
GET /health
```
Returns agent health status and component availability.

### Fact Extraction
```
POST /extract
```
Extract facts and preferences from a conversation.

**Request:**
```json
{
  "conversation": "User: Hi, I'm Alex. I work at Stripe...",
  "user_id": "default",
  "conversation_id": "conv-123",
  "include_preferences": true
}
```

**Response:**
```json
{
  "user_id": "default",
  "facts": [
    {
      "fact": "User's name is Alex",
      "category": "personal",
      "confidence": 1.0
    }
  ],
  "preferences": [
    {
      "preference_key": "response_format_preference",
      "preference_value": "bullet_points",
      "confidence": 0.9
    }
  ]
}
```

### Preference Learning
```
POST /learn-preference
```
Explicitly record a learned preference.

```
GET /preferences/{user_id}
```
Get all preferences for a user.

### Decision Tracking
```
POST /log-decision
```
Log a decision made.

```
GET /decisions/{user_id}
```
Get decision history.

```
PUT /decisions/{decision_id}/outcome
```
Record the outcome of a decision.

### Memory Recall
```
GET /recall?user_id=default&query=when%20I%20talked%20about%20my%20project
```
"Remember when..." natural language queries.

### Facts
```
GET /facts/{user_id}
```
Get all known facts about a user.

### Statistics
```
GET /stats/{user_id}
```
Get memory statistics for a user.

## Database Schema

Run `schema.sql` in Supabase SQL Editor to create required tables:

### aria_facts
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | TEXT | User identifier |
| fact | TEXT | The extracted fact |
| category | TEXT | Fact category |
| confidence | FLOAT | 0-1 confidence score |
| source_conversation_id | TEXT | Source conversation |
| created_at | TIMESTAMPTZ | When extracted |

### aria_preferences
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | TEXT | User identifier |
| preference_key | TEXT | Unique preference key |
| preference_value | TEXT | Preference value |
| category | TEXT | Preference category |
| confidence | FLOAT | 0-1 confidence score |
| confirmation_count | INT | Times confirmed |
| contradiction_count | INT | Times contradicted |
| learned_at | TIMESTAMPTZ | When first learned |
| last_confirmed | TIMESTAMPTZ | Last confirmation |

### aria_decisions
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | TEXT | User identifier |
| decision | TEXT | The decision made |
| decision_type | TEXT | Type of decision |
| context | JSONB | Decision context |
| options_considered | TEXT[] | Options evaluated |
| reasoning | TEXT | Why this decision |
| outcome | TEXT | What happened |
| outcome_rating | INT | 1-5 rating |
| created_at | TIMESTAMPTZ | When made |

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...     # Required for LLM extraction
SUPABASE_URL=http://...          # Supabase REST API URL
SUPABASE_SERVICE_KEY=...         # Supabase service key
EVENT_BUS_URL=http://...         # Event bus for notifications
```

## Integration with ARIA

Call Memory V2 after conversations to extract and store memories:

```python
import httpx

async def process_conversation(conversation: str, user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://memory-v2:8066/extract",
            json={
                "conversation": conversation,
                "user_id": user_id,
                "include_preferences": True
            }
        )
        return response.json()
```

Use recall before generating responses to include relevant context:

```python
async def get_memory_context(user_id: str, topic: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://memory-v2:8066/recall",
            params={
                "user_id": user_id,
                "query": topic
            }
        )
        return response.json()
```

## Fact Categories

- `personal` - Name, age, location, family
- `professional` - Job, company, skills
- `preference` - Likes, dislikes
- `context` - Current situation, goals
- `health` - Health conditions (handled sensitively)
- `technical` - Tech stack, tools
- `relationship` - People mentioned
- `schedule` - Work hours, timezone
- `financial` - Budget, financial goals
- `project` - Active projects, deadlines
- `general` - Other facts

## Preference Categories

- `communication` - How they like to communicate
- `scheduling` - Time preferences
- `tools` - Software preferences
- `workflow` - Work style preferences
- `content` - Content format preferences
- `interaction` - AI interaction style
- `technical` - Technical preferences
- `lifestyle` - Hobbies, activities
- `information` - How they like info presented
- `general` - Other preferences

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export SUPABASE_URL=http://localhost:8000
export SUPABASE_SERVICE_KEY=...

# Run the server
python memory_v2.py
```

## Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8066
CMD ["python", "memory_v2.py"]
```

## Architecture

```
ARIA (Main Chat)
    |
    v
Memory V2 (/extract) -----> Claude (Fact Extraction)
    |                            |
    v                            v
Supabase <--- aria_facts, aria_preferences, aria_decisions
    |
    v
Memory V2 (/recall) -----> Claude (Memory Summarization)
    |
    v
ARIA (Enhanced Context)
```

## Cost Tracking

All LLM calls are logged via the shared cost_tracker module to `agent_usage_logs` table.

## Team Integration

- **ARIA**: Primary consumer - extracts memories, queries for context
- **HERMES**: Notified of significant memory events
- **Event Bus**: All operations publish events for observability
- **Other Agents**: Can query user preferences and facts

## Version History

- **v2.0.0** (2026-01) - Initial release with fact extraction, preference learning, decision tracking, and recall
