#!/usr/bin/env python3
"""
Create n8n workflows for Phase 4 agents: HERMES, ARGUS, ALOY, ATHENA
Following the CHRONOS pattern: Webhook → AI Agent → Respond to Webhook
"""

import json
import subprocess
import uuid
from datetime import datetime

# Database connection
DB_USER = "n8n_control"
DB_NAME = "n8n_control"
DB_PASSWORD = "jsGibvef8RML3/jKSviA+oWZL+pytauV"
CONTAINER = "control-n8n-postgres"

def generate_workflow_id():
    """Generate a 16-char alphanumeric ID like n8n uses"""
    import random
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(16))

def generate_node_id():
    """Generate UUID for node IDs"""
    return str(uuid.uuid4())

# Anthropic credential ID from CHRONOS workflow
ANTHROPIC_CRED_ID = "NQ4e9Jw74TK8ABhU"
ANTHROPIC_CRED_NAME = "Anthropic account"

def create_workflow(agent_name, port, webhook_path, system_prompt, tools):
    """Create a workflow with webhook, AI agent, and tool nodes"""

    workflow_id = generate_workflow_id()
    webhook_id = f"{agent_name.lower()}-webhook"

    # Base nodes
    nodes = [
        {
            "name": f"{agent_name} Webhook",
            "type": "n8n-nodes-base.webhook",
            "position": [208, 304],
            "webhookId": webhook_id,
            "parameters": {
                "path": webhook_path,
                "options": {},
                "httpMethod": "POST",
                "responseMode": "responseNode"
            },
            "typeVersion": 2,
            "id": generate_node_id()
        },
        {
            "name": f"{agent_name} Agent",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "position": [464, 304],
            "parameters": {
                "text": "={{ $json.body.message || $json.body.chatInput || $json.body.query || JSON.stringify($json.body) }}",
                "options": {
                    "systemMessage": system_prompt
                },
                "promptType": "define"
            },
            "typeVersion": 1.7,
            "id": generate_node_id()
        },
        {
            "name": "Claude Sonnet",
            "type": "@n8n/n8n-nodes-langchain.lmChatAnthropic",
            "position": [336, 512],
            "parameters": {
                "model": "claude-sonnet-4-20250514",
                "options": {
                    "maxTokensToSample": 4096
                }
            },
            "typeVersion": 1.2,
            "id": generate_node_id(),
            "credentials": {
                "anthropicApi": {
                    "id": ANTHROPIC_CRED_ID,
                    "name": ANTHROPIC_CRED_NAME
                }
            }
        },
        {
            "name": "Log to Event Bus",
            "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
            "position": [480, 512],
            "parameters": {
                "url": "http://event-bus:8099/events",
                "method": "POST",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": f"={{\"source_agent\": \"{agent_name}\", \"action\": \"{{{{ $fromAI('action', 'Action performed') }}}}\", \"details\": {{\"message\": \"{{{{ $fromAI('details', 'Details') }}}}\"}}}}",
                "description": "Log an event to the Event Bus"
            },
            "typeVersion": 1.1,
            "id": generate_node_id()
        },
        {
            "name": "Respond to Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "position": [704, 304],
            "parameters": {
                "options": {},
                "respondWith": "text",
                "responseBody": "={{ $json.output }}"
            },
            "typeVersion": 1.1,
            "id": generate_node_id()
        }
    ]

    # Add tool nodes
    x_pos = 624
    for tool in tools:
        tool_node = {
            "name": tool["name"],
            "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
            "position": [x_pos, 512],
            "parameters": tool["parameters"],
            "typeVersion": 1.1,
            "id": generate_node_id()
        }
        nodes.append(tool_node)
        x_pos += 144

    # Connections
    connections = {
        f"{agent_name} Webhook": {
            "main": [[{"node": f"{agent_name} Agent", "type": "main", "index": 0}]]
        },
        f"{agent_name} Agent": {
            "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
        },
        "Claude Sonnet": {
            "ai_languageModel": [[{"node": f"{agent_name} Agent", "type": "ai_languageModel", "index": 0}]]
        },
        "Log to Event Bus": {
            "ai_tool": [[{"node": f"{agent_name} Agent", "type": "ai_tool", "index": 0}]]
        }
    }

    # Add tool connections
    for tool in tools:
        connections[tool["name"]] = {
            "ai_tool": [[{"node": f"{agent_name} Agent", "type": "ai_tool", "index": 0}]]
        }

    settings = {
        "executionOrder": "v1",
        "callerPolicy": "workflowsFromSameOwner",
        "availableInMCP": False
    }

    return {
        "id": workflow_id,
        "name": f"{agent_name} - Workflow",
        "nodes": nodes,
        "connections": connections,
        "settings": settings,
        "active": True
    }

def insert_workflow(workflow):
    """Insert workflow into database"""

    nodes_json = json.dumps(workflow["nodes"]).replace("'", "''")
    connections_json = json.dumps(workflow["connections"]).replace("'", "''")
    settings_json = json.dumps(workflow["settings"]).replace("'", "''")

    # Get timestamp
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f+00")

    # SQL for workflow_entity
    sql_entity = f"""
    INSERT INTO workflow_entity (id, name, active, nodes, connections, settings, "createdAt", "updatedAt", "staticData", "triggerCount", "versionId")
    VALUES (
        '{workflow["id"]}',
        '{workflow["name"]}',
        true,
        '{nodes_json}',
        '{connections_json}',
        '{settings_json}',
        '{now}',
        '{now}',
        NULL,
        0,
        '{uuid.uuid4()}'
    );
    """

    # SQL for workflow_history (required for n8n to see changes)
    version_id = str(uuid.uuid4())
    sql_history = f"""
    INSERT INTO workflow_history ("workflowId", "versionId", nodes, connections, "createdAt", "updatedAt", authors)
    VALUES (
        '{workflow["id"]}',
        '{version_id}',
        '{nodes_json}',
        '{connections_json}',
        '{now}',
        '{now}',
        'GSD'
    );
    """

    cmd = f'docker exec {CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c "{sql_entity}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error inserting {workflow['name']}: {result.stderr}")
        return False

    # Insert history
    cmd = f'docker exec {CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c "{sql_history}"'
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    print(f"Created: {workflow['name']} (ID: {workflow['id']})")
    return True


# Define agents
agents = [
    {
        "name": "HERMES",
        "port": 8014,
        "webhook_path": "hermes",
        "system_prompt": """You are HERMES, the Notification & Approval agent for the LeverEdge control plane.

Your responsibilities:
- Send notifications to various channels
- Request human approval for tier 2/3 operations
- Track pending approvals
- Report on notification history

You have tools to:
- Check HERMES backend health
- Send notifications
- Request approvals
- List pending approvals
- Get notification history
- Log events to Event Bus

Always be concise. Report what you did and the result.""",
        "tools": [
            {
                "name": "HERMES Health",
                "parameters": {
                    "url": "http://hermes:8014/health",
                    "description": "Check HERMES backend health"
                }
            },
            {
                "name": "Send Notification",
                "parameters": {
                    "url": "http://hermes:8014/notify",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"channel\": \"{{ $fromAI('channel', 'event-bus') }}\", \"message\": \"{{ $fromAI('message', 'Notification message') }}\", \"priority\": \"{{ $fromAI('priority', 'normal') }}\"}",
                    "description": "Send a notification. Channels: event-bus, telegram, slack. Priority: low, normal, high, critical."
                }
            },
            {
                "name": "Request Approval",
                "parameters": {
                    "url": "http://hermes:8014/request-approval",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"action\": \"{{ $fromAI('action', 'Action to approve') }}\", \"source_agent\": \"{{ $fromAI('source_agent', 'AGENT') }}\", \"tier\": {{ $fromAI('tier', '2') }}, \"details\": {\"info\": \"{{ $fromAI('details', 'Additional details') }}\"}}",
                    "description": "Request human approval for an action. Returns approval_id."
                }
            },
            {
                "name": "List Pending Approvals",
                "parameters": {
                    "url": "http://hermes:8014/pending",
                    "description": "List all pending approval requests"
                }
            },
            {
                "name": "Get History",
                "parameters": {
                    "url": "http://hermes:8014/history",
                    "description": "Get notification history"
                }
            }
        ]
    },
    {
        "name": "ARGUS",
        "port": 8016,
        "webhook_path": "argus",
        "system_prompt": """You are ARGUS, the Observability agent for the LeverEdge control plane.

Your responsibilities:
- Monitor system and agent health
- Query Prometheus metrics
- Report on service status
- Alert on issues

You have tools to:
- Check ARGUS backend health
- Get overall system status
- Get specific agent status
- Query Prometheus metrics
- Create alerts
- Log events to Event Bus

Always be concise. Report status clearly and highlight any issues.""",
        "tools": [
            {
                "name": "ARGUS Health",
                "parameters": {
                    "url": "http://argus:8016/health",
                    "description": "Check ARGUS backend health"
                }
            },
            {
                "name": "System Status",
                "parameters": {
                    "url": "http://argus:8016/status",
                    "description": "Get overall system status including all agents"
                }
            },
            {
                "name": "Agent Status",
                "parameters": {
                    "url": "=http://argus:8016/status/{{ $fromAI('agent_name', 'agent') }}",
                    "description": "Get status of a specific agent by name"
                }
            },
            {
                "name": "Get Metrics",
                "parameters": {
                    "url": "http://argus:8016/metrics",
                    "description": "Get current system metrics"
                }
            },
            {
                "name": "Query Prometheus",
                "parameters": {
                    "url": "http://argus:8016/prometheus/query",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"query\": \"{{ $fromAI('query', 'up') }}\"}",
                    "description": "Execute a Prometheus query. Use PromQL syntax."
                }
            },
            {
                "name": "Create Alert",
                "parameters": {
                    "url": "http://argus:8016/alert",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"severity\": \"{{ $fromAI('severity', 'warning') }}\", \"source\": \"{{ $fromAI('source', 'ARGUS') }}\", \"message\": \"{{ $fromAI('message', 'Alert message') }}\"}",
                    "description": "Create an alert. Severity: info, warning, error, critical."
                }
            }
        ]
    },
    {
        "name": "ALOY",
        "port": 8015,
        "webhook_path": "aloy",
        "system_prompt": """You are ALOY, the Audit & Anomaly Detection agent for the LeverEdge control plane.

Your responsibilities:
- Query and report on audit logs
- Detect anomalies in system behavior
- Analyze patterns in events
- Generate security reports

You have tools to:
- Check ALOY backend health
- Get recent audit events
- Generate audit reports
- List detected anomalies
- Analyze event patterns
- Log events to Event Bus

Always be concise. Report findings clearly and flag any security concerns.""",
        "tools": [
            {
                "name": "ALOY Health",
                "parameters": {
                    "url": "http://aloy:8015/health",
                    "description": "Check ALOY backend health"
                }
            },
            {
                "name": "Recent Audit Events",
                "parameters": {
                    "url": "http://aloy:8015/audit/recent",
                    "description": "Get recent audit events from Event Bus"
                }
            },
            {
                "name": "Audit Report",
                "parameters": {
                    "url": "http://aloy:8015/audit/report",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"hours\": {{ $fromAI('hours', '24') }}}",
                    "description": "Generate an audit report for the specified number of hours"
                }
            },
            {
                "name": "List Anomalies",
                "parameters": {
                    "url": "http://aloy:8015/anomalies",
                    "description": "List detected anomalies"
                }
            },
            {
                "name": "Analyze Patterns",
                "parameters": {
                    "url": "http://aloy:8015/analyze",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"focus\": \"{{ $fromAI('focus', 'all') }}\"}",
                    "description": "Analyze event patterns. Focus: all, security, performance, errors."
                }
            },
            {
                "name": "Get Rules",
                "parameters": {
                    "url": "http://aloy:8015/rules",
                    "description": "Get current anomaly detection rules"
                }
            }
        ]
    },
    {
        "name": "ATHENA",
        "port": 8013,
        "webhook_path": "athena",
        "system_prompt": """You are ATHENA, the Documentation agent for the LeverEdge control plane.

Your responsibilities:
- Generate system documentation
- Create architecture diagrams
- Maintain documentation freshness
- Update specific docs on request

You have tools to:
- Check ATHENA backend health
- Generate reports
- Generate architecture documentation
- List existing docs
- Get specific document content
- Update documents
- Log events to Event Bus

Always be concise. Focus on accuracy and clarity in documentation.""",
        "tools": [
            {
                "name": "ATHENA Health",
                "parameters": {
                    "url": "http://athena:8013/health",
                    "description": "Check ATHENA backend health"
                }
            },
            {
                "name": "Generate Report",
                "parameters": {
                    "url": "http://athena:8013/generate/report",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"report_type\": \"{{ $fromAI('report_type', 'status') }}\", \"scope\": \"{{ $fromAI('scope', 'all') }}\"}",
                    "description": "Generate a report. Types: status, health, deployment. Scope: all, agents, workflows."
                }
            },
            {
                "name": "Generate Architecture",
                "parameters": {
                    "url": "http://athena:8013/generate/architecture",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"format\": \"{{ $fromAI('format', 'markdown') }}\"}",
                    "description": "Generate architecture documentation. Format: markdown, mermaid, json."
                }
            },
            {
                "name": "List Docs",
                "parameters": {
                    "url": "http://athena:8013/docs",
                    "description": "List all available documentation"
                }
            },
            {
                "name": "Get Document",
                "parameters": {
                    "url": "=http://athena:8013/docs/{{ $fromAI('doc_name', 'README') }}",
                    "description": "Get content of a specific document by name"
                }
            },
            {
                "name": "Update Document",
                "parameters": {
                    "url": "=http://athena:8013/update/{{ $fromAI('doc_name', 'README') }}",
                    "method": "POST",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"content\": \"{{ $fromAI('content', 'New content') }}\"}",
                    "description": "Update a specific document"
                }
            }
        ]
    }
]

if __name__ == "__main__":
    print("Creating Phase 4 agent workflows...")
    print("=" * 50)

    for agent in agents:
        workflow = create_workflow(
            agent["name"],
            agent["port"],
            agent["webhook_path"],
            agent["system_prompt"],
            agent["tools"]
        )
        insert_workflow(workflow)

    print("=" * 50)
    print("Done! Verify with:")
    print("  docker exec control-n8n-postgres psql -U n8n_control -d n8n_control -c \"SELECT id, name, active FROM workflow_entity;\"")
