# CONSUL: Universal Project Master

**Version:** 2.0
**Port:** 8017
**Domain:** CHANCERY
**Tier:** 1 (Supervisor)
**Status:** SPECIFICATION

---

## IDENTITY

**Name:** CONSUL
**Title:** Universal Project Master
**Tagline:** "Nothing escapes my attention. Nothing falls through the cracks."

CONSUL speaks every PM language. Whether you use Notion, Asana, Monday, Jira, Linear, ClickUp, or anything else - CONSUL adapts. For LeverEdge internal work, he uses Leantime (ADHD-friendly) and OpenProject (enterprise). For client work, he speaks their language.

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONSUL - Universal Project Master                    │
│                                  Port 8017                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      UNIFIED PROJECT MODEL                           │   │
│  │                                                                      │   │
│  │   Projects ─── Tasks ─── Subtasks ─── Comments                      │   │
│  │      │           │          │            │                          │   │
│  │   Milestones  Assignees  Dependencies  Attachments                  │   │
│  │      │           │          │            │                          │   │
│  │   Timelines   Priorities  Blockers    Time Tracking                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                          ┌─────────┴─────────┐                             │
│                          │  ADAPTER LAYER    │                             │
│                          └─────────┬─────────┘                             │
│                                    │                                        │
│  ┌──────────┬──────────┬──────────┼──────────┬──────────┬──────────┐      │
│  │          │          │          │          │          │          │      │
│  ▼          ▼          ▼          ▼          ▼          ▼          ▼      │
│ ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐   │
│ │Lean│   │Open│   │Not-│   │Asa-│   │Mon-│   │Jira│   │Lin-│   │Cli-│   │
│ │time│   │Proj│   │ion │   │na  │   │day │   │    │   │ear │   │ckUp│   │
│ └────┘   └────┘   └────┘   └────┘   └────┘   └────┘   └────┘   └────┘   │
│                                                                             │
│  INTERNAL          │              CLIENT PM TOOLS                          │
│  (Self-hosted)     │              (Cloud APIs)                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PM TOOL MATRIX

### Internal Tools (Self-Hosted)

| Tool | Port | Purpose | Why |
|------|------|---------|-----|
| **Leantime** | 8040 | Daily driver | ADHD-friendly, simple, fast |
| **OpenProject** | 8041 | Enterprise projects | Gantt, resources, complex deps |

### Client Tool Adapters (Cloud APIs)

| Tool | API | Adapter Status | Use Case |
|------|-----|----------------|----------|
| **Notion** | REST API | PLANNED | Startups, creative teams |
| **Asana** | REST API | PLANNED | Mid-market, agencies |
| **Monday.com** | GraphQL | PLANNED | Sales teams, marketing |
| **Jira** | REST API | PLANNED | Enterprise, dev teams |
| **Linear** | GraphQL | PLANNED | Modern dev teams |
| **ClickUp** | REST API | PLANNED | All-in-one teams |
| **Trello** | REST API | PLANNED | Simple boards |
| **Basecamp** | REST API | PLANNED | Agencies, remote teams |
| **Wrike** | REST API | PLANNED | Marketing, creative |
| **Teamwork** | REST API | PLANNED | Agencies |
| **Smartsheet** | REST API | PLANNED | Enterprise, PMOs |
| **Airtable** | REST API | PLANNED | Flexible databases |

---

## UNIFIED DATA MODEL

CONSUL normalizes ALL PM tools to a common model:

```python
class UnifiedProject:
    id: str                      # CONSUL's internal ID
    external_id: str             # ID in source system
    source: str                  # "leantime", "asana", "jira", etc.
    
    name: str
    description: str
    status: ProjectStatus        # planning, active, on_hold, completed
    
    owner: str
    team: List[str]
    
    start_date: date
    end_date: date
    
    # Mapped from source
    custom_fields: Dict[str, Any]
    
class UnifiedTask:
    id: str
    external_id: str
    source: str
    project_id: str
    
    title: str
    description: str
    status: TaskStatus           # todo, in_progress, blocked, review, done
    priority: Priority           # critical, high, medium, low
    
    assignee: str
    assignee_external_id: str    # ID in source system
    
    due_date: date
    estimated_hours: float
    actual_hours: float
    
    parent_task_id: str          # For subtasks
    depends_on: List[str]        # Task IDs this depends on
    
    tags: List[str]
    custom_fields: Dict[str, Any]

class UnifiedComment:
    id: str
    task_id: str
    author: str
    content: str
    created_at: datetime
    
class UnifiedTimeEntry:
    id: str
    task_id: str
    user: str
    hours: float
    description: str
    date: date
```

