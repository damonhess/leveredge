#!/usr/bin/env python3
"""
APOLLO Service Registry

Maps services to their deployment configurations:
- Deployment scripts
- Health check endpoints
- Container names
- Environment support
- Rollback procedures
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
from enum import Enum

class DeployMethod(str, Enum):
    SCRIPT = "script"           # Run a shell script
    CONTAINER = "container"     # Docker restart/update
    COMPOSE = "compose"         # Docker compose up
    CUSTOM = "custom"           # Custom Python function

@dataclass
class ServiceConfig:
    """Configuration for a deployable service"""
    name: str
    display_name: str
    deploy_method: DeployMethod

    # Script deployment
    script_path: Optional[str] = None
    dry_run_flag: str = "--dry-run"
    force_flag: str = "--force"

    # Container deployment
    container_name: Optional[str] = None
    compose_file: Optional[str] = None
    compose_service: Optional[str] = None

    # Health check
    health_url: Optional[str] = None
    health_timeout: int = 30

    # Environments
    environments: List[str] = field(default_factory=lambda: ["dev", "prod"])

    # Backup config
    backup_type: str = "pre-deploy"
    skip_backup_allowed: bool = False

    # Rollback
    rollback_script: Optional[str] = None
    rollback_container: Optional[str] = None

    # Metadata
    critical: bool = False
    requires_approval: bool = False
    max_deploy_time: int = 300  # seconds

    # Tags for LCIS
    tags: List[str] = field(default_factory=list)


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

SERVICE_REGISTRY: Dict[str, ServiceConfig] = {

    # =========================================================================
    # ARIA ECOSYSTEM
    # =========================================================================

    "aria-frontend": ServiceConfig(
        name="aria-frontend",
        display_name="ARIA Frontend",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/shared/scripts/promote-aria-to-prod.sh",
        dry_run_flag="--dry-run",
        force_flag="--force",
        container_name="aria-frontend-prod",
        health_url="https://aria.leveredgeai.com",
        environments=["dev", "prod"],
        critical=True,
        requires_approval=False,
        tags=["aria", "frontend", "user-facing"],
    ),

    "aria-chat": ServiceConfig(
        name="aria-chat",
        display_name="ARIA Chat API",
        deploy_method=DeployMethod.CONTAINER,
        container_name="aria-chat-prod",
        health_url="https://aria-api.leveredgeai.com/health",
        environments=["dev", "prod"],
        critical=True,
        tags=["aria", "api", "backend"],
    ),

    "aria-memory": ServiceConfig(
        name="aria-memory",
        display_name="ARIA Memory Service",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="aria-memory",
        container_name="aria-memory",
        health_url="http://localhost:8114/health",
        environments=["dev"],
        tags=["aria", "memory"],
    ),

    # =========================================================================
    # CORE INFRASTRUCTURE
    # =========================================================================

    "fleet": ServiceConfig(
        name="fleet",
        display_name="Agent Fleet",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/fleet-start.sh",
        health_url="http://localhost:8099/health",  # Event bus as canary
        environments=["dev"],
        critical=True,
        max_deploy_time=600,  # Fleet takes longer
        tags=["fleet", "agents", "infrastructure"],
    ),

    "event-bus": ServiceConfig(
        name="event-bus",
        display_name="Event Bus",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="event-bus",
        container_name="event-bus",
        health_url="http://localhost:8099/health",
        critical=True,
        tags=["core", "event-bus"],
    ),

    # =========================================================================
    # SCHEMA / DATABASE
    # =========================================================================

    "schema": ServiceConfig(
        name="schema",
        display_name="Database Schema",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/shared/scripts/promote-schema.sh",
        environments=["dev", "prod"],
        critical=True,
        requires_approval=True,  # Schema changes need approval
        tags=["database", "schema", "migrations"],
    ),

    "schema-sync": ServiceConfig(
        name="schema-sync",
        display_name="Schema Sync (DEV → PROD)",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/shared/scripts/sync-schema-dev-to-prod.sh",
        environments=["prod"],
        critical=True,
        requires_approval=True,
        tags=["database", "schema", "sync"],
    ),

    # =========================================================================
    # MONITORING AGENTS
    # =========================================================================

    "panoptes": ServiceConfig(
        name="panoptes",
        display_name="PANOPTES Health Monitor",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="panoptes-watcher",
        container_name="leveredge-panoptes-watcher",
        health_url=None,  # Watcher has no HTTP endpoint
        tags=["monitoring", "health"],
    ),

    "argus": ServiceConfig(
        name="argus",
        display_name="ARGUS Metrics",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="argus",
        container_name="argus",
        health_url="http://localhost:8016/health",
        tags=["monitoring", "metrics"],
    ),

    "watchdog": ServiceConfig(
        name="watchdog",
        display_name="WATCHDOG Meta-Monitor",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="watchdog",
        container_name="leveredge-watchdog",
        health_url="http://localhost:8240/health",
        critical=True,
        tags=["monitoring", "watchdog"],
    ),

    # =========================================================================
    # LCIS
    # =========================================================================

    "lcis-librarian": ServiceConfig(
        name="lcis-librarian",
        display_name="LCIS Librarian",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="lcis-librarian",
        container_name="lcis-librarian",
        health_url="http://localhost:8050/health",
        critical=True,
        tags=["lcis", "knowledge"],
    ),

    # =========================================================================
    # CREATIVE FLEET
    # =========================================================================

    "muse": ServiceConfig(
        name="muse",
        display_name="Muse Creative Writer",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="muse",
        container_name="muse",
        health_url="http://localhost:8030/health",
        tags=["creative", "writing"],
    ),

    # =========================================================================
    # PERSONAL AGENTS
    # =========================================================================

    "gym-coach": ServiceConfig(
        name="gym-coach",
        display_name="Gym Coach",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="gym-coach",
        container_name="gym-coach",
        health_url="http://localhost:8230/health",
        tags=["personal", "fitness"],
    ),

    "academic-guide": ServiceConfig(
        name="academic-guide",
        display_name="Academic Guide",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="academic-guide",
        container_name="academic-guide",
        health_url="http://localhost:8231/health",
        tags=["personal", "learning"],
    ),
}


def get_service(name: str) -> Optional[ServiceConfig]:
    """Get service configuration by name"""
    return SERVICE_REGISTRY.get(name)


def list_services() -> List[str]:
    """List all registered services"""
    return list(SERVICE_REGISTRY.keys())


def list_critical_services() -> List[str]:
    """List critical services that need extra care"""
    return [name for name, config in SERVICE_REGISTRY.items() if config.critical]


def get_services_by_tag(tag: str) -> List[str]:
    """Get services by tag"""
    return [name for name, config in SERVICE_REGISTRY.items() if tag in config.tags]
