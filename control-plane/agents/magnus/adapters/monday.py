"""
MAGNUS Monday.com Adapter

Connects to Monday.com for project management.
API Docs: https://developer.monday.com/api-reference/docs
"""

import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import date

from .base import PMAdapter, UnifiedProject, UnifiedTask


class MondayAdapter(PMAdapter):
    """
    Adapter for Monday.com PM tool.
    Uses GraphQL API with API key authentication.
    """

    tool_name = "monday"
    api_base = "https://api.monday.com/v2"

    # Status mappings
    STATUS_TO_UNIFIED = {
        "": "todo",
        "working on it": "in_progress",
        "stuck": "blocked",
        "done": "done",
        "complete": "done",
    }

    STATUS_FROM_UNIFIED = {
        "todo": "",
        "in_progress": "Working on it",
        "blocked": "Stuck",
        "review": "Working on it",
        "done": "Done",
        "cancelled": "Done",
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
        """Test connection to Monday.com"""
        try:
            result = await self._graphql("query { me { id } }")
            return "data" in result and "me" in result.get("data", {})
        except Exception:
            return False

    async def list_projects(self) -> List[UnifiedProject]:
        """List all Monday boards (projects)"""
        query = """
        query {
            boards {
                id
                name
                description
                state
                board_folder_id
                workspace_id
            }
        }
        """

        result = await self._graphql(query)
        boards = result.get("data", {}).get("boards", [])

        return [
            UnifiedProject(
                external_id=str(b.get("id")),
                name=b.get("name", ""),
                description=b.get("description", ""),
                status="active" if b.get("state") == "active" else "completed",
                url=f"https://monday.com/boards/{b.get('id')}",
                raw_data=b,
            )
            for b in boards
        ]

    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific board"""
        board_id = external_id.replace("monday:", "")
        query = f"""
        query {{
            boards(ids: [{board_id}]) {{
                id
                name
                description
                state
            }}
        }}
        """

        result = await self._graphql(query)
        boards = result.get("data", {}).get("boards", [])

        if not boards:
            return None

        b = boards[0]
        return UnifiedProject(
            external_id=str(b.get("id")),
            name=b.get("name", ""),
            description=b.get("description", ""),
            status="active" if b.get("state") == "active" else "completed",
            url=f"https://monday.com/boards/{b.get('id')}",
            raw_data=b,
        )

    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new board"""
        # Note: This creates a board from scratch; you may want to use a template
        mutation = """
        mutation CreateBoard($boardName: String!, $boardKind: BoardKind!) {
            create_board(board_name: $boardName, board_kind: $boardKind) {
                id
            }
        }
        """

        result = await self._graphql(mutation, {
            "boardName": project.name,
            "boardKind": "public"
        })

        board_data = result.get("data", {}).get("create_board", {})
        project.external_id = str(board_data.get("id", ""))
        project.url = f"https://monday.com/boards/{project.external_id}"
        return project

    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update a board - Monday has limited board update capabilities"""
        # Monday doesn't allow updating board name/description via API easily
        # This would require using board_update which is limited
        return project

    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all items (tasks) in a board"""
        board_id = project_external_id.replace("monday:", "")
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

        result = await self._graphql(query)
        boards = result.get("data", {}).get("boards", [])

        if not boards:
            return []

        items = boards[0].get("items_page", {}).get("items", [])

        tasks = []
        for item in items:
            task = UnifiedTask(
                external_id=str(item.get("id")),
                project_external_id=project_external_id,
                title=item.get("name", ""),
                status="todo",
                priority="medium",
                url=f"https://monday.com/boards/{board_id}/pulses/{item.get('id')}",
                raw_data=item,
            )

            # Parse column values
            for col in item.get("column_values", []):
                col_id = col.get("id", "")
                col_text = col.get("text", "")

                if col_id == "status" or "status" in col_id.lower():
                    task.status = self.map_status_to_unified(col_text)
                elif col_id == "person" or "person" in col_id.lower():
                    task.assignee = col_text
                elif col_id == "date" or "date" in col_id.lower():
                    task.due_date = self._parse_date(col_text)

            tasks.append(task)

        return tasks

    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific item"""
        item_id = task_external_id.replace("monday:", "")
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

        result = await self._graphql(query)
        items = result.get("data", {}).get("items", [])

        if not items:
            return None

        item = items[0]
        board_id = item.get("board", {}).get("id", "")

        task = UnifiedTask(
            external_id=str(item.get("id")),
            project_external_id=f"monday:{board_id}",
            title=item.get("name", ""),
            status="todo",
            priority="medium",
            url=f"https://monday.com/boards/{board_id}/pulses/{item.get('id')}",
            raw_data=item,
        )

        # Parse column values
        for col in item.get("column_values", []):
            col_id = col.get("id", "")
            col_text = col.get("text", "")
            if "status" in col_id.lower():
                task.status = self.map_status_to_unified(col_text)
            elif "person" in col_id.lower():
                task.assignee = col_text
            elif "date" in col_id.lower():
                task.due_date = self._parse_date(col_text)

        return task

    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new item"""
        board_id = task.project_external_id.replace("monday:", "")

        # Build column values
        column_values = {}
        if task.due_date:
            column_values["date"] = {"date": task.due_date.isoformat()}

        mutation = """
        mutation CreateItem($boardId: ID!, $itemName: String!, $columnValues: JSON) {
            create_item(board_id: $boardId, item_name: $itemName, column_values: $columnValues) {
                id
            }
        }
        """

        result = await self._graphql(mutation, {
            "boardId": board_id,
            "itemName": task.title,
            "columnValues": json.dumps(column_values) if column_values else None
        })

        item_data = result.get("data", {}).get("create_item", {})
        task.external_id = str(item_data.get("id", ""))
        task.url = f"https://monday.com/boards/{board_id}/pulses/{task.external_id}"
        return task

    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing item"""
        item_id = task.external_id.replace("monday:", "")

        # Update item name
        mutation = """
        mutation UpdateItem($itemId: ID!, $columnValues: JSON) {
            change_multiple_column_values(item_id: $itemId, board_id: 0, column_values: $columnValues) {
                id
            }
        }
        """

        column_values = {}
        if task.status:
            column_values["status"] = {"label": self.STATUS_FROM_UNIFIED.get(task.status, "")}
        if task.due_date:
            column_values["date"] = {"date": task.due_date.isoformat()}

        if column_values:
            await self._graphql(mutation, {
                "itemId": item_id,
                "columnValues": json.dumps(column_values)
            })

        return task

    async def complete_task(self, task_external_id: str) -> bool:
        """Mark an item as complete by setting status to Done"""
        item_id = task_external_id.replace("monday:", "")

        mutation = """
        mutation UpdateStatus($itemId: ID!, $columnValues: JSON) {
            change_multiple_column_values(item_id: $itemId, board_id: 0, column_values: $columnValues) {
                id
            }
        }
        """

        result = await self._graphql(mutation, {
            "itemId": item_id,
            "columnValues": json.dumps({"status": {"label": "Done"}})
        })

        return "data" in result

    # Helper methods

    def map_status_to_unified(self, external_status: str) -> str:
        if not external_status:
            return "todo"
        return self.STATUS_TO_UNIFIED.get(external_status.lower(), "todo")

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
