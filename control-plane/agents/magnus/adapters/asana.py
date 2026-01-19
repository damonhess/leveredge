"""
MAGNUS Asana Adapter

Connects to Asana for project management.
API Docs: https://developers.asana.com/reference
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class AsanaAdapter(PMAdapter):
    """
    Adapter for Asana PM tool.
    Uses OAuth token or Personal Access Token (PAT).
    """

    tool_name = "asana"

    # Status mappings (based on section names)
    STATUS_TO_UNIFIED = {
        "to do": "todo",
        "todo": "todo",
        "in progress": "in_progress",
        "doing": "in_progress",
        "blocked": "blocked",
        "review": "review",
        "done": "done",
        "complete": "done",
        "completed": "done",
    }

    STATUS_FROM_UNIFIED = {
        "todo": "To Do",
        "in_progress": "In Progress",
        "blocked": "Blocked",
        "review": "Review",
        "done": "Done",
        "cancelled": "Done",
    }

    PRIORITY_TO_UNIFIED = {
        "high": "high",
        "medium": "medium",
        "low": "low",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = self.credentials.get("access_token") or self.credentials.get("pat", "")
        self.workspace_gid = config.get("workspace_gid", "")
        self.api_base = "https://app.asana.com/api/1.0"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test connection to Asana"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/users/me",
                    headers=self._headers(),
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_projects(self) -> List[UnifiedProject]:
        """List all Asana projects in workspace"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/workspaces/{self.workspace_gid}/projects",
                headers=self._headers(),
                params={"opt_fields": "name,notes,due_date,start_on,current_status,permalink_url"},
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            projects = data.get("data", [])

            return [
                UnifiedProject(
                    external_id=p.get("gid"),
                    name=p.get("name", ""),
                    description=p.get("notes", ""),
                    status=self._map_project_status(p.get("current_status")),
                    start_date=self._parse_date(p.get("start_on")),
                    end_date=self._parse_date(p.get("due_date")),
                    url=p.get("permalink_url"),
                    raw_data=p,
                )
                for p in projects
            ]

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific project"""
        gid = external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/projects/{gid}",
                headers=self._headers(),
                params={"opt_fields": "name,notes,due_date,start_on,current_status,permalink_url"},
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            p = response.json().get("data", {})
            return UnifiedProject(
                external_id=p.get("gid"),
                name=p.get("name", ""),
                description=p.get("notes", ""),
                status=self._map_project_status(p.get("current_status")),
                start_date=self._parse_date(p.get("start_on")),
                end_date=self._parse_date(p.get("due_date")),
                url=p.get("permalink_url"),
                raw_data=p,
            )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new project in Asana"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/projects",
                headers=self._headers(),
                json={
                    "data": {
                        "workspace": self.workspace_gid,
                        "name": project.name,
                        "notes": project.description or "",
                        "due_date": project.end_date.isoformat() if project.end_date else None,
                        "start_on": project.start_date.isoformat() if project.start_date else None,
                    }
                },
                timeout=30.0
            )

            data = response.json()
            result = data.get("data", {})
            project.external_id = result.get("gid")
            project.url = result.get("permalink_url")
            return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update an existing project"""
        gid = project.external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{self.api_base}/projects/{gid}",
                headers=self._headers(),
                json={
                    "data": {
                        "name": project.name,
                        "notes": project.description or "",
                    }
                },
                timeout=30.0
            )
            return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all tasks for a project"""
        gid = project_external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/projects/{gid}/tasks",
                headers=self._headers(),
                params={
                    "opt_fields": "name,notes,due_on,assignee.name,completed,memberships.section.name,permalink_url"
                },
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            tasks = data.get("data", [])

            return [
                UnifiedTask(
                    external_id=t.get("gid"),
                    project_external_id=project_external_id,
                    title=t.get("name", ""),
                    description=t.get("notes", ""),
                    status="done" if t.get("completed") else self._map_section_to_status(t),
                    priority="medium",
                    assignee=t.get("assignee", {}).get("name") if t.get("assignee") else None,
                    due_date=self._parse_date(t.get("due_on")),
                    url=t.get("permalink_url"),
                    raw_data=t,
                )
                for t in tasks
            ]

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific task"""
        gid = task_external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/tasks/{gid}",
                headers=self._headers(),
                params={"opt_fields": "name,notes,due_on,assignee.name,completed,projects,permalink_url"},
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            t = response.json().get("data", {})
            projects = t.get("projects", [])
            project_id = projects[0].get("gid") if projects else ""

            return UnifiedTask(
                external_id=t.get("gid"),
                project_external_id=project_id,
                title=t.get("name", ""),
                description=t.get("notes", ""),
                status="done" if t.get("completed") else "todo",
                assignee=t.get("assignee", {}).get("name") if t.get("assignee") else None,
                due_date=self._parse_date(t.get("due_on")),
                url=t.get("permalink_url"),
                raw_data=t,
            )

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new task"""
        gid = task.project_external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/tasks",
                headers=self._headers(),
                json={
                    "data": {
                        "name": task.title,
                        "notes": task.description or "",
                        "projects": [gid],
                        "due_on": task.due_date.isoformat() if task.due_date else None,
                    }
                },
                timeout=30.0
            )

            result = response.json().get("data", {})
            task.external_id = result.get("gid")
            task.url = result.get("permalink_url")
            return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing task"""
        gid = task.external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            data = {
                "name": task.title,
                "notes": task.description or "",
            }
            if task.due_date:
                data["due_on"] = task.due_date.isoformat()
            if task.status == "done":
                data["completed"] = True

            await client.put(
                f"{self.api_base}/tasks/{gid}",
                headers=self._headers(),
                json={"data": data},
                timeout=30.0
            )
            return task

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark a task as complete"""
        gid = task_external_id.replace("asana:", "")
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.api_base}/tasks/{gid}",
                headers=self._headers(),
                json={"data": {"completed": True}},
                timeout=10.0
            )
            return response.status_code == 200

    # Helper methods

    def _map_section_to_status(self, task: dict) -> str:
        """Map Asana section name to unified status"""
        memberships = task.get("memberships", [])
        if memberships:
            section = memberships[0].get("section", {}).get("name", "").lower()
            return self.STATUS_TO_UNIFIED.get(section, "todo")
        return "todo"

    def _map_project_status(self, current_status: Optional[dict]) -> str:
        if not current_status:
            return "active"
        status_text = current_status.get("text", "").lower()
        if "complete" in status_text:
            return "completed"
        elif "on hold" in status_text:
            return "on_hold"
        return "active"

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