---

## ADAPTER INTERFACE

Every PM tool adapter implements:

```python
class PMAdapter(ABC):
    """Base class for all PM tool adapters"""
    
    name: str                    # "asana", "jira", etc.
    requires_oauth: bool
    api_base_url: str
    
    # ============ CONNECTION ============
    
    @abstractmethod
    async def connect(self, credentials: dict) -> bool:
        """Establish connection with credentials"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify connection is working"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Clean up connection"""
        pass
    
    # ============ PROJECTS ============
    
    @abstractmethod
    async def list_projects(self) -> List[UnifiedProject]:
        """Get all accessible projects"""
        pass
    
    @abstractmethod
    async def get_project(self, project_id: str) -> UnifiedProject:
        """Get single project by ID"""
        pass
    
    @abstractmethod
    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create new project"""
        pass
    
    @abstractmethod
    async def update_project(self, project_id: str, updates: dict) -> UnifiedProject:
        """Update existing project"""
        pass
    
    # ============ TASKS ============
    
    @abstractmethod
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        """Get tasks in a project"""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> UnifiedTask:
        """Get single task"""
        pass
    
    @abstractmethod
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create new task"""
        pass
    
    @abstractmethod
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        """Update existing task"""
        pass
    
    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        pass
    
    @abstractmethod
    async def move_task(self, task_id: str, new_status: str) -> UnifiedTask:
        """Change task status"""
        pass
    
    @abstractmethod
    async def assign_task(self, task_id: str, assignee: str) -> UnifiedTask:
        """Assign task to user"""
        pass
    
    # ============ COMMENTS ============
    
    @abstractmethod
    async def list_comments(self, task_id: str) -> List[UnifiedComment]:
        """Get comments on a task"""
        pass
    
    @abstractmethod
    async def add_comment(self, task_id: str, content: str) -> UnifiedComment:
        """Add comment to task"""
        pass
    
    # ============ TIME TRACKING ============
    
    @abstractmethod
    async def log_time(self, task_id: str, hours: float, description: str) -> UnifiedTimeEntry:
        """Log time against a task"""
        pass
    
    @abstractmethod
    async def get_time_entries(self, task_id: str) -> List[UnifiedTimeEntry]:
        """Get time entries for a task"""
        pass
    
    # ============ SYNC ============
    
    @abstractmethod
    async def sync_from_source(self, project_id: str) -> SyncResult:
        """Pull changes from source system"""
        pass
    
    @abstractmethod
    async def sync_to_source(self, project_id: str) -> SyncResult:
        """Push changes to source system"""
        pass
    
    # ============ WEBHOOKS ============
    
    @abstractmethod
    async def register_webhook(self, project_id: str, events: List[str]) -> str:
        """Register for real-time updates"""
        pass
    
    @abstractmethod
    async def handle_webhook(self, payload: dict) -> WebhookResult:
        """Process incoming webhook"""
        pass
```

---

## ADAPTER IMPLEMENTATIONS

### Leantime Adapter (Internal)

```python
class LeantimeAdapter(PMAdapter):
    name = "leantime"
    requires_oauth = False
    api_base_url = "http://leantime:80/api"
    
    async def connect(self, credentials: dict) -> bool:
        self.api_key = credentials.get("api_key")
        self.session = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return await self.test_connection()
    
    async def list_projects(self) -> List[UnifiedProject]:
        response = await self.session.get("/projects")
        projects = []
        for p in response.json():
            projects.append(UnifiedProject(
                id=f"leantime:{p['id']}",
                external_id=str(p['id']),
                source="leantime",
                name=p['name'],
                description=p.get('details', ''),
                status=self._map_status(p['state']),
                start_date=p.get('dateToFinish'),
                end_date=p.get('dateToFinish'),
            ))
        return projects
    
    # ... implement all other methods
```

### Asana Adapter

