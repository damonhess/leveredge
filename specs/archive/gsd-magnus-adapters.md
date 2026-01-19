# GSD: MAGNUS PM Tool Adapters

**Priority:** MEDIUM
**Estimated Time:** 2 hours each adapter
**Component:** MAGNUS Enhancement

---

## OVERVIEW

Implement adapters for major PM tools so MAGNUS can sync with clients' existing systems:
- **Asana** - REST API
- **Jira** - REST API
- **Monday.com** - GraphQL
- **Notion** - REST API
- **Linear** - GraphQL

---

## ADAPTER INTERFACE

All adapters implement `PMAdapter` base class:

```python
# /opt/leveredge/control-plane/agents/magnus/adapters/base.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class UnifiedProject(BaseModel):
    id: Optional[str] = None
    external_id: Optional[str] = None
    source: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class UnifiedTask(BaseModel):
    id: Optional[str] = None
    external_id: Optional[str] = None
    source: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    tags: List[str] = []

class PMAdapter(ABC):
    name: str
    requires_oauth: bool = False
    
    @abstractmethod
    async def connect(self, credentials: dict) -> bool:
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        pass
    
    @abstractmethod
    async def list_projects(self) -> List[UnifiedProject]:
        pass
    
    @abstractmethod
    async def list_tasks(self, project_id: str) -> List[UnifiedTask]:
        pass
    
    @abstractmethod
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        pass
    
    @abstractmethod
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        pass
    
    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        pass
```

---

## ADAPTER 1: ASANA

```python
# /opt/leveredge/control-plane/agents/magnus/adapters/asana.py

"""
Asana PM Adapter
API Docs: https://developers.asana.com/reference
"""

import httpx
from typing import List, Optional
from .base import PMAdapter, UnifiedProject, UnifiedTask, TaskStatus, Priority

class AsanaAdapter(PMAdapter):
    name = "asana"
    requires_oauth = True
    api_base = "https://app.asana.com/api/1.0"
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.workspace_gid: Optional[str] = None
    
    async def connect(self, credentials: dict) -> bool:
        """Connect with OAuth token or PAT"""
        token = credentials.get("access_token") or credentials.get("pat")
        self.workspace_gid = credentials.get("workspace_gid")
        
        self.session = httpx.AsyncClient(
            base_url=self.api_base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        
        return await self.test_connection()
    
    async def test_connection(self) -> bool:
        try:
            response = await self.session.get("/users/me")
            return response.status_code == 200
        except:
            return False
    
    async def list_projects(self) -> List[UnifiedProject]:
        response = await self.session.get(
            f"/workspaces/{self.workspace_gid}/projects",
            params={"opt_fields": "name,notes,due_date,start_on,current_status"}
        )
        
        projects = []
        for p in response.json().get("data", []):
            projects.append(UnifiedProject(
                external_id=p["gid"],
                source="asana",
                name=p["name"],
                description=p.get("notes"),
                start_date=p.get("start_on"),
                end_date=p.get("due_date"),
            ))
        return projects
    
    async def get_project(self, project_id: str) -> UnifiedProject:
        gid = project_id.replace("asana:", "")
        response = await self.session.get(
            f"/projects/{gid}",
            params={"opt_fields": "name,notes,due_date,start_on"}
        )
        p = response.json().get("data", {})
        return UnifiedProject(
            external_id=p["gid"],
            source="asana",
            name=p["name"],
            description=p.get("notes"),
        )
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        gid = project_id.replace("asana:", "")
        response = await self.session.get(
            f"/projects/{gid}/tasks",
            params={
                "opt_fields": "name,notes,due_on,assignee,completed,memberships.section.name,tags"
            }
        )
        
        tasks = []
        for t in response.json().get("data", []):
            tasks.append(UnifiedTask(
                external_id=t["gid"],
                source="asana",
                project_id=project_id,
                title=t["name"],
                description=t.get("notes"),
                status=TaskStatus.DONE if t.get("completed") else self._map_section_to_status(t),
                assignee=t.get("assignee", {}).get("name") if t.get("assignee") else None,
                due_date=t.get("due_on"),
            ))
        return tasks
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        gid = task.project_id.replace("asana:", "")
        
        response = await self.session.post(
            "/tasks",
            json={
                "data": {
                    "name": task.title,
                    "notes": task.description or "",
                    "projects": [gid],
                    "due_on": str(task.due_date) if task.due_date else None,
                }
            }
        )
        
        result = response.json().get("data", {})
        task.external_id = result.get("gid")
        return task
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        gid = task_id.replace("asana:", "")
        
        data = {}
        if "title" in updates:
            data["name"] = updates["title"]
        if "description" in updates:
            data["notes"] = updates["description"]
        if "due_date" in updates:
            data["due_on"] = str(updates["due_date"])
        if "status" in updates:
            data["completed"] = updates["status"] == TaskStatus.DONE
        
        await self.session.put(f"/tasks/{gid}", json={"data": data})
        return await self.get_task(task_id)
    
    async def delete_task(self, task_id: str) -> bool:
        gid = task_id.replace("asana:", "")
        response = await self.session.delete(f"/tasks/{gid}")
        return response.status_code == 200
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        gid = task_id.replace("asana:", "")
        response = await self.session.get(
            f"/tasks/{gid}",
            params={"opt_fields": "name,notes,due_on,assignee,completed"}
        )
        t = response.json().get("data", {})
        return UnifiedTask(
            external_id=t["gid"],
            source="asana",
            project_id="",
            title=t["name"],
            description=t.get("notes"),
            status=TaskStatus.DONE if t.get("completed") else TaskStatus.TODO,
            due_date=t.get("due_on"),
        )
    
    def _map_section_to_status(self, task: dict) -> TaskStatus:
        """Map Asana section to task status"""
        memberships = task.get("memberships", [])
        if memberships:
            section = memberships[0].get("section", {}).get("name", "").lower()
            if "done" in section or "complete" in section:
                return TaskStatus.DONE
            elif "progress" in section or "doing" in section:
                return TaskStatus.IN_PROGRESS
            elif "review" in section:
                return TaskStatus.REVIEW
            elif "block" in section:
                return TaskStatus.BLOCKED
        return TaskStatus.TODO
```

