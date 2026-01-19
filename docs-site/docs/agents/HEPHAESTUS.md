# HEPHAESTUS

**Port:** 8011 (MCP) / 8207 (HTTP)
**Domain:** GAIA
**Status:** ✅ Operational

---

## Identity

**Name:** HEPHAESTUS
**Title:** The Divine Craftsman
**Tagline:** "Builder of tools for gods and mortals"

## Purpose

HEPHAESTUS is the MCP (Model Context Protocol) server that exposes LeverEdge capabilities to Claude Code. It provides file operations, command execution, agent tools, and pipeline management.

---

## API Endpoints

### Health
```
GET /health
```

### File Operations
```
GET /files/read?path=/path/to/file
POST /files/write
POST /files/search
GET /files/list?path=/directory
```

### Command Execution
```
POST /execute
{
  "command": "ls -la",
  "timeout": 30
}
```

---

## MCP Tools

### File Operations
| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write to a file |
| `edit_file` | Edit existing file |
| `search_files` | Search for files by pattern |
| `list_directory` | List directory contents |

### Commands
| Tool | Description |
|------|-------------|
| `execute_command` | Run shell command |
| `git_status` | Get git repository status |
| `git_commit` | Create git commit |

### Agent Tools
| Tool | Description |
|------|-------------|
| `agent_health_check` | Check agent health |
| `agent_restart` | Restart an agent |
| `agent_logs` | Get agent logs |

### Pipeline Tools
| Tool | Description |
|------|-------------|
| `pipeline_list` | List available pipelines |
| `pipeline_execute` | Execute a pipeline |
| `pipeline_status` | Check pipeline execution status |

### n8n Tools
| Tool | Description |
|------|-------------|
| `n8n_health` | Check n8n health |
| `n8n_db_health` | Check n8n database |
| `n8n_workflow_inventory` | List all workflows |
| `n8n_workflow_details` | Get workflow details |
| `n8n_validate_workflow` | Validate workflow config |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `pipeline_definitions` | Pipeline configurations |
| `pipeline_executions` | Execution history |
| `pipeline_stage_logs` | Stage-level logs |

---

## Configuration

Environment variables:
- `DATABASE_URL` - Database connection
- `MCP_PORT` - MCP server port (8011)
- `HTTP_PORT` - HTTP server port (8207)

---

## Integration Points

### Calls To
- File system for file operations
- Docker for container management
- n8n APIs for workflow operations
- Supabase for pipeline state

### Called By
- Claude Code (primary client)
- n8n workflows
- Other agents

---

## Security

HEPHAESTUS enforces:
- Path restrictions (no access outside allowed directories)
- Command sandboxing (restricted dangerous commands)
- Environment lock compliance (DEV-first)

---

## Deployment

```bash
# MCP Server
docker run -d --name hephaestus-mcp \
  --network leveredge-network \
  -p 8011:8011 \
  -v /opt/leveredge:/opt/leveredge \
  hephaestus:dev

# HTTP Server
docker run -d --name hephaestus \
  --network leveredge-network \
  -p 8207:8207 \
  hephaestus-http:dev
```

---

## MCP Configuration

Add to Claude Desktop `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hephaestus": {
      "command": "docker",
      "args": ["exec", "-i", "hephaestus-mcp", "python", "-m", "hephaestus_mcp"]
    }
  }
}
```

---

## Changelog

- 2026-01-19: Added pipeline execution tools
- 2026-01-18: Added n8n MCP tools
- 2026-01-15: Initial deployment
