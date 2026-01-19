"""
MAGNUS Linear Adapter

Connects to Linear for project management.
API Docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class LinearAdapter(PMAdapter):
    """
    Adapter for Linear PM tool.
    Uses GraphQL API with API key authentication.
    """

    tool_name = "linear"
    api_base = "https://api.linear.app/graphql"

    # Status mappings
    STATUS_TO_UNIFIED = {
        "backlog": "todo",
        "triage": "todo",
        "todo": "todo",
        "in progress": "in_progress",
        "in review": "review",
        "blocked": "blocked",
        "done": "done",
        "completed": "done",
        "canceled": "cancelled",
        "cancelled": "cancelled",
    }

    STATUS_FROM_UNIFIED = {
        "todo": "Todo",
        "in_progress": "In Progress",
        "blocked": "Blocked",
        "review": "In Review",
        "done": "Done",
        "cancelled": "Canceled",
    }

    PRIORITY_TO_UNIFIED = {
        0: "low",      # No priority
        1: "critical", # Urgent
        2: "high",     # High
        3: "medium",   # Medium
        4: "low",      # Low
    }

    PRIORITY_FROM_UNIFIED = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.credentials.get("api_key", "")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def _graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query"""
        async with httpx.AsyncClient() as client:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables

            response = await client.post(
                self.api_base,
                headers=self._headers(),
                json=payload,
                timeout=30.0
            )
            return response.json()

    async def test_connection(self) -> bool:
        """Test connection to Linear"""
        try:
            result = await self._graphql("query { viewer { id } }")
            return "data" in result and "viewer" in result.get("data", {})
        except Exception:
            return False

    async def list_projects(self) -> List[UnifiedProject]:
        """List all Linear projects"""
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
                    url
                }
            }
        }
        """

        result = await self._graphql(query)
        projects = result.get("data", {}).get("projects", {}).get("nodes", [])

        return [
            UnifiedProject(
                external_id=p.get("id"),
                name=p.get("name", ""),
                description=p.get("description", ""),
                status=self._map_project_state(p.get("state")),
                start_date=self._parse_date(p.get("startDate")),
                end_date=self._parse_date(p.get("targetDate")),
                url=p.get("url"),
                raw_data=p,
            )
            for p in projects
        ]

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific project"""
        project_id = external_id.replace("linear:", "")
        query = """
        query($id: String!) {
            project(id: $id) {
                id
                name
                description
                state
                startDate
                targetDate
                url
            }
        }
        """

        result = await self._graphql(query, {"id": project_id})
        p = result.get("data", {}).get("project")

        if not p:
            return None

        return UnifiedProject(
            external_id=p.get("id"),
            name=p.get("name", ""),
            description=p.get("description", ""),
            status=self._map_project_state(p.get("state")),
            start_date=self._parse_date(p.get("startDate")),
            end_date=self._parse_date(p.get("targetDate")),
            url=p.get("url"),
            raw_data=p,
        )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new project"""
        # Need team ID to create a project
        team_id = self.config.get("team_id")
        if not team_id:
            # Try to get first team
            teams_result = await self._graphql("query { teams { nodes { id } } }")
            teams = teams_result.get("data", {}).get("teams", {}).get("nodes", [])
            if teams:
                team_id = teams[0].get("id")
            else:
                raise ValueError("team_id required to create Linear project")

        mutation = """
        mutation CreateProject($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                success
                project {
                    id
                    url
                }
            }
        }
        """

        result = await self._graphql(mutation, {
            "input": {
                "name": project.name,
                "description": project.description or "",
                "teamIds": [team_id],
            }
        })

        project_data = result.get("data", {}).get("projectCreate", {}).get("project", {})
        project.external_id = project_data.get("id", "")
        project.url = project_data.get("url")
        return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update an existing project"""
        project_id = project.external_id.replace("linear:", "")

        mutation = """
        mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
            projectUpdate(id: $id, input: $input) {
                success
            }
        }
        """

        await self._graphql(mutation, {
            "id": project_id,
            "input": {
                "name": project.name,
                "description": project.description or "",
            }
        })

        return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all issues for a project"""
        project_id = project_external_id.replace("linear:", "")

        query = """
        query($projectId: ID!) {
            issues(filter: { project: { id: { eq: $projectId } } }) {
                nodes {
                    id
                    title
                    description
                    state {
                        name
                        type
                    }
                    priority
                    assignee {
                        name
                    }
                    dueDate
                    url
                }
            }
        }
        """

        result = await self._graphql(query, {"projectId": project_id})
        issues = result.get("data", {}).get("issues", {}).get("nodes", [])

        return [
            UnifiedTask(
                external_id=i.get("id"),
                project_external_id=project_external_id,
                title=i.get("title", ""),
                description=i.get("description", ""),
                status=self._map_state_to_unified(i.get("state")),
                priority=self.PRIORITY_TO_UNIFIED.get(i.get("priority", 0), "medium"),
                assignee=i.get("assignee", {}).get("name") if i.get("assignee") else None,
                due_date=self._parse_date(i.get("dueDate")),
                url=i.get("url"),
                raw_data=i,
            )
            for i in issues
        ]

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific issue"""
        issue_id = task_external_id.replace("linear:", "")

        query = """
        query($id: String!) {
            issue(id: $id) {
                id
                title
                description
                state {
                    name
                    type
                }
                priority
                assignee {
                    name
                }
                dueDate
                url
                project {
                    id
                }
            }
        }
        """

        result = await self._graphql(query, {"id": issue_id})
        i = result.get("data", {}).get("issue")

        if not i:
            return None

        project_id = i.get("project", {}).get("id", "") if i.get("project") else ""

        return UnifiedTask(
            external_id=i.get("id"),
            project_external_id=f"linear:{project_id}",
            title=i.get("title", ""),
            description=i.get("description", ""),
            status=self._map_state_to_unified(i.get("state")),
            priority=self.PRIORITY_TO_UNIFIED.get(i.get("priority", 0), "medium"),
            assignee=i.get("assignee", {}).get("name") if i.get("assignee") else None,
            due_date=self._parse_date(i.get("dueDate")),
            url=i.get("url"),
            raw_data=i,
        )

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new issue"""
        # Need team ID to create an issue
        team_id = self.config.get("team_id")
        if not team_id:
            teams_result = await self._graphql("query { teams { nodes { id } } }")
            teams = teams_result.get("data", {}).get("teams", {}).get("nodes", [])
            if teams:
                team_id = teams[0].get("id")
            else:
                raise ValueError("team_id required to create Linear issue")

        project_id = task.project_external_id.replace("linear:", "") if task.project_external_id else None

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    url
                }
            }
        }
        """

        input_data = {
            "teamId": team_id,
            "title": task.title,
            "description": task.description or "",
        }

        if project_id:
            input_data["projectId"] = project_id

        if task.due_date:
            input_data["dueDate"] = task.due_date.isoformat()

        if task.priority:
            input_data["priority"] = self.PRIORITY_FROM_UNIFIED.get(task.priority, 3)

        result = await self._graphql(mutation, {"input": input_data})

        issue_data = result.get("data", {}).get("issueCreate", {}).get("issue", {})
        task.external_id = issue_data.get("id", "")
        task.url = issue_data.get("url")
        return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing issue"""
        issue_id = task.external_id.replace("linear:", "")

        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
            }
        }
        """

        input_data = {
            "title": task.title,
        }

        if task.description:
            input_data["description"] = task.description

        if task.due_date:
            input_data["dueDate"] = task.due_date.isoformat()

        if task.priority:
            input_data["priority"] = self.PRIORITY_FROM_UNIFIED.get(task.priority, 3)

        await self._graphql(mutation, {
            "id": issue_id,
            "input": input_data
        })

        return task

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark an issue as complete by setting state to Done"""
        issue_id = task_external_id.replace("linear:", "")

        # First get the Done state ID for this team
        query = """
        query($id: String!) {
            issue(id: $id) {
                team {
                    states(filter: { type: { eq: "completed" } }) {
                        nodes {
                            id
                            name
                        }
                    }
                }
            }
        }
        """

        result = await self._graphql(query, {"id": issue_id})
        states = result.get("data", {}).get("issue", {}).get("team", {}).get("states", {}).get("nodes", [])

        if not states:
            return False

        done_state_id = states[0].get("id")

        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
            }
        }
        """

        result = await self._graphql(mutation, {
            "id": issue_id,
            "input": {"stateId": done_state_id}
        })

        return result.get("data", {}).get("issueUpdate", {}).get("success", False)

    # Helper methods

    def _map_project_state(self, state: Optional[str]) -> str:
        if not state:
            return "active"
        state_lower = state.lower()
        if state_lower in ["completed", "finished"]:
            return "completed"
        elif state_lower in ["canceled", "cancelled"]:
            return "cancelled"
        elif state_lower in ["paused"]:
            return "on_hold"
        return "active"

    def _map_state_to_unified(self, state: Optional[dict]) -> str:
        if not state:
            return "todo"
        state_type = state.get("type", "").lower()
        state_name = state.get("name", "").lower()

        # Map by type first
        if state_type == "completed":
            return "done"
        elif state_type == "canceled":
            return "cancelled"
        elif state_type == "started":
            return "in_progress"
        elif state_type == "backlog":
            return "todo"
        elif state_type == "unstarted":
            return "todo"

        # Fall back to name mapping
        return self.STATUS_TO_UNIFIED.get(state_name, "todo")

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