---

## ADAPTER 2: JIRA

```python
# /opt/leveredge/control-plane/agents/magnus/adapters/jira.py

"""
Jira PM Adapter
API Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

import httpx
import base64
from typing import List, Optional
from .base import PMAdapter, UnifiedProject, UnifiedTask, TaskStatus, Priority

class JiraAdapter(PMAdapter):
    name = "jira"
    requires_oauth = False  # Can use API token
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.cloud_id: Optional[str] = None
    
    async def connect(self, credentials: dict) -> bool:
        """Connect with email + API token or OAuth"""
        email = credentials.get("email")
        api_token = credentials.get("api_token")
        domain = credentials.get("domain")  # e.g., "yourcompany.atlassian.net"
        
        if email and api_token:
            # Basic auth with API token
            auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}"}
        else:
            # OAuth
            headers = {"Authorization": f"Bearer {credentials.get('access_token')}"}
        
        self.session = httpx.AsyncClient(
            base_url=f"https://{domain}/rest/api/3",
            headers=headers,
            timeout=30.0
        )
        
        return await self.test_connection()
    
    async def test_connection(self) -> bool:
        try:
            response = await self.session.get("/myself")
            return response.status_code == 200
        except:
            return False
    
    async def list_projects(self) -> List[UnifiedProject]:
        response = await self.session.get("/project/search")
        
        projects = []
        for p in response.json().get("values", []):
            projects.append(UnifiedProject(
                external_id=p["key"],
                source="jira",
                name=p["name"],
                description=p.get("description"),
            ))
        return projects
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        key = project_id.replace("jira:", "")
        
        jql = f"project = {key}"
        if filters:
            if filters.get("status"):
                jql += f" AND status = '{filters['status']}'"
            if filters.get("assignee"):
                jql += f" AND assignee = '{filters['assignee']}'"
        
        response = await self.session.get(
            "/search",
            params={
                "jql": jql,
                "fields": "summary,description,status,assignee,duedate,priority"
            }
        )
        
        tasks = []
        for issue in response.json().get("issues", []):
            fields = issue["fields"]
            tasks.append(UnifiedTask(
                external_id=issue["key"],
                source="jira",
                project_id=project_id,
                title=fields["summary"],
                description=self._extract_description(fields.get("description")),
                status=self._map_status(fields.get("status", {}).get("name")),
                priority=self._map_priority(fields.get("priority", {}).get("name")),
                assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                due_date=fields.get("duedate"),
            ))
        return tasks
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        key = task.project_id.replace("jira:", "")
        
        response = await self.session.post(
            "/issue",
            json={
                "fields": {
                    "project": {"key": key},
                    "summary": task.title,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": task.description or ""}]}]
                    },
                    "issuetype": {"name": "Task"},
                    "duedate": str(task.due_date) if task.due_date else None,
                }
            }
        )
        
        result = response.json()
        task.external_id = result.get("key")
        return task
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        key = task_id.replace("jira:", "")
        
        fields = {}
        if "title" in updates:
            fields["summary"] = updates["title"]
        if "due_date" in updates:
            fields["duedate"] = str(updates["due_date"])
        
        if fields:
            await self.session.put(f"/issue/{key}", json={"fields": fields})
        
        # Handle status transition separately
        if "status" in updates:
            await self._transition_issue(key, updates["status"])
        
        return await self.get_task(task_id)
    
    async def _transition_issue(self, key: str, target_status: str):
        """Transition issue to new status"""
        # Get available transitions
        response = await self.session.get(f"/issue/{key}/transitions")
        transitions = response.json().get("transitions", [])
        
        # Find matching transition
        for t in transitions:
            if target_status.lower() in t["name"].lower():
                await self.session.post(
                    f"/issue/{key}/transitions",
                    json={"transition": {"id": t["id"]}}
                )
                break
    
    async def delete_task(self, task_id: str) -> bool:
        key = task_id.replace("jira:", "")
        response = await self.session.delete(f"/issue/{key}")
        return response.status_code == 204
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        key = task_id.replace("jira:", "")
        response = await self.session.get(f"/issue/{key}")
        issue = response.json()
        fields = issue["fields"]
        
        return UnifiedTask(
            external_id=issue["key"],
            source="jira",
            project_id=f"jira:{fields['project']['key']}",
            title=fields["summary"],
            status=self._map_status(fields.get("status", {}).get("name")),
            due_date=fields.get("duedate"),
        )
    
    def _map_status(self, jira_status: str) -> TaskStatus:
        if not jira_status:
            return TaskStatus.TODO
        status_lower = jira_status.lower()
        if "done" in status_lower or "closed" in status_lower or "resolved" in status_lower:
            return TaskStatus.DONE
        elif "progress" in status_lower:
            return TaskStatus.IN_PROGRESS
        elif "review" in status_lower:
            return TaskStatus.REVIEW
        elif "blocked" in status_lower:
            return TaskStatus.BLOCKED
        return TaskStatus.TODO
    
    def _map_priority(self, jira_priority: str) -> Priority:
        if not jira_priority:
            return Priority.MEDIUM
        priority_lower = jira_priority.lower()
        if "highest" in priority_lower or "critical" in priority_lower:
            return Priority.CRITICAL
        elif "high" in priority_lower:
            return Priority.HIGH
        elif "low" in priority_lower or "lowest" in priority_lower:
            return Priority.LOW
        return Priority.MEDIUM
    
    def _extract_description(self, desc: dict) -> str:
        """Extract text from Jira's ADF format"""
        if not desc:
            return ""
        if isinstance(desc, str):
            return desc
        
        text_parts = []
        for content in desc.get("content", []):
            if content.get("type") == "paragraph":
                for c in content.get("content", []):
                    if c.get("type") == "text":
                        text_parts.append(c.get("text", ""))
        return " ".join(text_parts)
```

