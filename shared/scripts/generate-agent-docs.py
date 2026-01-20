#!/usr/bin/env python3
"""
Generate documentation for all agents from agent-registry.yaml
"""

import os
import yaml
from datetime import datetime

TEMPLATE = '''# {name}

**Port:** {port}
**Category:** {category}
**Status:** {status}

---

## Identity

**Name:** {name}
**Description:** {description}

---

## Health Check

```
GET /health
```

Response:
```json
{{
  "status": "healthy",
  "service": "{name_lower}",
  "port": {port}
}}
```

---

## Actions

{actions}

---

## Capabilities

{capabilities}

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `{name_lower}.action.completed`
- `{name_lower}.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name {name_lower} \\
  --network leveredge-fleet-net \\
  -p {port}:{port} \\
  -e DATABASE_URL="$DEV_DATABASE_URL" \\
  {name_lower}:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d {name_lower}
```

---

*Generated: {timestamp}*
'''


def format_actions(actions):
    """Format actions into markdown"""
    if not actions:
        return "*No actions defined*"

    lines = []
    for action_name, action in actions.items():
        endpoint = action.get('endpoint', '/')
        method = action.get('method', 'GET')
        description = action.get('description', '')
        lines.append(f"### {action_name}")
        lines.append(f"```")
        lines.append(f"{method} {endpoint}")
        lines.append(f"```")
        lines.append(f"{description}")
        lines.append("")

    return "\n".join(lines)


def format_capabilities(capabilities):
    """Format capabilities into markdown"""
    if not capabilities:
        return "*No capabilities defined*"

    return "\n".join([f"- {cap}" for cap in capabilities])


def generate_docs():
    """Generate documentation for all agents"""
    # Read registry
    with open('/opt/leveredge/config/agent-registry.yaml', 'r') as f:
        data = yaml.safe_load(f)

    agents = data.get('agents', {})
    output_dir = '/opt/leveredge/agent-docs'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    for name, config in sorted(agents.items()):
        conn = config.get('connection', {})
        url = conn.get('url', '')
        port = url.split(':')[-1].replace('/', '') if url else 'N/A'

        doc = TEMPLATE.format(
            name=config.get('name', name.upper()),
            name_lower=name.lower().replace('_', '-'),
            port=port,
            category=config.get('category', 'unknown'),
            status='Defined' if not config.get('llm_powered', True) else 'LLM-Powered',
            description=config.get('description', 'No description'),
            actions=format_actions(config.get('actions', {})),
            capabilities=format_capabilities(config.get('capabilities', [])),
            timestamp=timestamp,
        )

        filepath = f"{output_dir}/{name.upper()}.md"
        with open(filepath, 'w') as f:
            f.write(doc)

        print(f"Generated: {filepath}")


if __name__ == "__main__":
    generate_docs()
    print(f"\nDocs generated in /opt/leveredge/agent-docs/")
