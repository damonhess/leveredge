"""
MAGNUS Leantime Adapter

Connects to Leantime for ADHD-friendly project management.
Leantime is our internal daily driver.
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class LeantimeAdapter(PMAdapter):
    """
    Adapter for Leantime PM tool.

    Leantime API: https://docs.leantime.io/api/
    """

    tool_name = "leantime"

    # Status mappings
    STATUS_TO_UNIFIED = {
        "0": "todo",        # New
        "1": "in_progress", # In Progress
        "2": "blocked",     # Blocked
        "3": "review",      # Review
        "4": "done",        # Done
    }

    STATUS_FROM_UNIFIED = {
        "todo": "0",
        "in_progress": "1",
        "blocked": "2",
        "review": "3",
        "done": "4",
        "cancelled": "4",  # Map to done
    }

    PRIORITY_TO_UNIFIED = {
        "1": "critical",
        "2": "high",
        "3": "medium",
        "4": "low",
    }

    PRIORITY_FROM_UNIFIED = {
        "critical": "1",
        "high": "2",
        "medium": "3",
        "low": "4",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.credentials.get("api_key", "")
        self.base_url = self.instance_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test connection to Leantime"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/jsonrpc",
                    headers=self._headers(),
                    timeout=10.0
                )
                return response.status_code in [200, 401, 405]
        except Exception:
            return False

    async def list_projects(self) -> List[UnifiedProject]:
        """List all Leantime projects"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.projects.getAll",
                    "id": "1",
                }
            )

            if response.status_code != 200:
                return []

            data = response.json()
            projects = data.get("result", [])

            return [
                UnifiedProject(
                    external_id=str(p.get("id")),
                    name=p.get("name", ""),
                    description=p.get("details", ""),
                    status=self._map_project_status(p.get("state", "")),
                    start_date=self._parse_date(p.get("start")),
                    end_date=self._parse_date(p.get("end")),
                    owner=p.get("clientName", ""),
                    url=f"{self.base_url}/projects/showProject/{p.get('id')}",
                    raw_data=p,
                )
                for p in projects
            ]

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific project"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.projects.getProject",
                    "params": {"id": int(external_id)},
                    "id": "1",
                }
            )

            if response.status_code != 200:
                return None

            data = response.json()
            p = data.get("result")
            if not p:
                return None

            return UnifiedProject(
                external_id=str(p.get("id")),
                name=p.get("name", ""),
                description=p.get("details", ""),
                status=self._map_project_status(p.get("state", "")),
                start_date=self._parse_date(p.get("start")),
                end_date=self._parse_date(p.get("end")),
                owner=p.get("clientName", ""),
                url=f"{self.base_url}/projects/showProject/{p.get('id')}",
                raw_data=p,
            )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new project in Leantime"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.projects.addProject",
                    "params": {
                        "name": project.name,
                        "details": project.description or "",
                        "start": project.start_date.isoformat() if project.start_date else None,
                        "end": project.end_date.isoformat() if project.end_date else None,
                    },
                    "id": "1",
                }
            )

            data = response.json()
            new_id = data.get("result")

            project.external_id = str(new_id)
            project.url = f"{self.base_url}/projects/showProject/{new_id}"
            return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update an existing project"""
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.projects.patchProject",
                    "params": {
                        "id": int(project.external_id),
                        "name": project.name,
                        "details": project.description or "",
                    },
                    "id": "1",
                }
            )
            return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all tasks for a project"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.tickets.getAll",
                    "params": {"projectId": int(project_external_id)},
                    "id": "1",
                }
            )

            if response.status_code != 200:
                return []

            data = response.json()
            tasks = data.get("result", [])

            return [
                UnifiedTask(
                    external_id=str(t.get("id")),
                    project_external_id=project_external_id,
                    title=t.get("headline", ""),
                    description=t.get("description", ""),
                    status=self.map_status_to_unified(str(t.get("status", "0"))),
                    priority=self.map_priority_to_unified(str(t.get("priority", "3"))),
                    assignee=t.get("editorFirstname", ""),
                    due_date=self._parse_date(t.get("dateToFinish")),
                    estimated_hours=self._parse_float(t.get("planHours")),
                    parent_id=str(t.get("dependingTicketId")) if t.get("dependingTicketId") else None,
                    url=f"{self.base_url}/tickets/showTicket/{t.get('id')}",
                    raw_data=t,
                )
                for t in tasks
            ]

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific task"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.tickets.getTicket",
                    "params": {"id": int(task_external_id)},
                    "id": "1",
                }
            )

            if response.status_code != 200:
                return None

            data = response.json()
            t = data.get("result")
            if not t:
                return None

            return UnifiedTask(
                external_id=str(t.get("id")),
                project_external_id=str(t.get("projectId")),
                title=t.get("headline", ""),
                description=t.get("description", ""),
                status=self.map_status_to_unified(str(t.get("status", "0"))),
                priority=self.map_priority_to_unified(str(t.get("priority", "3"))),
                assignee=t.get("editorFirstname", ""),
                due_date=self._parse_date(t.get("dateToFinish")),
                estimated_hours=self._parse_float(t.get("planHours")),
                url=f"{self.base_url}/tickets/showTicket/{t.get('id')}",
                raw_data=t,
            )

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new task"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.tickets.addTicket",
                    "params": {
                        "headline": task.title,
                        "description": task.description or "",
                        "projectId": int(task.project_external_id),
                        "status": self.map_status_from_unified(task.status),
                        "priority": self.map_priority_from_unified(task.priority),
                        "dateToFinish": task.due_date.isoformat() if task.due_date else None,
                        "planHours": task.estimated_hours,
                    },
                    "id": "1",
                }
            )

            data = response.json()
            new_id = data.get("result")

            task.external_id = str(new_id)
            task.url = f"{self.base_url}/tickets/showTicket/{new_id}"
            return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing task"""
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.tickets.patchTicket",
                    "params": {
                        "id": int(task.external_id),
                        "headline": task.title,
                        "description": task.description or "",
                        "status": self.map_status_from_unified(task.status),
                        "priority": self.map_priority_from_unified(task.priority),
                    },
                    "id": "1",
                }
            )
            return task

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark a task as complete"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/jsonrpc",
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.tickets.patchTicket",
                    "params": {
                        "id": int(task_external_id),
                        "status": "4",  # Done
                    },
                    "id": "1",
                }
            )
            return response.status_code == 200

    # Helper methods

    def map_status_to_unified(self, external_status: str) -> str:
        return self.STATUS_TO_UNIFIED.get(external_status, "todo")

    def map_status_from_unified(self, unified_status: str) -> str:
        return self.STATUS_FROM_UNIFIED.get(unified_status, "0")

    def map_priority_to_unified(self, external_priority: str) -> str:
        return self.PRIORITY_TO_UNIFIED.get(external_priority, "medium")

    def map_priority_from_unified(self, unified_priority: str) -> str:
        return self.PRIORITY_FROM_UNIFIED.get(unified_priority, "3")

    def _map_project_status(self, state: str) -> str:
        mapping = {
            "0": "planning",
            "1": "active",
            "2": "completed",
            "-1": "cancelled",
        }
        return mapping.get(state, "planning")

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None

    def _parse_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
