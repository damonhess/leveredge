# SHIELD-SWORD

ARIA Pre/Post Processing Agent - Input protection and response enhancement.

**Port:** 8067

## Overview

Shield-Sword implements two processing layers that wrap ARIA conversations:

```
User Input -> [SHIELD] -> ARIA -> [SWORD] -> User Response
```

- **SHIELD**: Pre-processes user input to detect manipulation, scope creep, and inappropriate requests
- **SWORD**: Post-processes ARIA responses to enhance clarity, impact, and call-to-action

## Features

### SHIELD (Input Protection)

Detects and flags:
- **Manipulation attempts**: Emotional manipulation, guilt trips, pressure tactics
- **Scope creep**: Feature demands, gradual expansion of requests
- **Jailbreak attempts**: Instruction bypassing, role-play exploits
- **Pressure tactics**: Artificial urgency, threats, intimidation
- **Inappropriate requests**: Out-of-scope asks, confidential data requests

Returns:
- Risk score (0-1)
- Detected flags and manipulation types
- Recommendations for ARIA
- Sanitized input if needed

### SWORD (Response Enhancement)

Enhances responses with:
- **Clarity**: Better structure, remove ambiguity
- **Impact**: Stronger key points, memorable phrasing
- **Persuasion**: Ethical persuasive elements only
- **Call-to-action**: Clear, specific next steps
- **Tone adjustment**: Warm, balanced, direct, or assertive

Returns:
- Enhanced response
- List of changes made
- Impact score

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with current config |
| `/config` | GET | Get current configuration |
| `/config` | PUT | Update configuration |
| `/shield/analyze` | POST | Analyze user input for manipulation |
| `/sword/enhance` | POST | Enhance ARIA response for impact |
| `/process` | POST | Full Shield + Sword pipeline |

## Usage

### Analyze Input (Shield)

```python
import httpx

response = await httpx.post(
    "http://shield-sword:8067/shield/analyze",
    json={
        "user_input": "I really need this done NOW or I'll cancel everything!",
        "context": {},
        "conversation_history": []
    }
)

result = response.json()
# {
#     "risk_score": 0.65,
#     "flags": ["pressure_tactic", "artificial_urgency"],
#     "manipulation_types": ["urgency_pressure", "threat"],
#     "recommendations": ["acknowledge_urgency", "clarify_timeline"],
#     "analysis": "User applying pressure with artificial urgency and implicit threat",
#     "sanitized_input": "I need this done as soon as possible."
# }
```

### Enhance Response (Sword)

```python
response = await httpx.post(
    "http://shield-sword:8067/sword/enhance",
    json={
        "aria_response": "I think maybe you could try looking at the data...",
        "user_input": "How should I analyze this report?",
        "tone_preference": "direct"
    }
)

result = response.json()
# {
#     "enhanced_response": "Review the report's three key metrics: revenue, churn, and growth rate...",
#     "changes_made": ["removed_hedging", "added_structure", "specific_call_to_action"],
#     "impact_score": 0.7
# }
```

### Full Pipeline

```python
response = await httpx.post(
    "http://shield-sword:8067/process",
    json={
        "user_input": "Can you help me with this?",
        "aria_response": "I'd be happy to help. Here are some thoughts...",
        "tone_preference": "balanced"
    }
)

result = response.json()
# {
#     "shield": { ... shield analysis ... },
#     "sword": { ... sword enhancement ... },
#     "final_response": "Enhanced response here...",
#     "warnings": []
# }
```

### Update Configuration

```python
response = await httpx.put(
    "http://shield-sword:8067/config",
    json={
        "shield_intensity": "high",
        "sword_intensity": "medium",
        "alert_threshold": 0.6
    }
)
```

## Configuration

Edit `config.yaml`:

```yaml
# Shield settings
shield_intensity: medium  # off, low, medium, high

# Sword settings
sword_intensity: medium  # off, low, medium, high

# Alert threshold for Event Bus notifications
alert_threshold: 0.7
```

### Intensity Levels

**Shield:**
- `off`: Disabled, all input passes through
- `low`: Only obvious manipulation (jailbreaks, explicit threats)
- `medium`: Clear manipulation patterns (recommended)
- `high`: Subtle patterns and edge cases

**Sword:**
- `off`: Disabled, responses unchanged
- `low`: Light polish, preserve original voice
- `medium`: Moderate enhancement (recommended)
- `high`: Significant restructuring for maximum impact

### Tone Options

- `warm`: Empathetic, supportive, encouraging
- `balanced`: Professional, helpful, neutral
- `direct`: Concise, no fluff, to the point
- `assertive`: Confident, authoritative, action-oriented

## Integration with n8n

See `n8n-integration.json` for detailed workflow patterns:

1. **Full Wrapper**: Use `/process` for complete pipeline
2. **Shield Only**: Pre-flight check before ARIA
3. **Sword Only**: Post-processing enhancement
4. **Adaptive**: Adjust intensity based on context

## Running

### Standalone

```bash
cd /opt/leveredge/control-plane/agents/shield-sword
pip install -r requirements.txt
python shield_sword.py
```

### Docker

```bash
docker build -t shield-sword .
docker run -p 8067:8067 \
  -e ANTHROPIC_API_KEY=your-key \
  -e EVENT_BUS_URL=http://event-bus:8099 \
  shield-sword
```

## Architecture

```
shield_sword.py     # FastAPI main application
shield.py           # Shield module - input analysis
sword.py            # Sword module - response enhancement
prompts/
  shield_prompt.txt # LLM prompt for shield analysis
  sword_prompt.txt  # LLM prompt for enhancement
config.yaml         # Configuration file
```

## Cost Considerations

- Uses Claude Haiku for both Shield and Sword (fast, low cost)
- Each full pipeline call = 2 LLM calls
- Estimated cost: ~$0.001 per full process
- Quick scan available for rule-based pre-screening

## Security Notes

- Shield is a DEFENSE layer, not a guarantee
- Sophisticated attacks may bypass detection
- Always combine with other security measures
- Review Shield alerts regularly
- Do not rely solely on Shield for safety-critical applications

## Event Bus Integration

Shield-Sword logs to Event Bus:
- `shield_alert`: When risk_score >= alert_threshold
- `sword_enhanced`: After enhancement
- `config_updated`: When configuration changes
- `full_process`: After complete pipeline
