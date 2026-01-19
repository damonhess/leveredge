# MAGNUS PM Adapters
from .base import PMAdapter, UnifiedProject, UnifiedTask
from .leantime import LeantimeAdapter
from .asana import AsanaAdapter
from .jira import JiraAdapter
from .monday import MondayAdapter
from .notion import NotionAdapter
from .linear import LinearAdapter
from .openproject import OpenProjectAdapter

__all__ = [
    'PMAdapter',
    'UnifiedProject',
    'UnifiedTask',
    'LeantimeAdapter',
    'AsanaAdapter',
    'JiraAdapter',
    'MondayAdapter',
    'NotionAdapter',
    'LinearAdapter',
    'OpenProjectAdapter',
]

# Adapter registry for dynamic lookup
ADAPTERS = {
    'leantime': LeantimeAdapter,
    'asana': AsanaAdapter,
    'jira': JiraAdapter,
    'monday': MondayAdapter,
    'notion': NotionAdapter,
    'linear': LinearAdapter,
    'openproject': OpenProjectAdapter,
}
