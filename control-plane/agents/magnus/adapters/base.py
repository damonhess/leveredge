"""
MAGNUS PM Adapter Base Class

Every PM tool adapter inherits from this class.
Provides a unified interface for all project management tools.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel


class UnifiedProject(BaseModel):
    """Unified project representation across all PM tools"""
    external_id: str
    name: str
    description: Optional[str] = None
    status: str = "planning"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    owner: Optional[str] = None
    url: Optional[str] = None
    raw_data: Dict[str, Any] = {}


class UnifiedTask(BaseModel):
    """Unified task representation across all PM tools"""
    external_id: str
    project_external_id: str
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    parent_id: Optional[str] = None
    url: Optional[str] = None
    raw_data: Dict[str, Any] = {}


class PMAdapter(ABC):
    """
    Abstract base class for PM tool adapters.

    Each adapter translates between MAGNUS's unified model
    and the external PM tool's API.
    """

    tool_name: str = "unknown"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration.

        Args:
            config: Contains connection info, credentials, etc.
        """
        self.config = config
        self.instance_url = config.get("instance_url", "")
        self.credentials = config.get("credentials", {})

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection to the PM tool is working"""
        pass

    @abstractmethod
    async def list_projects(self) -> List[UnifiedProject]:
        """List all projects from the PM tool"""
        pass

    @abstractmethod
    async def get_project(self, external_id: str) -> Optional[UnifiedProject]:
        """Get a specific project by its external ID"""
        pass

    @abstractmethod
    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create a new project in the PM tool"""
        pass

    @abstractmethod
    async def update_project(self, project: UnifiedProject) -> UnifiedProject:
        """Update an existing project"""
        pass

    @abstractmethod
    async def list_tasks(self, project_external_id: str) -> List[UnifiedTask]:
        """List all tasks for a project"""
        pass

    @abstractmethod
    async def get_task(self, task_external_id: str) -> Optional[UnifiedTask]:
        """Get a specific task by its external ID"""
        pass

    @abstractmethod
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create a new task in the PM tool"""
        pass

    @abstractmethod
    async def update_task(self, task: UnifiedTask) -> UnifiedTask:
        """Update an existing task"""
        pass

    @abstractmethod
    async def complete_task(self, task_external_id: str) -> bool:
        """Mark a task as complete"""
        pass

    # Status mapping - each adapter overrides as needed
    def map_status_to_unified(self, external_status: str) -> str:
        """Map external status to unified status"""
        return external_status.lower()

    def map_status_from_unified(self, unified_status: str) -> str:
        """Map unified status to external status"""
        return unified_status

    # Priority mapping
    def map_priority_to_unified(self, external_priority: Any) -> str:
        """Map external priority to unified priority"""
        return "medium"

    def map_priority_from_unified(self, unified_priority: str) -> Any:
        """Map unified priority to external format"""
        return unified_priority
