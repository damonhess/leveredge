# MAGNUS

**Port:** 8019
**Domain:** CHANCERY
**Status:** ✅ Operational

---

## Identity

**Name:** MAGNUS
**Title:** Universal Project Master
**Tagline:** "MAGNUS speaks 7 PM languages"

## Purpose

MAGNUS is the universal project management agent. It provides a unified interface to manage projects and tasks across multiple PM tools through adapters.

---

## Supported PM Tools

| Tool | Adapter | API Type |
|------|---------|----------|
| Leantime | LeantimeAdapter | JSON-RPC |
| OpenProject | OpenProjectAdapter | REST |
| Asana | AsanaAdapter | REST |
| Jira | JiraAdapter | REST |
| Monday.com | MondayAdapter | GraphQL |
| Notion | NotionAdapter | REST |
| Linear | LinearAdapter | GraphQL |

---

## API Endpoints

### Health
```
GET /health
```

### Projects

```
GET /projects
GET /projects/{tool}/{id}
POST /projects/{tool}
PUT /projects/{tool}/{id}
```

### Tasks

```
GET /projects/{tool}/{project_id}/tasks
GET /tasks/{tool}/{id}
POST /projects/{tool}/{project_id}/tasks
PUT /tasks/{tool}/{id}
DELETE /tasks/{tool}/{id}
POST /tasks/{tool}/{id}/complete
```

### Connection Test

```
GET /tools/{tool}/test
```

---

## Unified Data Model

### UnifiedProject
```python
{
    "external_id": "string",
    "name": "string",
    "description": "string",
    "status": "planning|active|completed|on_hold",
    "start_date": "date",
    "end_date": "date",
    "url": "string"
}
```

### UnifiedTask
```python
{
    "external_id": "string",
    "project_external_id": "string",
    "title": "string",
    "description": "string",
    "status": "todo|in_progress|blocked|review|done|cancelled",
    "priority": "low|medium|high|critical",
    "assignee": "string",
    "due_date": "date",
    "url": "string"
}
```

---

## Status Mappings

Each adapter maps tool-specific statuses to unified statuses:

| Unified | OpenProject | Jira | Asana |
|---------|-------------|------|-------|
| todo | New | To Do | To Do |
| in_progress | In progress | In Progress | Doing |
| blocked | On hold | Blocked | Blocked |
| review | In testing | In Review | Review |
| done | Closed | Done | Done |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `magnus_list_projects` | List all projects from a tool |
| `magnus_get_project` | Get project details |
| `magnus_create_task` | Create a new task |
| `magnus_update_task` | Update task details |
| `magnus_complete_task` | Mark task as done |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `pm_tool_connections` | Tool configurations |
| `pm_sync_log` | Synchronization history |

---

## Configuration

Each tool requires specific credentials:

```yaml
# OpenProject
openproject:
  instance_url: "http://openproject:80"
  credentials:
    api_key: "your-api-key"

# Jira
jira:
  domain: "yourcompany.atlassian.net"
  credentials:
    email: "user@example.com"
    api_token: "your-token"

# Asana
asana:
  workspace_gid: "workspace-id"
  credentials:
    access_token: "your-pat"
```

---

## Integration Points

### Calls To
- PM tool APIs (Leantime, OpenProject, etc.)
- Supabase for sync state
- VARYS for portfolio context

### Called By
- ARIA for task management
- n8n workflows
- Claude Code via MCP

---

## Deployment

```bash
docker run -d --name magnus \
  --network leveredge-network \
  -p 8019:8017 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  magnus:dev
```

---

## Adapters Directory

```
/opt/leveredge/control-plane/agents/magnus/adapters/
├── __init__.py      # Registry and exports
├── base.py          # PMAdapter base class
├── leantime.py      # Leantime adapter
├── openproject.py   # OpenProject adapter
├── asana.py         # Asana adapter
├── jira.py          # Jira adapter
├── monday.py        # Monday.com adapter
├── notion.py        # Notion adapter
└── linear.py        # Linear adapter
```

---

## Changelog

- 2026-01-19: Added OpenProject adapter with delete_task
- 2026-01-19: Added 5 new adapters (Asana, Jira, Monday, Notion, Linear)
- 2026-01-18: Initial deployment with Leantime
