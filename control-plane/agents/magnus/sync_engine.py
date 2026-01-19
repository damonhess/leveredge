"""
MAGNUS Sync Engine

Orchestrates bidirectional sync between MAGNUS and external PM tools.
Every piece on the board, perfectly synchronized.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncpg

from adapters import (
    PMAdapter, UnifiedProject, UnifiedTask, ADAPTERS,
    LeantimeAdapter, OpenProjectAdapter, AsanaAdapter,
    JiraAdapter, MondayAdapter, LinearAdapter, NotionAdapter
)


class SyncDirection(Enum):
    PUSH = "to_source"          # MAGNUS → External
    PULL = "from_source"        # External → MAGNUS
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(Enum):
    MAGNUS_WINS = "magnus_wins"
    EXTERNAL_WINS = "external_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


class SyncEngine:
    """
    Orchestrates sync between MAGNUS and external PM tools.

    Features:
    - Bidirectional sync with conflict detection
    - Change tracking via hashing
    - Conflict resolution strategies
    - Detailed sync logging

    "Every piece must know its position on every board."
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.adapters: Dict[str, PMAdapter] = {}

    async def get_adapter(self, connection_id: str) -> Optional[PMAdapter]:
        """Get or create adapter for a connection"""
        if connection_id in self.adapters:
            return self.adapters[connection_id]

        async with self.pool.acquire() as conn:
            connection = await conn.fetchrow(
                "SELECT * FROM magnus_pm_connections WHERE id = $1::uuid",
                connection_id
            )

            if not connection:
                return None

            tool_name = connection['tool_name']
            adapter_class = ADAPTERS.get(tool_name)

            if not adapter_class:
                return None

            # Get credentials from config (AEGIS integration TODO)
            config = connection['config'] or {}
            # Handle both dict and JSON string
            if isinstance(config, str):
                config = json.loads(config) if config else {}
            credentials = config.get('credentials', {})
            api_key = config.get('api_key') or credentials.get('api_key', '')

            adapter_config = {
                "instance_url": connection['instance_url'] or '',
                "credentials": {
                    "api_key": api_key,
                    **credentials
                },
                **{k: v for k, v in config.items() if k not in ['credentials', 'api_key']}
            }

            adapter = adapter_class(adapter_config)
            self.adapters[connection_id] = adapter
            return adapter

    def _compute_hash(self, data: dict) -> str:
        """Compute hash of entity data for change detection"""
        normalized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def _log_sync(
        self,
        connection_id: str,
        sync_type: str,
        direction: str,
        status: str,
        project_mapping_id: str = None,
        items_synced: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_failed: int = 0,
        conflicts: int = 0,
        error: str = None,
        details: dict = None
    ) -> str:
        """Log sync operation"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO magnus_sync_log
                (connection_id, project_mapping_id, sync_type, direction, status,
                 items_synced, items_created, items_updated, items_failed,
                 conflicts_detected, error_message, details, completed_at)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                        CASE WHEN $5 IN ('completed', 'failed', 'partial') THEN NOW() ELSE NULL END)
                RETURNING id
            """, connection_id, project_mapping_id, sync_type, direction, status,
                items_synced, items_created, items_updated, items_failed,
                conflicts, error, json.dumps(details or {}))
            return str(row['id'])

    async def _update_connection_sync_status(
        self,
        connection_id: str,
        status: str,
        error: str = None
    ):
        """Update connection's last sync status"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE magnus_pm_connections
                SET last_sync_at = NOW(), last_sync_status = $2, last_sync_error = $3,
                    updated_at = NOW()
                WHERE id = $1::uuid
            """, connection_id, status, error)

    # =========================================
    # PROJECT SYNC
    # =========================================

    async def sync_projects(
        self,
        connection_id: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    ) -> dict:
        """Sync all projects for a connection"""
        adapter = await self.get_adapter(connection_id)
        if not adapter:
            return {"error": "Connection not found or adapter unavailable", "synced": 0, "conflicts": 0}

        log_id = await self._log_sync(connection_id, "full", direction.value, "running")

        try:
            results = {
                "pulled": 0,
                "pushed": 0,
                "created": 0,
                "updated": 0,
                "conflicts": 0,
                "errors": []
            }

            if direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
                pull_result = await self._pull_projects(connection_id, adapter)
                results["pulled"] = pull_result["synced"]
                results["created"] += pull_result.get("created", 0)
                results["conflicts"] += pull_result.get("conflicts", 0)
                results["errors"].extend(pull_result.get("errors", []))

            if direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
                push_result = await self._push_projects(connection_id, adapter)
                results["pushed"] = push_result["synced"]
                results["updated"] += push_result.get("updated", 0)
                results["errors"].extend(push_result.get("errors", []))

            final_status = "completed" if not results["errors"] else "partial"
            await self._log_sync(
                connection_id, "full", direction.value, final_status,
                items_synced=results["pulled"] + results["pushed"],
                items_created=results["created"],
                items_updated=results["updated"],
                conflicts=results["conflicts"],
                details=results
            )

            await self._update_connection_sync_status(connection_id, final_status)

            return results

        except Exception as e:
            await self._log_sync(
                connection_id, "full", direction.value, "failed",
                error=str(e)
            )
            await self._update_connection_sync_status(connection_id, "failed", str(e))
            return {"error": str(e), "synced": 0, "conflicts": 0}

    async def _pull_projects(self, connection_id: str, adapter: PMAdapter) -> dict:
        """Pull projects from external tool into MAGNUS"""
        result = {"synced": 0, "created": 0, "conflicts": 0, "errors": []}

        try:
            external_projects = await adapter.list_projects()

            async with self.pool.acquire() as conn:
                for ext_proj in external_projects:
                    try:
                        # Check if mapping exists
                        mapping = await conn.fetchrow("""
                            SELECT pm.*, p.name as magnus_name, p.updated_at as magnus_updated
                            FROM magnus_project_mappings pm
                            LEFT JOIN magnus_projects p ON pm.magnus_project_id = p.id
                            WHERE pm.connection_id = $1::uuid AND pm.external_project_id = $2
                        """, connection_id, ext_proj.external_id)

                        if mapping and mapping['magnus_project_id']:
                            # Update existing project
                            await conn.execute("""
                                UPDATE magnus_projects
                                SET name = $2, description = $3, updated_at = NOW()
                                WHERE id = $1
                            """, mapping['magnus_project_id'], ext_proj.name, ext_proj.description)

                            await conn.execute("""
                                UPDATE magnus_project_mappings
                                SET last_sync_at = NOW(), external_project_name = $2,
                                    last_sync_status = 'success'
                                WHERE id = $1
                            """, mapping['id'], ext_proj.name)
                        else:
                            # Create new project in MAGNUS
                            new_proj = await conn.fetchrow("""
                                INSERT INTO magnus_projects (name, description, status)
                                VALUES ($1, $2, 'active')
                                RETURNING id
                            """, ext_proj.name, ext_proj.description)

                            if mapping:
                                # Update existing mapping
                                await conn.execute("""
                                    UPDATE magnus_project_mappings
                                    SET magnus_project_id = $2, last_sync_at = NOW(),
                                        external_project_name = $3, last_sync_status = 'success'
                                    WHERE id = $1
                                """, mapping['id'], new_proj['id'], ext_proj.name)
                            else:
                                # Create new mapping
                                await conn.execute("""
                                    INSERT INTO magnus_project_mappings
                                    (magnus_project_id, connection_id, external_project_id,
                                     external_project_name, external_project_url, last_sync_at)
                                    VALUES ($1, $2::uuid, $3, $4, $5, NOW())
                                """, new_proj['id'], connection_id, ext_proj.external_id,
                                    ext_proj.name, ext_proj.url)

                            result["created"] += 1

                        result["synced"] += 1

                    except Exception as e:
                        result["errors"].append(f"Project {ext_proj.name}: {str(e)}")

        except Exception as e:
            result["errors"].append(str(e))

        return result

    async def _push_projects(self, connection_id: str, adapter: PMAdapter) -> dict:
        """Push MAGNUS projects to external tool"""
        result = {"synced": 0, "updated": 0, "errors": []}

        async with self.pool.acquire() as conn:
            # Get MAGNUS projects that have mappings to this connection
            mappings = await conn.fetch("""
                SELECT pm.*, p.name, p.description, p.status
                FROM magnus_project_mappings pm
                JOIN magnus_projects p ON pm.magnus_project_id = p.id
                WHERE pm.connection_id = $1::uuid AND pm.sync_enabled != FALSE
            """, connection_id)

            for mapping in mappings:
                try:
                    project = UnifiedProject(
                        external_id=mapping['external_project_id'],
                        name=mapping['name'],
                        description=mapping['description'],
                        status=mapping['status']
                    )

                    await adapter.update_project(project)

                    await conn.execute("""
                        UPDATE magnus_project_mappings
                        SET last_sync_at = NOW(), last_sync_status = 'success'
                        WHERE id = $1
                    """, mapping['id'])

                    result["synced"] += 1
                    result["updated"] += 1

                except Exception as e:
                    result["errors"].append(f"Project {mapping['name']}: {str(e)}")

        return result

    # =========================================
    # TASK SYNC
    # =========================================

    async def sync_tasks(
        self,
        connection_id: str,
        project_mapping_id: str = None,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    ) -> dict:
        """Sync tasks for a connection (optionally filtered by project)"""
        adapter = await self.get_adapter(connection_id)
        if not adapter:
            return {"error": "Connection not found", "synced": 0, "conflicts": 0}

        log_id = await self._log_sync(connection_id, "incremental", direction.value, "running",
                                      project_mapping_id=project_mapping_id)

        try:
            results = {"pulled": 0, "pushed": 0, "created": 0, "updated": 0, "conflicts": 0, "errors": []}

            # Get project mappings
            async with self.pool.acquire() as conn:
                if project_mapping_id:
                    mappings = await conn.fetch(
                        "SELECT * FROM magnus_project_mappings WHERE id = $1::uuid",
                        project_mapping_id
                    )
                else:
                    mappings = await conn.fetch("""
                        SELECT * FROM magnus_project_mappings
                        WHERE connection_id = $1::uuid AND sync_enabled != FALSE
                    """, connection_id)

            for mapping in mappings:
                if direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
                    pull_result = await self._pull_tasks(connection_id, adapter, dict(mapping))
                    results["pulled"] += pull_result["synced"]
                    results["created"] += pull_result.get("created", 0)
                    results["conflicts"] += pull_result.get("conflicts", 0)
                    results["errors"].extend(pull_result.get("errors", []))

                if direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
                    push_result = await self._push_tasks(connection_id, adapter, dict(mapping))
                    results["pushed"] += push_result["synced"]
                    results["updated"] += push_result.get("updated", 0)
                    results["errors"].extend(push_result.get("errors", []))

            final_status = "completed" if not results["errors"] else "partial"
            await self._log_sync(
                connection_id, "incremental", direction.value, final_status,
                project_mapping_id=project_mapping_id,
                items_synced=results["pulled"] + results["pushed"],
                items_created=results["created"],
                items_updated=results["updated"],
                conflicts=results["conflicts"],
                details=results
            )

            return results

        except Exception as e:
            await self._log_sync(
                connection_id, "incremental", direction.value, "failed",
                error=str(e)
            )
            return {"error": str(e), "synced": 0, "conflicts": 0}

    async def _pull_tasks(self, connection_id: str, adapter: PMAdapter, project_mapping: dict) -> dict:
        """Pull tasks from external tool"""
        result = {"synced": 0, "created": 0, "conflicts": 0, "errors": []}

        try:
            external_tasks = await adapter.list_tasks(project_mapping['external_project_id'])

            async with self.pool.acquire() as conn:
                for ext_task in external_tasks:
                    try:
                        # Check if mapping exists
                        task_mapping = await conn.fetchrow("""
                            SELECT tm.*, t.title, t.status, t.updated_at as magnus_updated
                            FROM magnus_task_mappings tm
                            LEFT JOIN magnus_tasks t ON tm.magnus_task_id = t.id
                            WHERE tm.connection_id = $1::uuid AND tm.external_task_id = $2
                        """, connection_id, ext_task.external_id)

                        new_hash = self._compute_hash({
                            "title": ext_task.title,
                            "description": ext_task.description,
                            "status": ext_task.status,
                            "priority": ext_task.priority
                        })

                        if task_mapping and task_mapping['magnus_task_id']:
                            # Check for changes
                            if task_mapping.get('last_sync_hash') != new_hash:
                                # Update task in MAGNUS
                                await conn.execute("""
                                    UPDATE magnus_tasks
                                    SET title = $2, description = $3, status = $4,
                                        priority = $5, external_url = $6,
                                        source_tool = $7, updated_at = NOW()
                                    WHERE id = $1
                                """, task_mapping['magnus_task_id'], ext_task.title,
                                    ext_task.description, ext_task.status, ext_task.priority,
                                    ext_task.url, adapter.tool_name)

                            await conn.execute("""
                                UPDATE magnus_task_mappings
                                SET last_sync_at = NOW(), last_sync_hash = $2,
                                    external_url = $3
                                WHERE id = $1
                            """, task_mapping['id'], new_hash, ext_task.url)
                        else:
                            # Create new task in MAGNUS
                            new_task = await conn.fetchrow("""
                                INSERT INTO magnus_tasks
                                (project_id, title, description, status, priority,
                                 source_tool, external_url, estimated_hours)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                                RETURNING id
                            """, project_mapping['magnus_project_id'], ext_task.title,
                                ext_task.description, ext_task.status, ext_task.priority,
                                adapter.tool_name, ext_task.url, ext_task.estimated_hours)

                            if task_mapping:
                                # Update existing mapping
                                await conn.execute("""
                                    UPDATE magnus_task_mappings
                                    SET magnus_task_id = $2, last_sync_at = NOW(),
                                        last_sync_hash = $3, external_url = $4
                                    WHERE id = $1
                                """, task_mapping['id'], new_task['id'], new_hash, ext_task.url)
                            else:
                                # Create mapping
                                await conn.execute("""
                                    INSERT INTO magnus_task_mappings
                                    (magnus_task_id, connection_id, project_mapping_id,
                                     external_task_id, external_url, last_sync_hash, last_sync_at)
                                    VALUES ($1, $2::uuid, $3::uuid, $4, $5, $6, NOW())
                                """, new_task['id'], connection_id, project_mapping['id'],
                                    ext_task.external_id, ext_task.url, new_hash)

                            result["created"] += 1

                        result["synced"] += 1

                    except Exception as e:
                        result["errors"].append(f"Task {ext_task.title}: {str(e)}")

        except Exception as e:
            result["errors"].append(str(e))

        return result

    async def _push_tasks(self, connection_id: str, adapter: PMAdapter, project_mapping: dict) -> dict:
        """Push MAGNUS tasks to external tool"""
        result = {"synced": 0, "created": 0, "updated": 0, "errors": []}

        async with self.pool.acquire() as conn:
            # Get MAGNUS tasks for this project
            tasks = await conn.fetch("""
                SELECT t.*, tm.external_task_id, tm.id as mapping_id
                FROM magnus_tasks t
                LEFT JOIN magnus_task_mappings tm ON t.id = tm.magnus_task_id
                    AND tm.connection_id = $2::uuid
                WHERE t.project_id = $1
            """, project_mapping['magnus_project_id'], connection_id)

            for task in tasks:
                try:
                    unified_task = UnifiedTask(
                        external_id=task['external_task_id'] or "",
                        project_external_id=project_mapping['external_project_id'],
                        title=task['title'],
                        description=task.get('description'),
                        status=task['status'],
                        priority=task.get('priority', 'medium'),
                        due_date=task.get('due_date'),
                        estimated_hours=float(task['estimated_hours']) if task.get('estimated_hours') else None
                    )

                    if task['external_task_id']:
                        # Update existing
                        await adapter.update_task(unified_task)
                        result["updated"] += 1
                    else:
                        # Create new
                        created = await adapter.create_task(unified_task)

                        # Create mapping
                        await conn.execute("""
                            INSERT INTO magnus_task_mappings
                            (magnus_task_id, connection_id, project_mapping_id,
                             external_task_id, external_url, last_sync_at)
                            VALUES ($1, $2::uuid, $3::uuid, $4, $5, NOW())
                        """, task['id'], connection_id, project_mapping['id'],
                            created.external_id, created.url)

                        # Update task with external URL
                        await conn.execute("""
                            UPDATE magnus_tasks
                            SET external_url = $2, source_tool = $3
                            WHERE id = $1
                        """, task['id'], created.url, adapter.tool_name)

                        result["created"] += 1

                    result["synced"] += 1

                except Exception as e:
                    result["errors"].append(f"Task {task['title']}: {str(e)}")

        return result

    # =========================================
    # SINGLE ENTITY SYNC
    # =========================================

    async def sync_single_task(
        self,
        magnus_task_id: str,
        direction: SyncDirection = SyncDirection.PUSH
    ) -> dict:
        """Sync a single task to/from all connected tools"""
        results = {"synced_to": [], "errors": []}

        async with self.pool.acquire() as conn:
            # Get task and its project
            task = await conn.fetchrow(
                "SELECT * FROM magnus_tasks WHERE id = $1::uuid", magnus_task_id
            )

            if not task:
                return {"error": "Task not found", "synced_to": []}

            # Get all connections for this project
            mappings = await conn.fetch("""
                SELECT pm.*, pc.tool_name, pc.instance_url, pc.id as connection_id
                FROM magnus_project_mappings pm
                JOIN magnus_pm_connections pc ON pm.connection_id = pc.id
                WHERE pm.magnus_project_id = $1 AND pm.sync_enabled != FALSE
            """, task['project_id'])

            for mapping in mappings:
                try:
                    adapter = await self.get_adapter(str(mapping['connection_id']))
                    if not adapter:
                        continue

                    # Check for existing task mapping
                    task_mapping = await conn.fetchrow("""
                        SELECT * FROM magnus_task_mappings
                        WHERE magnus_task_id = $1::uuid AND connection_id = $2
                    """, magnus_task_id, mapping['connection_id'])

                    unified_task = UnifiedTask(
                        external_id=task_mapping['external_task_id'] if task_mapping else "",
                        project_external_id=mapping['external_project_id'],
                        title=task['title'],
                        description=task.get('description'),
                        status=task['status'],
                        priority=task.get('priority', 'medium'),
                        due_date=task.get('due_date'),
                        estimated_hours=float(task['estimated_hours']) if task.get('estimated_hours') else None
                    )

                    if task_mapping:
                        await adapter.update_task(unified_task)
                    else:
                        created = await adapter.create_task(unified_task)
                        await conn.execute("""
                            INSERT INTO magnus_task_mappings
                            (magnus_task_id, connection_id, project_mapping_id,
                             external_task_id, external_url, last_sync_at)
                            VALUES ($1::uuid, $2, $3::uuid, $4, $5, NOW())
                        """, magnus_task_id, mapping['connection_id'], mapping['id'],
                            created.external_id, created.url)

                    results["synced_to"].append(mapping['tool_name'])

                except Exception as e:
                    results["errors"].append(f"{mapping['tool_name']}: {str(e)}")

        return results

    # =========================================
    # CONFLICT RESOLUTION
    # =========================================

    async def get_pending_conflicts(self, connection_id: str = None) -> List[dict]:
        """Get all pending sync conflicts"""
        async with self.pool.acquire() as conn:
            if connection_id:
                rows = await conn.fetch("""
                    SELECT c.*, pc.tool_name, pc.display_name
                    FROM magnus_sync_conflicts c
                    JOIN magnus_pm_connections pc ON c.connection_id = pc.id
                    WHERE c.status = 'pending' AND c.connection_id = $1::uuid
                    ORDER BY c.created_at DESC
                """, connection_id)
            else:
                rows = await conn.fetch("""
                    SELECT c.*, pc.tool_name, pc.display_name
                    FROM magnus_sync_conflicts c
                    JOIN magnus_pm_connections pc ON c.connection_id = pc.id
                    WHERE c.status = 'pending'
                    ORDER BY c.created_at DESC
                """)
            return [dict(r) for r in rows]

    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        merged_data: dict = None
    ) -> dict:
        """Resolve a sync conflict"""
        async with self.pool.acquire() as conn:
            conflict = await conn.fetchrow(
                "SELECT * FROM magnus_sync_conflicts WHERE id = $1::uuid",
                conflict_id
            )

            if not conflict:
                return {"error": "Conflict not found"}

            magnus_data = conflict['magnus_data'] if isinstance(conflict['magnus_data'], dict) else json.loads(conflict['magnus_data'])
            external_data = conflict['external_data'] if isinstance(conflict['external_data'], dict) else json.loads(conflict['external_data'])

            if resolution == ConflictResolution.MAGNUS_WINS:
                final_data = magnus_data
                status = "resolved_magnus"
            elif resolution == ConflictResolution.EXTERNAL_WINS:
                final_data = external_data
                status = "resolved_external"
            elif resolution == ConflictResolution.MANUAL and merged_data:
                final_data = merged_data
                status = "merged"
            else:
                return {"error": "Invalid resolution"}

            # Apply the resolution
            if conflict['entity_type'] == 'task' and conflict['magnus_entity_id']:
                await conn.execute("""
                    UPDATE magnus_tasks
                    SET title = $2, description = $3, status = $4, updated_at = NOW()
                    WHERE id = $1::uuid
                """, conflict['magnus_entity_id'], final_data.get('title'),
                    final_data.get('description'), final_data.get('status'))

            # Mark conflict resolved
            await conn.execute("""
                UPDATE magnus_sync_conflicts
                SET status = $2, resolution = $3, resolved_at = NOW(), resolved_by = 'damon'
                WHERE id = $1::uuid
            """, conflict_id, status, json.dumps(final_data))

            return {"status": "resolved", "resolution": status}

    # =========================================
    # UTILITIES
    # =========================================

    async def get_sync_status(self, connection_id: str = None) -> dict:
        """Get sync status for connections"""
        async with self.pool.acquire() as conn:
            if connection_id:
                connections = await conn.fetch("""
                    SELECT id, tool_name, display_name, last_sync_at, last_sync_status,
                           sync_enabled
                    FROM magnus_pm_connections
                    WHERE id = $1::uuid
                """, connection_id)
            else:
                connections = await conn.fetch("""
                    SELECT id, tool_name, display_name, last_sync_at, last_sync_status,
                           sync_enabled
                    FROM magnus_pm_connections
                    WHERE sync_enabled = TRUE
                    ORDER BY tool_name
                """)

            # Get recent sync logs
            recent_logs = await conn.fetch("""
                SELECT sl.*, pc.tool_name
                FROM magnus_sync_log sl
                JOIN magnus_pm_connections pc ON sl.connection_id = pc.id
                ORDER BY sl.started_at DESC
                LIMIT 20
            """)

            in_progress = [r for r in recent_logs if r['status'] == 'running']

            return {
                "connections": [dict(c) for c in connections],
                "recent_syncs": [dict(r) for r in recent_logs],
                "in_progress": len(in_progress)
            }

    async def list_connections(self) -> List[dict]:
        """List all PM connections"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM magnus_pm_connections
                ORDER BY tool_name, display_name
            """)
            return [dict(r) for r in rows]