```python
class AsanaAdapter(PMAdapter):
    name = "asana"
    requires_oauth = True
    api_base_url = "https://app.asana.com/api/1.0"
    
    async def connect(self, credentials: dict) -> bool:
        self.access_token = credentials.get("access_token")
        self.workspace_gid = credentials.get("workspace_gid")
        self.session = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return await self.test_connection()
    
    async def list_projects(self) -> List[UnifiedProject]:
        response = await self.session.get(
            f"/workspaces/{self.workspace_gid}/projects",
            params={"opt_fields": "name,notes,due_date,start_on,current_status"}
        )
        projects = []
        for p in response.json()['data']:
            projects.append(UnifiedProject(
                id=f"asana:{p['gid']}",
                external_id=p['gid'],
                source="asana",
                name=p['name'],
                description=p.get('notes', ''),
                status=self._map_status(p.get('current_status')),
                start_date=p.get('start_on'),
                end_date=p.get('due_date'),
            ))
        return projects
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        response = await self.session.post(
            "/tasks",
            json={
                "data": {
                    "name": task.title,
                    "notes": task.description,
                    "projects": [task.project_id.replace("asana:", "")],
                    "due_on": str(task.due_date) if task.due_date else None,
                    "assignee": task.assignee_external_id,
                }
            }
        )
        # Map response back to UnifiedTask
        ...
```

### Jira Adapter

```python
class JiraAdapter(PMAdapter):
    name = "jira"
    requires_oauth = True  # Or API token
    api_base_url = None    # Set per instance (cloud vs server)
    
    async def connect(self, credentials: dict) -> bool:
        self.cloud_id = credentials.get("cloud_id")
        self.api_base_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}/rest/api/3"
        self.access_token = credentials.get("access_token")
        # Or basic auth with API token
        self.email = credentials.get("email")
        self.api_token = credentials.get("api_token")
        
        if self.access_token:
            self.auth_header = f"Bearer {self.access_token}"
        else:
            import base64
            creds = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            self.auth_header = f"Basic {creds}"
        
        self.session = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={"Authorization": self.auth_header}
        )
        return await self.test_connection()
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        jql = f"project = {project_id.replace('jira:', '')}"
        if filters:
            if filters.get('status'):
                jql += f" AND status = '{filters['status']}'"
            if filters.get('assignee'):
                jql += f" AND assignee = '{filters['assignee']}'"
        
        response = await self.session.get(
            "/search",
            params={"jql": jql, "fields": "summary,description,status,assignee,duedate,priority"}
        )
        
        tasks = []
        for issue in response.json()['issues']:
            tasks.append(UnifiedTask(
                id=f"jira:{issue['key']}",
                external_id=issue['key'],
                source="jira",
                project_id=project_id,
                title=issue['fields']['summary'],
                description=issue['fields'].get('description', ''),
                status=self._map_status(issue['fields']['status']['name']),
                priority=self._map_priority(issue['fields']['priority']['name']),
                assignee=issue['fields'].get('assignee', {}).get('displayName'),
                due_date=issue['fields'].get('duedate'),
            ))
        return tasks
```

### Monday.com Adapter

```python
class MondayAdapter(PMAdapter):
    name = "monday"
    requires_oauth = True
    api_base_url = "https://api.monday.com/v2"
    
    async def connect(self, credentials: dict) -> bool:
        self.api_key = credentials.get("api_key")
        self.session = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
        )
        return await self.test_connection()
    
    async def list_projects(self) -> List[UnifiedProject]:
        # Monday uses GraphQL
        query = """
        query {
            boards {
                id
                name
                description
                state
            }
        }
        """
        response = await self.session.post("", json={"query": query})
        
        projects = []
        for board in response.json()['data']['boards']:
            projects.append(UnifiedProject(
                id=f"monday:{board['id']}",
                external_id=board['id'],
                source="monday",
                name=board['name'],
                description=board.get('description', ''),
                status='active' if board['state'] == 'active' else 'completed',
            ))
        return projects
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        # Monday calls tasks "items"
        mutation = """
        mutation ($boardId: Int!, $itemName: String!, $columnValues: JSON) {
            create_item (
                board_id: $boardId,
                item_name: $itemName,
                column_values: $columnValues
            ) {
                id
                name
            }
        }
        """
        # Build column values based on task properties
        column_values = {}
        if task.due_date:
            column_values['date'] = {"date": str(task.due_date)}
        if task.assignee_external_id:
            column_values['person'] = {"personsAndTeams": [{"id": task.assignee_external_id, "kind": "person"}]}
        
        response = await self.session.post("", json={
            "query": mutation,
            "variables": {
                "boardId": int(task.project_id.replace("monday:", "")),
                "itemName": task.title,
                "columnValues": json.dumps(column_values)
            }
        })
        # Map response back
        ...
```