---

## ADAPTER 3: MONDAY.COM

```python
# /opt/leveredge/control-plane/agents/magnus/adapters/monday.py

"""
Monday.com PM Adapter
API Docs: https://developer.monday.com/api-reference/docs
"""

import httpx
from typing import List, Optional
from .base import PMAdapter, UnifiedProject, UnifiedTask, TaskStatus, Priority

class MondayAdapter(PMAdapter):
    name = "monday"
    requires_oauth = False  # API key works
    api_base = "https://api.monday.com/v2"
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
    
    async def connect(self, credentials: dict) -> bool:
        api_key = credentials.get("api_key")
        
        self.session = httpx.AsyncClient(
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        return await self.test_connection()
    
    async def test_connection(self) -> bool:
        try:
            response = await self.session.post(
                self.api_base,
                json={"query": "query { me { id } }"}
            )
            return "data" in response.json()
        except:
            return False
    
    async def list_projects(self) -> List[UnifiedProject]:
        """Monday calls projects 'boards'"""
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
        
        response = await self.session.post(self.api_base, json={"query": query})
        
        projects = []
        for board in response.json().get("data", {}).get("boards", []):
            projects.append(UnifiedProject(
                external_id=board["id"],
                source="monday",
                name=board["name"],
                description=board.get("description"),
                status="active" if board["state"] == "active" else "completed",
            ))
        return projects
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        """Monday calls tasks 'items'"""
        board_id = project_id.replace("monday:", "")
        
        query = f"""
        query {{
            boards(ids: [{board_id}]) {{
                items_page {{
                    items {{
                        id
                        name
                        column_values {{
                            id
                            text
                            value
                        }}
                    }}
                }}
            }}
        }}
        """
        
        response = await self.session.post(self.api_base, json={"query": query})
        
        tasks = []
        boards = response.json().get("data", {}).get("boards", [])
        if boards:
            items = boards[0].get("items_page", {}).get("items", [])
            for item in items:
                task = UnifiedTask(
                    external_id=item["id"],
                    source="monday",
                    project_id=project_id,
                    title=item["name"],
                    status=TaskStatus.TODO,
                )
                
                # Parse column values
                for col in item.get("column_values", []):
                    if col["id"] == "status":
                        task.status = self._map_status(col.get("text"))
                    elif col["id"] == "person":
                        task.assignee = col.get("text")
                    elif col["id"] == "date":
                        task.due_date = col.get("text")
                
                tasks.append(task)
        
        return tasks
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        board_id = task.project_id.replace("monday:", "")
        
        # Build column values
        column_values = {}
        if task.due_date:
            column_values["date"] = {"date": str(task.due_date)}
        
        mutation = f"""
        mutation {{
            create_item (
                board_id: {board_id},
                item_name: "{task.title}",
                column_values: "{str(column_values).replace('"', '\\"')}"
            ) {{
                id
            }}
        }}
        """
        
        response = await self.session.post(self.api_base, json={"query": mutation})
        result = response.json().get("data", {}).get("create_item", {})
        task.external_id = result.get("id")
        return task
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        item_id = task_id.replace("monday:", "")
        
        if "title" in updates:
            mutation = f"""
            mutation {{
                change_simple_column_value(
                    item_id: {item_id},
                    board_id: 0,
                    column_id: "name",
                    value: "{updates['title']}"
                ) {{
                    id
                }}
            }}
            """
            await self.session.post(self.api_base, json={"query": mutation})
        
        return await self.get_task(task_id)
    
    async def delete_task(self, task_id: str) -> bool:
        item_id = task_id.replace("monday:", "")
        
        mutation = f"""
        mutation {{
            delete_item(item_id: {item_id}) {{
                id
            }}
        }}
        """
        
        response = await self.session.post(self.api_base, json={"query": mutation})
        return "data" in response.json()
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        item_id = task_id.replace("monday:", "")
        
        query = f"""
        query {{
            items(ids: [{item_id}]) {{
                id
                name
                board {{
                    id
                }}
                column_values {{
                    id
                    text
                }}
            }}
        }}
        """
        
        response = await self.session.post(self.api_base, json={"query": query})
        items = response.json().get("data", {}).get("items", [])
        
        if items:
            item = items[0]
            return UnifiedTask(
                external_id=item["id"],
                source="monday",
                project_id=f"monday:{item['board']['id']}",
                title=item["name"],
                status=TaskStatus.TODO,
            )
        
        raise Exception(f"Task {task_id} not found")
    
    def _map_status(self, status_text: str) -> TaskStatus:
        if not status_text:
            return TaskStatus.TODO
        status_lower = status_text.lower()
        if "done" in status_lower or "complete" in status_lower:
            return TaskStatus.DONE
        elif "working" in status_lower or "progress" in status_lower:
            return TaskStatus.IN_PROGRESS
        elif "stuck" in status_lower or "blocked" in status_lower:
            return TaskStatus.BLOCKED
        return TaskStatus.TODO
```

