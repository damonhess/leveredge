"""
MAGNUS Notion Adapter

Connects to Notion for project management via databases.
API Docs: https://developers.notion.com/reference
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class NotionAdapter(PMAdapter):
    """
    Adapter for Notion PM tool.
    Uses integration token authentication.
    """

    tool_name = "notion"
    api_base = "https://api.notion.com/v1"
    api_version = "2022-06-28"

    # Status mappings
    STATUS_TO_UNIFIED = {
        "not started": "todo",
        "to do": "todo",
        "in progress": "in_progress",
        "in review": "review",
        "blocked": "blocked",
        "done": "done",
        "complete": "done",
        "completed": "done",
    }

    STATUS_FROM_UNIFIED = {
        "todo": "Not started",
        "in_progress": "In progress",
        "blocked": "Blocked",
        "review": "In review",
        "done": "Done",
        "cancelled": "Done",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.credentials.get("api_key") or self.credentials.get("access_token", "")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.api_version,
        }

    async def test_connection(self) -> bool:
        """Test connection to Notion"""
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
        """List all Notion databases (as projects)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/search",
                headers=self._headers(),
                json={"filter": {"property": "object", "value": "database"}},
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            databases = data.get("results", [])

            projects = []
            for db in databases:
                title = self._extract_title(db.get("title", []))
                projects.append(UnifiedProject(
                    external_id=db.get("id"),
                    name=title or "Untitled",
                    description="",
                    status="active",
                    url=db.get("url"),
                    raw_data=db,
                ))

            return projects

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific database"""
        db_id = external_id.replace("notion:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/databases/{db_id}",
                headers=self._headers(),
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            db = response.json()
            title = self._extract_title(db.get("title", []))

            return UnifiedProject(
                external_id=db.get("id"),
                name=title or "Untitled",
                description="",
                status="active",
                url=db.get("url"),
                raw_data=db,
            )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new database in a parent page"""
        # Note: Requires a parent page to create a database
        parent_page_id = self.config.get("parent_page_id")
        if not parent_page_id:
            raise ValueError("parent_page_id required to create Notion database")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/databases",
                headers=self._headers(),
                json={
                    "parent": {"type": "page_id", "page_id": parent_page_id},
                    "title": [{"type": "text", "text": {"content": project.name}}],
                    "properties": {
                        "Name": {"title": {}},
                        "Status": {
                            "status": {
                                "options": [
                                    {"name": "Not started", "color": "default"},
                                    {"name": "In progress", "color": "blue"},
                                    {"name": "Done", "color": "green"},
                                ]
                            }
                        },
                        "Due Date": {"date": {}},
                    }
                },
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                data = response.json()
                project.external_id = data.get("id")
                project.url = data.get("url")

            return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update database title"""
        db_id = project.external_id.replace("notion:", "")
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{self.api_base}/databases/{db_id}",
                headers=self._headers(),
                json={
                    "title": [{"type": "text", "text": {"content": project.name}}]
                },
                timeout=30.0
            )
            return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """Query database for pages (tasks)"""
        db_id = project_external_id.replace("notion:", "")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/databases/{db_id}/query",
                headers=self._headers(),
                json={},
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            pages = data.get("results", [])

            tasks = []
            for page in pages:
                props = page.get("properties", {})
                title = self._extract_page_title(props)

                task = UnifiedTask(
                    external_id=page.get("id"),
                    project_external_id=project_external_id,
                    title=title or "Untitled",
                    status=self._extract_status(props),
                    priority="medium",
                    assignee=self._extract_person(props),
                    due_date=self._extract_date(props),
                    url=page.get("url"),
                    raw_data=page,
                )
                tasks.append(task)

            return tasks

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific page"""
        page_id = task_external_id.replace("notion:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/pages/{page_id}",
                headers=self._headers(),
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            page = response.json()
            props = page.get("properties", {})
            title = self._extract_page_title(props)

            # Get parent database ID
            parent = page.get("parent", {})
            parent_id = parent.get("database_id", "")

            return UnifiedTask(
                external_id=page.get("id"),
                project_external_id=f"notion:{parent_id}",
                title=title or "Untitled",
                status=self._extract_status(props),
                priority="medium",
                assignee=self._extract_person(props),
                due_date=self._extract_date(props),
                url=page.get("url"),
                raw_data=page,
            )

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new page in database"""
        db_id = task.project_external_id.replace("notion:", "")

        properties = {
            "Name": {
                "title": [{"text": {"content": task.title}}]
            }
        }

        if task.due_date:
            properties["Due Date"] = {
                "date": {"start": task.due_date.isoformat()}
            }

        if task.status:
            status_name = self.STATUS_FROM_UNIFIED.get(task.status, "Not started")
            properties["Status"] = {
                "status": {"name": status_name}
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/pages",
                headers=self._headers(),
                json={
                    "parent": {"database_id": db_id},
                    "properties": properties
                },
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                result = response.json()
                task.external_id = result.get("id")
                task.url = result.get("url")

            return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing page"""
        page_id = task.external_id.replace("notion:", "")

        properties = {}
        if task.title:
            properties["Name"] = {
                "title": [{"text": {"content": task.title}}]
            }
        if task.due_date:
            properties["Due Date"] = {
                "date": {"start": task.due_date.isoformat()}
            }
        if task.status:
            status_name = self.STATUS_FROM_UNIFIED.get(task.status, "Not started")
            properties["Status"] = {
                "status": {"name": status_name}
            }

        if properties:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{self.api_base}/pages/{page_id}",
                    headers=self._headers(),
                    json={"properties": properties},
                    timeout=30.0
                )

        return task

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark a page as complete"""
        page_id = task_external_id.replace("notion:", "")

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.api_base}/pages/{page_id}",
                headers=self._headers(),
                json={
                    "properties": {
                        "Status": {"status": {"name": "Done"}}
                    }
                },
                timeout=10.0
            )
            return response.status_code == 200

    # Helper methods

    def _extract_title(self, title_array: List[dict]) -> str:
        """Extract text from Notion title array"""
        parts = []
        for t in title_array:
            if t.get("type") == "text":
                parts.append(t.get("text", {}).get("content", ""))
            elif "plain_text" in t:
                parts.append(t.get("plain_text", ""))
        return "".join(parts)

    def _extract_page_title(self, props: dict) -> str:
        """Extract title from page properties"""
        for prop in props.values():
            if prop.get("type") == "title":
                return self._extract_title(prop.get("title", []))
        return ""

    def _extract_status(self, props: dict) -> str:
        """Extract status from page properties"""
        for prop in props.values():
            if prop.get("type") == "status":
                status_obj = prop.get("status")
                if status_obj:
                    status_name = status_obj.get("name", "").lower()
                    return self.STATUS_TO_UNIFIED.get(status_name, "todo")
        return "todo"

    def _extract_person(self, props: dict) -> Optional[str]:
        """Extract assignee from page properties"""
        for prop in props.values():
            if prop.get("type") == "people":
                people = prop.get("people", [])
                if people:
                    return people[0].get("name")
        return None

    def _extract_date(self, props: dict) -> Optional[date]:
        """Extract due date from page properties"""
        for prop_name, prop in props.items():
            if prop.get("type") == "date":
                date_obj = prop.get("date")
                if date_obj and date_obj.get("start"):
                    return self._parse_date(date_obj.get("start"))
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