### Notion Adapter

```python
class NotionAdapter(PMAdapter):
    name = "notion"
    requires_oauth = True
    api_base_url = "https://api.notion.com/v1"
    
    async def connect(self, credentials: dict) -> bool:
        self.api_key = credentials.get("api_key")  # Integration token
        self.session = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
        )
        return await self.test_connection()
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        # Notion uses database queries
        database_id = project_id.replace("notion:", "")
        
        filter_obj = {"and": []}
        if filters:
            if filters.get('status'):
                filter_obj['and'].append({
                    "property": "Status",
                    "status": {"equals": filters['status']}
                })
        
        response = await self.session.post(
            f"/databases/{database_id}/query",
            json={"filter": filter_obj} if filter_obj['and'] else {}
        )
        
        tasks = []
        for page in response.json()['results']:
            props = page['properties']
            tasks.append(UnifiedTask(
                id=f"notion:{page['id']}",
                external_id=page['id'],
                source="notion",
                project_id=project_id,
                title=self._extract_title(props.get('Name', props.get('Title', {}))),
                status=self._map_status(props.get('Status', {}).get('status', {}).get('name')),
                assignee=self._extract_person(props.get('Assignee', {})),
                due_date=self._extract_date(props.get('Due Date', {})),
            ))
        return tasks
```

### Linear Adapter

```python
class LinearAdapter(PMAdapter):
    name = "linear"
    requires_oauth = True
    api_base_url = "https://api.linear.app/graphql"
    
    async def connect(self, credentials: dict) -> bool:
        self.api_key = credentials.get("api_key")
        self.session = httpx.AsyncClient(
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
        )
        return await self.test_connection()
    
    async def list_projects(self) -> List[UnifiedProject]:
        query = """
        query {
            projects {
                nodes {
                    id
                    name
                    description
                    state
                    startDate
                    targetDate
                }
            }
        }
        """
        response = await self.session.post(
            self.api_base_url,
            json={"query": query}
        )
        
        projects = []
        for p in response.json()['data']['projects']['nodes']:
            projects.append(UnifiedProject(
                id=f"linear:{p['id']}",
                external_id=p['id'],
                source="linear",
                name=p['name'],
                description=p.get('description', ''),
                status=self._map_status(p['state']),
                start_date=p.get('startDate'),
                end_date=p.get('targetDate'),
            ))
        return projects
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        # Linear calls tasks "issues"
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                }
            }
        }
        """
        response = await self.session.post(
            self.api_base_url,
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "title": task.title,
                        "description": task.description,
                        "projectId": task.project_id.replace("linear:", ""),
                        "dueDate": str(task.due_date) if task.due_date else None,
                        "assigneeId": task.assignee_external_id,
                    }
                }
            }
        )
        # Map response back
        ...
```

---

## DATABASE SCHEMA ADDITIONS

```sql
-- PM Tool Connections (credentials stored in AEGIS)
CREATE TABLE IF NOT EXISTS consul_pm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    tool_name TEXT NOT NULL,              -- "asana", "jira", etc.
    connection_name TEXT NOT NULL,         -- "Client ABC's Jira"
    
    -- Connection details
    instance_url TEXT,                     -- For self-hosted (Jira Server, etc.)
    workspace_id TEXT,                     -- Asana workspace, Jira project, etc.
    
    -- Auth reference (actual creds in AEGIS)
    aegis_credential_key TEXT NOT NULL,
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error')),
    last_sync TIMESTAMPTZ,
    last_error TEXT,
    
    -- Sync settings
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 15,
    webhook_registered BOOLEAN DEFAULT FALSE,
    webhook_id TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tool_name, connection_name)
);

-- Project mappings (link external projects to CONSUL)
CREATE TABLE IF NOT EXISTS consul_project_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    consul_project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
    external_project_id TEXT NOT NULL,
    external_project_name TEXT,
    
    -- Sync direction
    sync_direction TEXT DEFAULT 'bidirectional' CHECK (sync_direction IN (
        'from_source',      -- Only pull from external
        'to_source',        -- Only push to external
        'bidirectional'     -- Full sync
    )),
    
    -- Field mappings (which fields to sync)
    field_mappings JSONB DEFAULT '{}',
    
    last_sync TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(connection_id, external_project_id)
);

-- Task mappings
CREATE TABLE IF NOT EXISTS consul_task_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    consul_task_id UUID REFERENCES consul_tasks(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
    external_task_id TEXT NOT NULL,
    
    last_sync TIMESTAMPTZ,
    last_sync_hash TEXT,  -- To detect changes
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(connection_id, external_task_id)
);

-- Sync log
CREATE TABLE IF NOT EXISTS consul_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES consul_pm_connections(id),
    project_mapping_id UUID REFERENCES consul_project_mappings(id),
    
    sync_type TEXT CHECK (sync_type IN ('full', 'incremental', 'webhook')),
    direction TEXT CHECK (direction IN ('from_source', 'to_source')),
    
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    items_synced INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    
    error_details JSONB DEFAULT '[]',
    
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed'))
);

-- Status mappings per connection
CREATE TABLE IF NOT EXISTS consul_status_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
    consul_status TEXT NOT NULL,          -- Our status
    external_status TEXT NOT NULL,        -- Their status
    
    UNIQUE(connection_id, consul_status, external_status)
);

-- Priority mappings per connection  
CREATE TABLE IF NOT EXISTS consul_priority_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
    consul_priority TEXT NOT NULL,
    external_priority TEXT NOT NULL,
    
    UNIQUE(connection_id, consul_priority, external_priority)
);
```