---

## ADAPTER 4: NOTION

```python
# /opt/leveredge/control-plane/agents/magnus/adapters/notion.py

"""
Notion PM Adapter
API Docs: https://developers.notion.com/reference
"""

import httpx
from typing import List, Optional
from .base import PMAdapter, UnifiedProject, UnifiedTask, TaskStatus, Priority

class NotionAdapter(PMAdapter):
    name = "notion"
    requires_oauth = True
    api_base = "https://api.notion.com/v1"
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
    
    async def connect(self, credentials: dict) -> bool:
        token = credentials.get("api_key") or credentials.get("access_token")
        
        self.session = httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        return await self.test_connection()
    
    async def test_connection(self) -> bool:
        try:
            response = await self.session.get("/users/me")
            return response.status_code == 200
        except:
            return False
    
    async def list_projects(self) -> List[UnifiedProject]:
        """List databases as projects"""
        response = await self.session.post(
            "/search",
            json={"filter": {"property": "object", "value": "database"}}
        )
        
        projects = []
        for db in response.json().get("results", []):
            title = ""
            for t in db.get("title", []):
                title += t.get("plain_text", "")
            
            projects.append(UnifiedProject(
                external_id=db["id"],
                source="notion",
                name=title or "Untitled",
            ))
        return projects
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        """Query database for tasks"""
        db_id = project_id.replace("notion:", "")
        
        filter_obj = {}
        if filters and filters.get("status"):
            filter_obj = {
                "property": "Status",
                "status": {"equals": filters["status"]}
            }
        
        response = await self.session.post(
            f"/databases/{db_id}/query",
            json={"filter": filter_obj} if filter_obj else {}
        )
        
        tasks = []
        for page in response.json().get("results", []):
            props = page.get("properties", {})
            
            # Extract title
            title = ""
            for prop in props.values():
                if prop.get("type") == "title":
                    for t in prop.get("title", []):
                        title += t.get("plain_text", "")
                    break
            
            task = UnifiedTask(
                external_id=page["id"],
                source="notion",
                project_id=project_id,
                title=title or "Untitled",
                status=self._extract_status(props),
                assignee=self._extract_person(props),
                due_date=self._extract_date(props),
            )
            tasks.append(task)
        
        return tasks
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        db_id = task.project_id.replace("notion:", "")
        
        properties = {
            "Name": {
                "title": [{"text": {"content": task.title}}]
            }
        }
        
        if task.due_date:
            properties["Due Date"] = {
                "date": {"start": str(task.due_date)}
            }
        
        response = await self.session.post(
            "/pages",
            json={
                "parent": {"database_id": db_id},
                "properties": properties
            }
        )
        
        result = response.json()
        task.external_id = result.get("id")
        return task
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        page_id = task_id.replace("notion:", "")
        
        properties = {}
        if "title" in updates:
            properties["Name"] = {
                "title": [{"text": {"content": updates["title"]}}]
            }
        if "due_date" in updates:
            properties["Due Date"] = {
                "date": {"start": str(updates["due_date"])}
            }
        
        if properties:
            await self.session.patch(
                f"/pages/{page_id}",
                json={"properties": properties}
            )
        
        return await self.get_task(task_id)
    
    async def delete_task(self, task_id: str) -> bool:
        page_id = task_id.replace("notion:", "")
        response = await self.session.patch(
            f"/pages/{page_id}",
            json={"archived": True}
        )
        return response.status_code == 200
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        page_id = task_id.replace("notion:", "")
        response = await self.session.get(f"/pages/{page_id}")
        page = response.json()
        props = page.get("properties", {})
        
        title = ""
        for prop in props.values():
            if prop.get("type") == "title":
                for t in prop.get("title", []):
                    title += t.get("plain_text", "")
                break
        
        return UnifiedTask(
            external_id=page["id"],
            source="notion",
            project_id=f"notion:{page['parent']['database_id']}",
            title=title or "Untitled",
            status=self._extract_status(props),
        )
    
    def _extract_status(self, props: dict) -> TaskStatus:
        for prop in props.values():
            if prop.get("type") == "status":
                status_name = prop.get("status", {}).get("name", "").lower()
                if "done" in status_name or "complete" in status_name:
                    return TaskStatus.DONE
                elif "progress" in status_name:
                    return TaskStatus.IN_PROGRESS
        return TaskStatus.TODO
    
    def _extract_person(self, props: dict) -> Optional[str]:
        for prop in props.values():
            if prop.get("type") == "people":
                people = prop.get("people", [])
                if people:
                    return people[0].get("name")
        return None
    
    def _extract_date(self, props: dict) -> Optional[str]:
        for prop in props.values():
            if prop.get("type") == "date":
                date_obj = prop.get("date")
                if date_obj:
                    return date_obj.get("start")
        return None
```

