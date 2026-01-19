"""
MAGNUS OpenProject Adapter

Connects to OpenProject for project management.
API Docs: https://www.openproject.org/docs/api/
"""

import httpx
import base64
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class OpenProjectAdapter(PMAdapter):
    """
    Adapter for OpenProject PM tool.
    Uses API key authentication (Basic auth with apikey:x).
    """

    tool_name = "openproject"

    # Status mappings
    STATUS_TO_UNIFIED = {
        "new": "todo",
        "to be scheduled": "todo",
        "scheduled": "todo",
        "in progress": "in_progress",
        "in development": "in_progress",
        "developed": "review",
        "in testing": "review",
        "tested": "review",
        "on hold": "blocked",
        "rejected": "cancelled",
        "closed": "done",
        "done": "done",
    }

    STATUS_FROM_UNIFIED = {
        "todo": "New",
        "in_progress": "In progress",
        "blocked": "On hold",
        "review": "In testing",
        "done": "Closed",
        "cancelled": "Rejected",
    }

    PRIORITY_TO_UNIFIED = {
        "immediate": "critical",
        "high": "high",
        "normal": "medium",
        "low": "low",
    }

    PRIORITY_FROM_UNIFIED = {
        "critical": "Immediate",
        "high": "High",
        "medium": "Normal",
        "low": "Low",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.credentials.get("api_key", "")
        # Default to local OpenProject instance
        self.api_base = config.get("instance_url", "http://openproject:80") + "/api/v3"

    def _headers(self) -> Dict[str, str]:
        # OpenProject uses Basic auth with "apikey" as username
        auth = base64.b64encode(f"apikey:{self.api_key}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test connection to OpenProject"""
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
        """List all OpenProject projects"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/projects",
                headers=self._headers(),
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            projects = data.get("_embedded", {}).get("elements", [])

            return [
                UnifiedProject(
                    external_id=str(p.get("id")),
                    name=p.get("name", ""),
                    description=p.get("description", {}).get("raw", "") if isinstance(p.get("description"), dict) else (p.get("description") or ""),
                    status=self._map_project_status(p.get("status")),
                    start_date=self._parse_date(p.get("startDate")),
                    end_date=self._parse_date(p.get("dueDate")),
                    url=p.get("_links", {}).get("self", {}).get("href"),
                    raw_data=p,
                )
                for p in projects
            ]

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific project"""
        project_id = external_id.replace("openproject:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/projects/{project_id}",
                headers=self._headers(),
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            p = response.json()
            return UnifiedProject(
                external_id=str(p.get("id")),
                name=p.get("name", ""),
                description=p.get("description", {}).get("raw", "") if isinstance(p.get("description"), dict) else (p.get("description") or ""),
                status=self._map_project_status(p.get("status")),
                start_date=self._parse_date(p.get("startDate")),
                end_date=self._parse_date(p.get("dueDate")),
                url=p.get("_links", {}).get("self", {}).get("href"),
                raw_data=p,
            )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new project"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/projects",
                headers=self._headers(),
                json={
                    "name": project.name,
                    "description": {"raw": project.description or ""},
                    "public": False,
                },
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                data = response.json()
                project.external_id = str(data.get("id"))
                project.url = data.get("_links", {}).get("self", {}).get("href")

            return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update an existing project"""
        project_id = project.external_id.replace("openproject:", "")
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{self.api_base}/projects/{project_id}",
                headers=self._headers(),
                json={
                    "name": project.name,
                    "description": {"raw": project.description or ""},
                },
                timeout=30.0
            )
            return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all work packages (tasks) for a project"""
        project_id = project_external_id.replace("openproject:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/projects/{project_id}/work_packages",
                headers=self._headers(),
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            work_packages = data.get("_embedded", {}).get("elements", [])

            return [
                UnifiedTask(
                    external_id=str(wp.get("id")),
                    project_external_id=project_external_id,
                    title=wp.get("subject", ""),
                    description=wp.get("description", {}).get("raw", "") if isinstance(wp.get("description"), dict) else (wp.get("description") or ""),
                    status=self._map_status_to_unified(wp),
                    priority=self._map_priority_to_unified(wp),
                    assignee=self._extract_assignee(wp),
                    due_date=self._parse_date(wp.get("dueDate")),
                    url=wp.get("_links", {}).get("self", {}).get("href"),
                    raw_data=wp,
                )
                for wp in work_packages
            ]

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific work package"""
        wp_id = task_external_id.replace("openproject:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/work_packages/{wp_id}",
                headers=self._headers(),
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            wp = response.json()
            project_link = wp.get("_links", {}).get("project", {}).get("href", "")
            project_id = project_link.split("/")[-1] if project_link else ""

            return UnifiedTask(
                external_id=str(wp.get("id")),
                project_external_id=f"openproject:{project_id}",
                title=wp.get("subject", ""),
                description=wp.get("description", {}).get("raw", "") if isinstance(wp.get("description"), dict) else (wp.get("description") or ""),
                status=self._map_status_to_unified(wp),
                priority=self._map_priority_to_unified(wp),
                assignee=self._extract_assignee(wp),
                due_date=self._parse_date(wp.get("dueDate")),
                url=wp.get("_links", {}).get("self", {}).get("href"),
                raw_data=wp,
            )

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new work package"""
        project_id = task.project_external_id.replace("openproject:", "")

        payload = {
            "subject": task.title,
            "description": {"raw": task.description or ""},
        }

        if task.due_date:
            payload["dueDate"] = task.due_date.isoformat()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/projects/{project_id}/work_packages",
                headers=self._headers(),
                json=payload,
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                result = response.json()
                task.external_id = str(result.get("id"))
                task.url = result.get("_links", {}).get("self", {}).get("href")

            return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing work package"""
        wp_id = task.external_id.replace("openproject:", "")

        # Get current work package to get lock version
        async with httpx.AsyncClient() as client:
            get_response = await client.get(
                f"{self.api_base}/work_packages/{wp_id}",
                headers=self._headers(),
                timeout=10.0
            )

            if get_response.status_code != 200:
                return task

            current = get_response.json()
            lock_version = current.get("lockVersion", 0)

            payload = {
                "subject": task.title,
                "lockVersion": lock_version,
            }

            if task.description:
                payload["description"] = {"raw": task.description}

            if task.due_date:
                payload["dueDate"] = task.due_date.isoformat()

            await client.patch(
                f"{self.api_base}/work_packages/{wp_id}",
                headers=self._headers(),
                json=payload,
                timeout=30.0
            )

            return task

    async def delete_task(self, task_external_id: str) -> bool:
        """Delete a work package"""
        wp_id = task_external_id.replace("openproject:", "")
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.api_base}/work_packages/{wp_id}",
                headers=self._headers(),
                timeout=10.0
            )
            return response.status_code in [200, 204]

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark a work package as complete by transitioning to Closed status"""
        wp_id = task_external_id.replace("openproject:", "")

        async with httpx.AsyncClient() as client:
            # Get current work package for lock version
            get_response = await client.get(
                f"{self.api_base}/work_packages/{wp_id}",
                headers=self._headers(),
                timeout=10.0
            )

            if get_response.status_code != 200:
                return False

            current = get_response.json()
            lock_version = current.get("lockVersion", 0)

            # Get available statuses to find "Closed"
            statuses_response = await client.get(
                f"{self.api_base}/statuses",
                headers=self._headers(),
                timeout=10.0
            )

            if statuses_response.status_code != 200:
                return False

            statuses = statuses_response.json().get("_embedded", {}).get("elements", [])
            closed_status = None
            for s in statuses:
                if s.get("name", "").lower() in ["closed", "done", "resolved"]:
                    closed_status = s
                    break

            if not closed_status:
                return False

            # Update work package status
            response = await client.patch(
                f"{self.api_base}/work_packages/{wp_id}",
                headers=self._headers(),
                json={
                    "lockVersion": lock_version,
                    "_links": {
                        "status": {"href": closed_status.get("_links", {}).get("self", {}).get("href")}
                    }
                },
                timeout=10.0
            )
            return response.status_code == 200

    async def list_statuses(self) -> List[Dict[str, Any]]:
        """Get all available statuses"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/statuses",
                headers=self._headers(),
                timeout=10.0
            )
            if response.status_code != 200:
                return []
            return response.json().get("_embedded", {}).get("elements", [])

    async def list_types(self) -> List[Dict[str, Any]]:
        """Get all available work package types"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/types",
                headers=self._headers(),
                timeout=10.0
            )
            if response.status_code != 200:
                return []
            return response.json().get("_embedded", {}).get("elements", [])

    # Helper methods

    def _map_project_status(self, status: Optional[str]) -> str:
        if not status:
            return "active"
        status_lower = status.lower()
        if status_lower in ["closed", "archived"]:
            return "completed"
        elif status_lower in ["on hold"]:
            return "on_hold"
        return "active"

    def _map_status_to_unified(self, wp: dict) -> str:
        status_link = wp.get("_links", {}).get("status", {})
        status_name = status_link.get("title", "").lower() if status_link else ""
        return self.STATUS_TO_UNIFIED.get(status_name, "todo")

    def _map_priority_to_unified(self, wp: dict) -> str:
        priority_link = wp.get("_links", {}).get("priority", {})
        priority_name = priority_link.get("title", "").lower() if priority_link else ""
        return self.PRIORITY_TO_UNIFIED.get(priority_name, "medium")

    def _extract_assignee(self, wp: dict) -> Optional[str]:
        assignee_link = wp.get("_links", {}).get("assignee", {})
        if assignee_link and assignee_link.get("title"):
            return assignee_link.get("title")
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