---

## CONSUL SKILL MATRIX

### Core PM Skills

| Skill | Description | Level |
|-------|-------------|-------|
| **Project Decomposition** | Break large goals into actionable tasks | Expert |
| **Dependency Mapping** | Identify and track task dependencies | Expert |
| **Critical Path Analysis** | Find the longest path to completion | Expert |
| **Resource Allocation** | Match tasks to available agents | Expert |
| **Risk Assessment** | Identify and quantify project risks | Advanced |
| **Velocity Tracking** | Measure team throughput over time | Expert |
| **Burndown/Burnup** | Track progress toward milestones | Expert |
| **Scope Management** | Document and assess scope changes | Expert |
| **Stakeholder Comms** | Keep everyone informed appropriately | Expert |

### Methodology Knowledge

| Methodology | CONSUL's Approach |
|-------------|------------------|
| **Agile/Scrum** | Sprint planning, daily standups, retrospectives |
| **Kanban** | WIP limits, flow optimization, cycle time |
| **Waterfall** | Phase gates, milestone tracking, documentation |
| **Hybrid** | Adapts to client's preferred approach |
| **ADHD-Friendly** | Time boxing, body doubling, external accountability |

### Tool-Specific Skills

| Tool | API Features CONSUL Uses |
|------|-------------------------|
| **Leantime** | Projects, tasks, time tracking, milestones |
| **OpenProject** | Work packages, Gantt, resources, costs |
| **Asana** | Tasks, sections, portfolios, goals, forms |
| **Jira** | Issues, sprints, boards, JQL, automation |
| **Monday** | Boards, items, columns, automations |
| **Notion** | Databases, pages, relations, rollups |
| **Linear** | Issues, projects, cycles, roadmaps |
| **ClickUp** | Tasks, goals, time tracking, dashboards |
| **Trello** | Cards, lists, power-ups, automation |

---

## MCP TOOLS (Expanded)