---

## ADAPTER 5: LINEAR

```python
# /opt/leveredge/control-plane/agents/magnus/adapters/linear.py

"""
Linear PM Adapter
API Docs: https://developers.linear.app/docs
"""

import httpx
from typing import List, Optional
from .base import PMAdapter, UnifiedProject, UnifiedTask, TaskStatus, Priority

class LinearAdapter(PMAdapter):
    name = "linear"
    requires_oauth = True
    api_base = "https://api.linear.app/graphql"
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
    
    async def connect(self, credentials: dict) -> bool:
        token = credentials.get("api_key")
        
        self.session = httpx.AsyncClient(
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        return await self.test_connection()
    
    async def test_connection(self) -> bool:
        try:
            response = await self.session.post(
                self.api_base,
                json={"query": "query { viewer { id } }"}
            )
            return "data" in response.json()
        except:
            return False
    
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
        
        response = await self.session.post(self.api_base, json={"query": query})
        
        projects = []
        for p in response.json().get("data", {}).get("projects", {}).get("nodes", []):
            projects.append(UnifiedProject(
                external_id=p["id"],
                source="linear",
                name=p["name"],
                description=p.get("description"),
                start_date=p.get("startDate"),
                end_date=p.get("targetDate"),
            ))
        return projects
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        """Linear calls tasks 'issues'"""
        proj_id = project_id.replace("linear:", "")
        
        query = f"""
        query {{
            project(id: "{proj_id}") {{
                issues {{
                    nodes {{
                        id
                        identifier
                        title
                        description
                        state {{
                            name
                        }}
                        priority
                        assignee {{
                            name
                        }}
                        dueDate
                    }}
                }}
            }}
        }}
        """
        
        response = await self.session.post(self.api_base, json={"query": query})
        
        tasks = []
        issues = response.json().get("data", {}).get("project", {}).get("issues", {}).get("nodes", [])
        
        for issue in issues:
            tasks.append(UnifiedTask(
                external_id=issue["id"],
                source="linear",
                project_id=project_id,
                title=issue["title"],
                description=issue.get("description"),
                status=self._map_status(issue.get("state", {}).get("name")),
                priority=self._map_priority(issue.get("priority")),
                assignee=issue.get("assignee", {}).get("name") if issue.get("assignee") else None,
                due_date=issue.get("dueDate"),
            ))
        
        return tasks
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        proj_id = task.project_id.replace("linear:", "")
        
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                }
            }
        }
        """
        
        variables = {
            "input": {
                "title": task.title,
                "description": task.description,
                "projectId": proj_id,
            }
        }
        
        if task.due_date:
            variables["input"]["dueDate"] = str(task.due_date)
        
        response = await self.session.post(
            self.api_base,
            json={"query": mutation, "variables": variables}
        )
        
        result = response.json().get("data", {}).get("issueCreate", {})
        if result.get("success"):
            task.external_id = result.get("issue", {}).get("id")
        
        return task
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        issue_id = task_id.replace("linear:", "")
        
        mutation = """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
            }
        }
        """
        
        input_data = {}
        if "title" in updates:
            input_data["title"] = updates["title"]
        if "description" in updates:
            input_data["description"] = updates["description"]
        if "due_date" in updates:
            input_data["dueDate"] = str(updates["due_date"])
        
        await self.session.post(
            self.api_base,
            json={
                "query": mutation,
                "variables": {"id": issue_id, "input": input_data}
            }
        )
        
        return await self.get_task(task_id)
    
    async def delete_task(self, task_id: str) -> bool:
        issue_id = task_id.replace("linear:", "")
        
        mutation = """
        mutation IssueDelete($id: String!) {
            issueDelete(id: $id) {
                success
            }
        }
        """
        
        response = await self.session.post(
            self.api_base,
            json={"query": mutation, "variables": {"id": issue_id}}
        )
        
        return response.json().get("data", {}).get("issueDelete", {}).get("success", False)
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        issue_id = task_id.replace("linear:", "")
        
        query = f"""
        query {{
            issue(id: "{issue_id}") {{
                id
                title
                description
                state {{
                    name
                }}
                project {{
                    id
                }}
                dueDate
            }}
        }}
        """
        
        response = await self.session.post(self.api_base, json={"query": query})
        issue = response.json().get("data", {}).get("issue", {})
        
        return UnifiedTask(
            external_id=issue["id"],
            source="linear",
            project_id=f"linear:{issue.get('project', {}).get('id', '')}",
            title=issue["title"],
            description=issue.get("description"),
            status=self._map_status(issue.get("state", {}).get("name")),
            due_date=issue.get("dueDate"),
        )
    
    def _map_status(self, state_name: str) -> TaskStatus:
        if not state_name:
            return TaskStatus.TODO
        state_lower = state_name.lower()
        if "done" in state_lower or "completed" in state_lower:
            return TaskStatus.DONE
        elif "progress" in state_lower or "started" in state_lower:
            return TaskStatus.IN_PROGRESS
        elif "review" in state_lower:
            return TaskStatus.REVIEW
        elif "blocked" in state_lower:
            return TaskStatus.BLOCKED
        elif "canceled" in state_lower or "cancelled" in state_lower:
            return TaskStatus.CANCELLED
        return TaskStatus.TODO
    
    def _map_priority(self, priority: int) -> Priority:
        if priority is None:
            return Priority.MEDIUM
        if priority <= 1:
            return Priority.CRITICAL
        elif priority == 2:
            return Priority.HIGH
        elif priority == 3:
            return Priority.MEDIUM
        return Priority.LOW
```

