"""
MAGNUS Jira Adapter

Connects to Jira Cloud for project management.
API Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

import httpx
import base64
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class JiraAdapter(PMAdapter):
    """
    Adapter for Jira Cloud PM tool.
    Uses email + API token authentication.
    """

    tool_name = "jira"

    # Status mappings
    STATUS_TO_UNIFIED = {
        "to do": "todo",
        "backlog": "todo",
        "open": "todo",
        "in progress": "in_progress",
        "in review": "review",
        "review": "review",
        "blocked": "blocked",
        "done": "done",
        "closed": "done",
        "resolved": "done",
    }

    STATUS_FROM_UNIFIED = {
        "todo": "To Do",
        "in_progress": "In Progress",
        "blocked": "Blocked",
        "review": "In Review",
        "done": "Done",
        "cancelled": "Done",
    }

    PRIORITY_TO_UNIFIED = {
        "highest": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "lowest": "low",
    }

    PRIORITY_FROM_UNIFIED = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.email = self.credentials.get("email", "")
        self.api_token = self.credentials.get("api_token", "")
        self.domain = config.get("domain", "")  # e.g., "yourcompany.atlassian.net"
        self.api_base = f"https://{self.domain}/rest/api/3"

    def _headers(self) -> Dict[str, str]:
        auth = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test connection to Jira"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/myself",
                    headers=self._headers(),
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_projects(self) -> List[UnifiedProject]:
        """List all Jira projects"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/project/search",
                headers=self._headers(),
                params={"expand": "description"},
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            projects = data.get("values", [])

            return [
                UnifiedProject(
                    external_id=p.get("key"),
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    status="active",
                    url=f"https://{self.domain}/browse/{p.get('key')}",
                    raw_data=p,
                )
                for p in projects
            ]

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific project"""
        key = external_id.replace("jira:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/project/{key}",
                headers=self._headers(),
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            p = response.json()
            return UnifiedProject(
                external_id=p.get("key"),
                name=p.get("name", ""),
                description=p.get("description", ""),
                status="active",
                url=f"https://{self.domain}/browse/{p.get('key')}",
                raw_data=p,
            )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new project in Jira"""
        # Note: Project creation in Jira requires admin permissions
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/project",
                headers=self._headers(),
                json={
                    "key": project.name[:10].upper().replace(" ", ""),
                    "name": project.name,
                    "description": project.description or "",
                    "projectTypeKey": "software",
                },
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                data = response.json()
                project.external_id = data.get("key")
                project.url = f"https://{self.domain}/browse/{data.get('key')}"

            return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update an existing project"""
        key = project.external_id.replace("jira:", "")
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{self.api_base}/project/{key}",
                headers=self._headers(),
                json={
                    "name": project.name,
                    "description": project.description or "",
                },
                timeout=30.0
            )
            return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all tasks (issues) for a project"""
        key = project_external_id.replace("jira:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/search",
                headers=self._headers(),
                params={
                    "jql": f"project = {key}",
                    "fields": "summary,description,status,assignee,duedate,priority",
                    "maxResults": 100,
                },
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            data = response.json()
            issues = data.get("issues", [])

            return [
                UnifiedTask(
                    external_id=issue.get("key"),
                    project_external_id=project_external_id,
                    title=issue.get("fields", {}).get("summary", ""),
                    description=self._extract_description(issue.get("fields", {}).get("description")),
                    status=self.map_status_to_unified(
                        issue.get("fields", {}).get("status", {}).get("name", "")
                    ),
                    priority=self.map_priority_to_unified(
                        issue.get("fields", {}).get("priority", {}).get("name", "")
                    ),
                    assignee=issue.get("fields", {}).get("assignee", {}).get("displayName")
                             if issue.get("fields", {}).get("assignee") else None,
                    due_date=self._parse_date(issue.get("fields", {}).get("duedate")),
                    url=f"https://{self.domain}/browse/{issue.get('key')}",
                    raw_data=issue,
                )
                for issue in issues
            ]

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific task"""
        key = task_external_id.replace("jira:", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/issue/{key}",
                headers=self._headers(),
                params={"fields": "summary,description,status,assignee,duedate,priority,project"},
                timeout=10.0
            )

            if response.status_code != 200:
                return None

            issue = response.json()
            fields = issue.get("fields", {})

            return UnifiedTask(
                external_id=issue.get("key"),
                project_external_id=f"jira:{fields.get('project', {}).get('key', '')}",
                title=fields.get("summary", ""),
                description=self._extract_description(fields.get("description")),
                status=self.map_status_to_unified(fields.get("status", {}).get("name", "")),
                priority=self.map_priority_to_unified(fields.get("priority", {}).get("name", "")),
                assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                due_date=self._parse_date(fields.get("duedate")),
                url=f"https://{self.domain}/browse/{issue.get('key')}",
                raw_data=issue,
            )

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new task (issue)"""
        key = task.project_external_id.replace("jira:", "")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/issue",
                headers=self._headers(),
                json={
                    "fields": {
                        "project": {"key": key},
                        "summary": task.title,
                        "description": self._build_description(task.description),
                        "issuetype": {"name": "Task"},
                        "duedate": task.due_date.isoformat() if task.due_date else None,
                    }
                },
                timeout=30.0
            )

            if response.status_code in [200, 201]:
                result = response.json()
                task.external_id = result.get("key")
                task.url = f"https://{self.domain}/browse/{result.get('key')}"

            return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing task"""
        key = task.external_id.replace("jira:", "")
        async with httpx.AsyncClient() as client:
            fields = {"summary": task.title}
            if task.due_date:
                fields["duedate"] = task.due_date.isoformat()
            if task.description:
                fields["description"] = self._build_description(task.description)

            await client.put(
                f"{self.api_base}/issue/{key}",
                headers=self._headers(),
                json={"fields": fields},
                timeout=30.0
            )

            # Handle status transition if needed
            if task.status:
                await self._transition_issue(key, task.status)

            return task

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark a task as complete"""
        key = task_external_id.replace("jira:", "")
        return await self._transition_issue(key, "done")

    async def _transition_issue(self, key: str, target_status: str) -> bool:
        """Transition an issue to a new status"""
        async with httpx.AsyncClient() as client:
            # Get available transitions
            response = await client.get(
                f"{self.api_base}/issue/{key}/transitions",
                headers=self._headers(),
                timeout=10.0
            )

            if response.status_code != 200:
                return False

            transitions = response.json().get("transitions", [])

            # Find matching transition
            target_lower = target_status.lower()
            for t in transitions:
                transition_name = t.get("name", "").lower()
                if target_lower in transition_name or transition_name in target_lower:
                    await client.post(
                        f"{self.api_base}/issue/{key}/transitions",
                        headers=self._headers(),
                        json={"transition": {"id": t["id"]}},
                        timeout=10.0
                    )
                    return True

            return False

    # Helper methods

    def map_status_to_unified(self, external_status: str) -> str:
        if not external_status:
            return "todo"
        return self.STATUS_TO_UNIFIED.get(external_status.lower(), "todo")

    def map_priority_to_unified(self, external_priority: str) -> str:
        if not external_priority:
            return "medium"
        return self.PRIORITY_TO_UNIFIED.get(external_priority.lower(), "medium")

    def _extract_description(self, desc: Any) -> str:
        """Extract text from Jira's ADF (Atlassian Document Format)"""
        if not desc:
            return ""
        if isinstance(desc, str):
            return desc

        # Parse ADF format
        text_parts = []
        for content in desc.get("content", []):
            if content.get("type") == "paragraph":
                for c in content.get("content", []):
                    if c.get("type") == "text":
                        text_parts.append(c.get("text", ""))
        return " ".join(text_parts)

    def _build_description(self, text: Optional[str]) -> dict:
        """Build Jira ADF from plain text"""
        if not text:
            return {
                "type": "doc",
                "version": 1,
                "content": []
            }
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}]
                }
            ]
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