```python
# ============ CONNECTION MANAGEMENT ============

@mcp_tool(name="consul_connect_tool")
async def connect_pm_tool(
    tool_name: str,        # "asana", "jira", "notion", etc.
    connection_name: str,  # "Client ABC's Jira"
    credentials: dict      # Will be stored in AEGIS
) -> dict:
    """Connect CONSUL to an external PM tool"""

@mcp_tool(name="consul_list_connections")
async def list_connections() -> List[dict]:
    """List all PM tool connections"""

@mcp_tool(name="consul_test_connection")
async def test_connection(connection_id: str) -> dict:
    """Test a PM tool connection"""

@mcp_tool(name="consul_sync_project")
async def sync_project(
    connection_id: str,
    external_project_id: str,
    direction: str = "bidirectional"
) -> dict:
    """Sync a project with external tool"""

# ============ UNIFIED PROJECT OPERATIONS ============

@mcp_tool(name="consul_create_project")
async def create_project(
    name: str,
    description: str = None,
    target_end: str = None,
    tool: str = "leantime",      # Which tool to create in
    sync_to: List[str] = None    # Also create in these tools
) -> dict:
    """Create project (optionally in multiple tools)"""

@mcp_tool(name="consul_create_task")
async def create_task(
    project_id: str,
    title: str,
    assigned_agent: str = None,
    due_date: str = None,
    estimated_hours: float = None,
    sync: bool = True            # Sync to connected tools
) -> dict:
    """Create task with optional external sync"""

@mcp_tool(name="consul_move_task")
async def move_task(
    task_id: str,
    new_status: str,
    sync: bool = True
) -> dict:
    """Move task to new status (syncs to external tools)"""

# ============ MULTI-TOOL QUERIES ============

@mcp_tool(name="consul_search_all")
async def search_all_tools(
    query: str,
    tools: List[str] = None      # None = search all connected
) -> dict:
    """Search across all connected PM tools"""

@mcp_tool(name="consul_aggregate_status")
async def aggregate_status() -> dict:
    """Get unified status across all tools and projects"""

@mcp_tool(name="consul_cross_tool_report")
async def cross_tool_report(
    report_type: str,            # "overdue", "blocked", "velocity"
    tools: List[str] = None
) -> dict:
    """Generate report across multiple PM tools"""

# ============ CLIENT ONBOARDING ============

@mcp_tool(name="consul_onboard_client")
async def onboard_client(
    client_name: str,
    tool_name: str,              # Which PM tool they use
    credentials: dict,
    project_ids: List[str]       # Which projects to sync
) -> dict:
    """Onboard a new client with their PM tool"""

@mcp_tool(name="consul_setup_client_workspace")
async def setup_client_workspace(
    client_name: str,
    template: str = "automation_project"  # Use project template
) -> dict:
    """Set up new client workspace in CONSUL"""
```

---

## CONSUL'S ADVANCED CAPABILITIES

### 1. Cross-Tool Dashboards

CONSUL can show unified views across ALL connected tools:

```
┌─────────────────────────────────────────────────────────────────┐
│              CONSUL UNIFIED DASHBOARD                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INTERNAL (Leantime)           │  CLIENT A (Asana)             │
│  ├─ LeverEdge Launch: 45%      │  ├─ Automation Project: 60%   │
│  ├─ Tasks: 12 todo, 5 done     │  ├─ Tasks: 8 todo, 12 done    │
│  └─ Blockers: 1                │  └─ Blockers: 0               │
│                                 │                               │
│  CLIENT B (Jira)               │  CLIENT C (Monday)            │
│  ├─ Integration Sprint: 30%    │  ├─ Marketing Auto: 80%       │
│  ├─ Issues: 6 open, 14 closed  │  ├─ Items: 3 todo, 9 done     │
│  └─ Blockers: 2                │  └─ Blockers: 0               │
│                                                                 │
│  TOTAL: 4 projects, 29 open tasks, 3 blockers                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Intelligent Task Routing

CONSUL knows which tool to create tasks in based on:
- Project ownership (internal vs client)
- Client's preferred tool
- Task type (dev work → Jira, marketing → Monday)

### 3. Automated Sync

- **Webhook listeners** for real-time updates
- **Scheduled sync** for tools without webhooks
- **Conflict resolution** when same task updated in multiple places

### 4. Template System

Pre-built project templates:
- `automation_project` - For client automation builds
- `agent_development` - For building new agents
- `infrastructure` - For infra work
- `client_onboarding` - For new client setup

---

## BUILD PHASES (Updated)

| Phase | Component | Time |
|-------|-----------|------|
| 1 | Deploy Leantime + OpenProject | 2 hrs |
| 2 | CONSUL core + database schema | 4 hrs |
| 3 | Leantime adapter | 2 hrs |
| 4 | OpenProject adapter | 2 hrs |
| 5 | Adapter framework + base class | 2 hrs |
| 6 | Asana adapter | 2 hrs |
| 7 | Jira adapter | 2 hrs |
| 8 | Monday adapter | 2 hrs |
| 9 | Notion adapter | 2 hrs |
| 10 | Linear adapter | 2 hrs |
| 11 | MCP tools integration | 2 hrs |
| 12 | Sync engine + webhooks | 4 hrs |
| **Total** | | **28 hrs** |

**MVP (Phases 1-5):** 12 hours - Internal tools working
**Full Build:** 28 hours - All major adapters

---

*"I speak every PM language. Your clients use Jira? I use Jira. They use Notion? I use Notion. Nothing escapes my attention. Nothing falls through the cracks."*