---

## REGISTER ADAPTERS IN MAGNUS

Update `/opt/leveredge/control-plane/agents/magnus/magnus.py`:

```python
# Import all adapters
from adapters.base import PMAdapter
from adapters.leantime import LeantimeAdapter
from adapters.asana import AsanaAdapter
from adapters.jira import JiraAdapter
from adapters.monday import MondayAdapter
from adapters.notion import NotionAdapter
from adapters.linear import LinearAdapter

# Registry
ADAPTERS = {
    "leantime": LeantimeAdapter,
    "asana": AsanaAdapter,
    "jira": JiraAdapter,
    "monday": MondayAdapter,
    "notion": NotionAdapter,
    "linear": LinearAdapter,
}
```

---

## BUILD & TEST

```bash
# Copy adapters to MAGNUS service
cp adapters/*.py /opt/leveredge/control-plane/agents/magnus/adapters/

# Rebuild MAGNUS
cd /opt/leveredge/control-plane/agents/magnus
docker build -t magnus:dev .
docker stop magnus && docker rm magnus
docker run -d --name magnus \
  --network leveredge-network \
  -p 8019:8017 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  magnus:dev

# Test adapter availability
curl http://localhost:8019/connections/supported | jq .
```

---

## GIT COMMIT

```bash
git add .
git commit -m "MAGNUS Adapters: Asana, Jira, Monday, Notion, Linear

- Asana: REST API adapter with section-based status mapping
- Jira: REST API adapter with JQL support and transitions
- Monday.com: GraphQL adapter with column value parsing
- Notion: REST API adapter with database queries
- Linear: GraphQL adapter with issue management

MAGNUS now speaks 6 PM languages."
```

---

*"Your clients use Jira? I use Jira. They use Notion? I use Notion. I adapt."*
