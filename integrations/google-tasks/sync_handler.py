"""
Google Tasks Sync Handler
Handles bidirectional sync logic with conflict resolution
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json

import asyncpg
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING_PUSH = "pending_push"
    PENDING_PULL = "pending_pull"
    CONFLICT = "conflict"
    ERROR = "error"


class ConflictResolution(str, Enum):
    GOOGLE_WINS = "google_wins"
    LOCAL_WINS = "local_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


@dataclass
class LocalTask:
    """Represents a task in aria_tasks"""
    id: str
    title: str
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = "needsAction"
    completed_at: Optional[datetime] = None
    priority: str = "normal"
    category: Optional[str] = None
    tags: list = field(default_factory=list)
    parent_task_id: Optional[str] = None
    position: Optional[str] = None
    updated_at: Optional[datetime] = None


@dataclass
class GoogleTask:
    """Represents a task from Google Tasks API"""
    id: str
    tasklist_id: str
    title: str
    notes: Optional[str] = None
    due: Optional[str] = None  # RFC3339 date
    status: str = "needsAction"
    completed: Optional[str] = None  # RFC3339 timestamp
    parent: Optional[str] = None
    position: Optional[str] = None
    updated: Optional[str] = None  # RFC3339 timestamp
    etag: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a sync operation"""
    success: bool
    operation: str
    local_task_id: Optional[str] = None
    google_task_id: Optional[str] = None
    message: str = ""
    conflict_detected: bool = False
    error: Optional[str] = None


class TasksSyncHandler:
    """
    Handles bidirectional sync between aria_tasks and Google Tasks.
    Implements conflict detection and resolution strategies.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        tasks_service: Resource,
        default_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS,
        default_tasklist_id: str = "@default"
    ):
        self.db_pool = db_pool
        self.tasks_service = tasks_service
        self.default_resolution = default_resolution
        self.default_tasklist_id = default_tasklist_id

    # =========================================================================
    # Google Tasks API Operations
    # =========================================================================

    def list_google_tasklists(self) -> list[dict]:
        """Get all Google Task Lists."""
        try:
            result = self.tasks_service.tasklists().list().execute()
            return result.get('items', [])
        except HttpError as e:
            logger.error(f"Failed to list tasklists: {e}")
            raise

    def list_google_tasks(
        self,
        tasklist_id: str = "@default",
        show_completed: bool = True,
        show_deleted: bool = False,
        updated_min: Optional[str] = None
    ) -> list[dict]:
        """
        Get tasks from a Google Task List.

        Args:
            tasklist_id: Google Task List ID
            show_completed: Include completed tasks
            show_deleted: Include deleted tasks
            updated_min: RFC3339 timestamp - only return tasks updated after this time
        """
        try:
            params = {
                'tasklist': tasklist_id,
                'showCompleted': show_completed,
                'showDeleted': show_deleted,
                'maxResults': 100
            }
            if updated_min:
                params['updatedMin'] = updated_min

            result = self.tasks_service.tasks().list(**params).execute()
            return result.get('items', [])
        except HttpError as e:
            logger.error(f"Failed to list tasks: {e}")
            raise

    def get_google_task(self, task_id: str, tasklist_id: str = "@default") -> Optional[dict]:
        """Get a single task from Google Tasks."""
        try:
            return self.tasks_service.tasks().get(
                tasklist=tasklist_id,
                task=task_id
            ).execute()
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error(f"Failed to get task: {e}")
            raise

    def create_google_task(
        self,
        tasklist_id: str,
        title: str,
        notes: Optional[str] = None,
        due: Optional[str] = None,
        parent: Optional[str] = None
    ) -> dict:
        """Create a new task in Google Tasks."""
        body = {'title': title}
        if notes:
            body['notes'] = notes
        if due:
            body['due'] = due

        try:
            params = {'tasklist': tasklist_id, 'body': body}
            if parent:
                params['parent'] = parent

            result = self.tasks_service.tasks().insert(**params).execute()
            logger.info(f"Created Google task: {result['id']}")
            return result
        except HttpError as e:
            logger.error(f"Failed to create task: {e}")
            raise

    def update_google_task(
        self,
        task_id: str,
        tasklist_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        due: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict:
        """Update an existing task in Google Tasks."""
        # First get current task
        task = self.get_google_task(task_id, tasklist_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update fields
        if title is not None:
            task['title'] = title
        if notes is not None:
            task['notes'] = notes
        if due is not None:
            task['due'] = due
        if status is not None:
            task['status'] = status
            if status == 'completed':
                task['completed'] = datetime.now(timezone.utc).isoformat()
            else:
                task.pop('completed', None)

        try:
            result = self.tasks_service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()
            logger.info(f"Updated Google task: {task_id}")
            return result
        except HttpError as e:
            logger.error(f"Failed to update task: {e}")
            raise

    def delete_google_task(self, task_id: str, tasklist_id: str) -> bool:
        """Delete a task from Google Tasks."""
        try:
            self.tasks_service.tasks().delete(
                tasklist=tasklist_id,
                task=task_id
            ).execute()
            logger.info(f"Deleted Google task: {task_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete task: {e}")
            raise

    def complete_google_task(self, task_id: str, tasklist_id: str) -> dict:
        """Mark a Google task as completed."""
        return self.update_google_task(task_id, tasklist_id, status='completed')

    # =========================================================================
    # Local Database Operations
    # =========================================================================

    async def get_local_task(self, task_id: str) -> Optional[dict]:
        """Get a task from aria_tasks."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aria_tasks WHERE id = $1 AND deleted = FALSE",
                task_id
            )
            return dict(row) if row else None

    async def create_local_task(
        self,
        title: str,
        notes: Optional[str] = None,
        due_date: Optional[datetime] = None,
        status: str = "needsAction",
        priority: str = "normal",
        category: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        position: Optional[str] = None,
        user_id: str = "damon"
    ) -> dict:
        """Create a task in aria_tasks."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO aria_tasks (
                    user_id, title, notes, due_date, status,
                    priority, category, parent_task_id, position
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
                """,
                user_id, title, notes, due_date, status,
                priority, category, parent_task_id, position
            )
            logger.info(f"Created local task: {row['id']}")
            return dict(row)

    async def update_local_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        due_date: Optional[datetime] = None,
        status: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[dict]:
        """Update a task in aria_tasks."""
        async with self.db_pool.acquire() as conn:
            # Build dynamic update
            updates = []
            values = []
            idx = 1

            if title is not None:
                updates.append(f"title = ${idx}")
                values.append(title)
                idx += 1
            if notes is not None:
                updates.append(f"notes = ${idx}")
                values.append(notes)
                idx += 1
            if due_date is not None:
                updates.append(f"due_date = ${idx}")
                values.append(due_date)
                idx += 1
            if status is not None:
                updates.append(f"status = ${idx}")
                values.append(status)
                idx += 1
            if completed_at is not None:
                updates.append(f"completed_at = ${idx}")
                values.append(completed_at)
                idx += 1

            if not updates:
                return await self.get_local_task(task_id)

            values.append(task_id)
            query = f"""
                UPDATE aria_tasks
                SET {', '.join(updates)}
                WHERE id = ${idx}
                RETURNING *
            """

            row = await conn.fetchrow(query, *values)
            if row:
                logger.info(f"Updated local task: {task_id}")
            return dict(row) if row else None

    async def delete_local_task(self, task_id: str) -> bool:
        """Soft delete a task in aria_tasks."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE aria_tasks
                SET deleted = TRUE, deleted_at = NOW()
                WHERE id = $1
                """,
                task_id
            )
            logger.info(f"Soft deleted local task: {task_id}")
            return result == "UPDATE 1"

    # =========================================================================
    # Sync Tracking Operations
    # =========================================================================

    async def get_sync_record(self, local_task_id: str) -> Optional[dict]:
        """Get sync record for a local task."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aria_tasks_sync WHERE local_task_id = $1",
                local_task_id
            )
            return dict(row) if row else None

    async def get_sync_by_google_id(
        self,
        google_task_id: str,
        google_tasklist_id: str
    ) -> Optional[dict]:
        """Get sync record by Google task ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM aria_tasks_sync
                WHERE google_task_id = $1 AND google_tasklist_id = $2
                """,
                google_task_id, google_tasklist_id
            )
            return dict(row) if row else None

    async def create_sync_record(
        self,
        local_task_id: str,
        google_task_id: str,
        google_tasklist_id: str,
        google_etag: Optional[str] = None
    ) -> dict:
        """Create a sync tracking record."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO aria_tasks_sync (
                    local_task_id, google_task_id, google_tasklist_id,
                    google_etag, sync_status, last_synced_at
                ) VALUES ($1, $2, $3, $4, 'synced', NOW())
                RETURNING *
                """,
                local_task_id, google_task_id, google_tasklist_id, google_etag
            )
            return dict(row)

    async def update_sync_status(
        self,
        local_task_id: str,
        status: SyncStatus,
        error: Optional[str] = None
    ) -> None:
        """Update sync status for a task."""
        async with self.db_pool.acquire() as conn:
            if error:
                await conn.execute(
                    """
                    UPDATE aria_tasks_sync
                    SET sync_status = $1, last_error = $2,
                        error_count = error_count + 1, last_error_at = NOW()
                    WHERE local_task_id = $3
                    """,
                    status.value, error, local_task_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE aria_tasks_sync
                    SET sync_status = $1, last_synced_at = NOW()
                    WHERE local_task_id = $2
                    """,
                    status.value, local_task_id
                )

    async def get_pending_tasks(self) -> list[dict]:
        """Get tasks that need syncing."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.*, t.title, t.notes, t.due_date, t.status as task_status
                FROM aria_tasks_sync s
                JOIN aria_tasks t ON t.id = s.local_task_id
                WHERE s.sync_status IN ('pending_push', 'pending_pull', 'conflict')
                ORDER BY s.updated_at DESC
                """
            )
            return [dict(row) for row in rows]

    async def get_conflicts(self) -> list[dict]:
        """Get tasks with conflicts."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.*, t.title, t.notes, t.due_date, t.status as task_status
                FROM aria_tasks_sync s
                JOIN aria_tasks t ON t.id = s.local_task_id
                WHERE s.sync_status = 'conflict'
                """
            )
            return [dict(row) for row in rows]

    # =========================================================================
    # Conflict Detection & Resolution
    # =========================================================================

    async def detect_conflict(
        self,
        local_task_id: str,
        google_updated: datetime
    ) -> Optional[SyncStatus]:
        """
        Detect if there's a conflict between local and Google versions.

        Returns:
            SyncStatus indicating the result
        """
        sync_record = await self.get_sync_record(local_task_id)
        if not sync_record:
            return None

        last_synced = sync_record['last_synced_at']
        last_local_update = sync_record['last_local_update']

        # Both modified since last sync = conflict
        if last_local_update > last_synced and google_updated > last_synced:
            await self.update_sync_status(local_task_id, SyncStatus.CONFLICT)
            return SyncStatus.CONFLICT

        # Only Google modified
        if google_updated > last_synced:
            await self.update_sync_status(local_task_id, SyncStatus.PENDING_PULL)
            return SyncStatus.PENDING_PULL

        # Only local modified
        if last_local_update > last_synced:
            await self.update_sync_status(local_task_id, SyncStatus.PENDING_PUSH)
            return SyncStatus.PENDING_PUSH

        return SyncStatus.SYNCED

    async def resolve_conflict(
        self,
        local_task_id: str,
        resolution: Optional[ConflictResolution] = None
    ) -> SyncResult:
        """
        Resolve a conflict using the specified strategy.

        Args:
            local_task_id: ID of the local task
            resolution: Strategy to use (defaults to handler's default)

        Returns:
            SyncResult indicating the outcome
        """
        resolution = resolution or self.default_resolution

        sync_record = await self.get_sync_record(local_task_id)
        if not sync_record:
            return SyncResult(
                success=False,
                operation="resolve_conflict",
                error="No sync record found"
            )

        if sync_record['sync_status'] != 'conflict':
            return SyncResult(
                success=False,
                operation="resolve_conflict",
                error="Task is not in conflict state"
            )

        local_task = await self.get_local_task(local_task_id)
        google_task = self.get_google_task(
            sync_record['google_task_id'],
            sync_record['google_tasklist_id']
        )

        if not local_task or not google_task:
            return SyncResult(
                success=False,
                operation="resolve_conflict",
                error="Could not retrieve task data"
            )

        try:
            if resolution == ConflictResolution.GOOGLE_WINS:
                # Update local from Google
                await self._apply_google_to_local(local_task_id, google_task)
                winner = "google"

            elif resolution == ConflictResolution.LOCAL_WINS:
                # Update Google from local
                self._apply_local_to_google(
                    sync_record['google_task_id'],
                    sync_record['google_tasklist_id'],
                    local_task
                )
                winner = "local"

            elif resolution == ConflictResolution.NEWEST_WINS:
                # Compare timestamps
                google_updated = datetime.fromisoformat(
                    google_task['updated'].replace('Z', '+00:00')
                )
                local_updated = local_task['updated_at']

                if local_updated.tzinfo is None:
                    local_updated = local_updated.replace(tzinfo=timezone.utc)

                if google_updated > local_updated:
                    await self._apply_google_to_local(local_task_id, google_task)
                    winner = "google"
                else:
                    self._apply_local_to_google(
                        sync_record['google_task_id'],
                        sync_record['google_tasklist_id'],
                        local_task
                    )
                    winner = "local"

            else:  # MANUAL - just mark as resolved
                winner = "manual"

            # Update sync record
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE aria_tasks_sync
                    SET sync_status = 'synced',
                        conflict_resolution = $1,
                        conflict_resolved_at = NOW(),
                        last_synced_at = NOW()
                    WHERE local_task_id = $2
                    """,
                    resolution.value, local_task_id
                )

            # Log resolution
            await self._log_sync_operation(
                local_task_id=local_task_id,
                google_task_id=sync_record['google_task_id'],
                google_tasklist_id=sync_record['google_tasklist_id'],
                operation="conflict_resolved",
                after_data={"resolution": resolution.value, "winner": winner}
            )

            return SyncResult(
                success=True,
                operation="resolve_conflict",
                local_task_id=local_task_id,
                google_task_id=sync_record['google_task_id'],
                message=f"Conflict resolved: {winner} wins"
            )

        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return SyncResult(
                success=False,
                operation="resolve_conflict",
                error=str(e)
            )

    async def _apply_google_to_local(
        self,
        local_task_id: str,
        google_task: dict
    ) -> None:
        """Apply Google task data to local task."""
        due_date = None
        if google_task.get('due'):
            due_date = datetime.fromisoformat(
                google_task['due'].replace('Z', '+00:00')
            )

        completed_at = None
        if google_task.get('completed'):
            completed_at = datetime.fromisoformat(
                google_task['completed'].replace('Z', '+00:00')
            )

        await self.update_local_task(
            task_id=local_task_id,
            title=google_task.get('title'),
            notes=google_task.get('notes'),
            due_date=due_date,
            status=google_task.get('status', 'needsAction'),
            completed_at=completed_at
        )

    def _apply_local_to_google(
        self,
        google_task_id: str,
        google_tasklist_id: str,
        local_task: dict
    ) -> dict:
        """Apply local task data to Google task."""
        due = None
        if local_task.get('due_date'):
            due = local_task['due_date'].isoformat()

        return self.update_google_task(
            task_id=google_task_id,
            tasklist_id=google_tasklist_id,
            title=local_task.get('title'),
            notes=local_task.get('notes'),
            due=due,
            status=local_task.get('status')
        )

    # =========================================================================
    # Full Sync Operations
    # =========================================================================

    async def full_sync(
        self,
        tasklist_id: Optional[str] = None,
        user_id: str = "damon"
    ) -> dict:
        """
        Perform a full bidirectional sync.

        Returns:
            Summary of sync operations
        """
        tasklist_id = tasklist_id or self.default_tasklist_id

        results = {
            "pulled": 0,
            "pushed": 0,
            "conflicts": 0,
            "errors": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Get all Google tasks
            google_tasks = self.list_google_tasks(tasklist_id)

            # Get all local tasks with sync records
            async with self.db_pool.acquire() as conn:
                local_rows = await conn.fetch(
                    """
                    SELECT t.*, s.google_task_id, s.google_tasklist_id,
                           s.sync_status, s.last_synced_at
                    FROM aria_tasks t
                    LEFT JOIN aria_tasks_sync s ON s.local_task_id = t.id
                    WHERE t.user_id = $1 AND t.deleted = FALSE
                    """,
                    user_id
                )

            local_tasks = {str(row['id']): dict(row) for row in local_rows}
            synced_google_ids = {
                row['google_task_id'] for row in local_rows
                if row['google_task_id']
            }

            # Process Google tasks
            for g_task in google_tasks:
                g_id = g_task['id']

                if g_id in synced_google_ids:
                    # Check for updates
                    sync = await self.get_sync_by_google_id(g_id, tasklist_id)
                    if sync:
                        g_updated = datetime.fromisoformat(
                            g_task['updated'].replace('Z', '+00:00')
                        )
                        status = await self.detect_conflict(
                            str(sync['local_task_id']),
                            g_updated
                        )
                        if status == SyncStatus.PENDING_PULL:
                            await self._apply_google_to_local(
                                str(sync['local_task_id']),
                                g_task
                            )
                            await self.update_sync_status(
                                str(sync['local_task_id']),
                                SyncStatus.SYNCED
                            )
                            results["pulled"] += 1
                        elif status == SyncStatus.CONFLICT:
                            # Auto-resolve based on default strategy
                            await self.resolve_conflict(
                                str(sync['local_task_id']),
                                self.default_resolution
                            )
                            results["conflicts"] += 1
                else:
                    # New task from Google - create locally
                    result = await self.pull_task_from_google(g_task, tasklist_id)
                    if result.success:
                        results["pulled"] += 1
                    else:
                        results["errors"].append(result.error)

            # Push local tasks without sync records
            for local_id, local_task in local_tasks.items():
                if not local_task.get('google_task_id'):
                    result = await self.push_task_to_google(local_id, tasklist_id)
                    if result.success:
                        results["pushed"] += 1
                    else:
                        results["errors"].append(result.error)

            logger.info(
                f"Full sync completed: {results['pulled']} pulled, "
                f"{results['pushed']} pushed, {results['conflicts']} conflicts"
            )

        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            results["errors"].append(str(e))

        return results

    async def pull_task_from_google(
        self,
        google_task: dict,
        tasklist_id: str,
        user_id: str = "damon"
    ) -> SyncResult:
        """
        Pull a single task from Google Tasks to local.
        """
        try:
            # Parse dates
            due_date = None
            if google_task.get('due'):
                due_date = datetime.fromisoformat(
                    google_task['due'].replace('Z', '+00:00')
                )

            completed_at = None
            if google_task.get('completed'):
                completed_at = datetime.fromisoformat(
                    google_task['completed'].replace('Z', '+00:00')
                )

            # Create local task
            local_task = await self.create_local_task(
                title=google_task.get('title', 'Untitled'),
                notes=google_task.get('notes'),
                due_date=due_date,
                status=google_task.get('status', 'needsAction'),
                position=google_task.get('position'),
                user_id=user_id
            )

            if completed_at:
                await self.update_local_task(
                    str(local_task['id']),
                    completed_at=completed_at
                )

            # Create sync record
            await self.create_sync_record(
                local_task_id=str(local_task['id']),
                google_task_id=google_task['id'],
                google_tasklist_id=tasklist_id,
                google_etag=google_task.get('etag')
            )

            # Log operation
            await self._log_sync_operation(
                local_task_id=str(local_task['id']),
                google_task_id=google_task['id'],
                google_tasklist_id=tasklist_id,
                operation="create_local",
                after_data={"title": google_task.get('title')},
                triggered_by="poll"
            )

            return SyncResult(
                success=True,
                operation="pull",
                local_task_id=str(local_task['id']),
                google_task_id=google_task['id'],
                message=f"Pulled task: {google_task.get('title')}"
            )

        except Exception as e:
            logger.error(f"Failed to pull task: {e}")
            return SyncResult(
                success=False,
                operation="pull",
                google_task_id=google_task.get('id'),
                error=str(e)
            )

    async def push_task_to_google(
        self,
        local_task_id: str,
        tasklist_id: Optional[str] = None
    ) -> SyncResult:
        """
        Push a local task to Google Tasks.
        """
        tasklist_id = tasklist_id or self.default_tasklist_id

        try:
            local_task = await self.get_local_task(local_task_id)
            if not local_task:
                return SyncResult(
                    success=False,
                    operation="push",
                    error=f"Local task {local_task_id} not found"
                )

            # Format due date
            due = None
            if local_task.get('due_date'):
                due = local_task['due_date'].isoformat()

            # Create in Google
            google_task = self.create_google_task(
                tasklist_id=tasklist_id,
                title=local_task.get('title', 'Untitled'),
                notes=local_task.get('notes'),
                due=due
            )

            # Update status if completed
            if local_task.get('status') == 'completed':
                google_task = self.complete_google_task(
                    google_task['id'],
                    tasklist_id
                )

            # Create sync record
            await self.create_sync_record(
                local_task_id=local_task_id,
                google_task_id=google_task['id'],
                google_tasklist_id=tasklist_id,
                google_etag=google_task.get('etag')
            )

            # Log operation
            await self._log_sync_operation(
                local_task_id=local_task_id,
                google_task_id=google_task['id'],
                google_tasklist_id=tasklist_id,
                operation="create_google",
                after_data={"title": local_task.get('title')},
                triggered_by="api"
            )

            return SyncResult(
                success=True,
                operation="push",
                local_task_id=local_task_id,
                google_task_id=google_task['id'],
                message=f"Pushed task: {local_task.get('title')}"
            )

        except Exception as e:
            logger.error(f"Failed to push task: {e}")
            return SyncResult(
                success=False,
                operation="push",
                local_task_id=local_task_id,
                error=str(e)
            )

    # =========================================================================
    # Webhook Handler
    # =========================================================================

    async def handle_webhook(
        self,
        change_type: str,
        google_task_id: str,
        tasklist_id: str,
        task_data: Optional[dict] = None
    ) -> SyncResult:
        """
        Handle incoming webhook notification from Google Tasks.

        Args:
            change_type: Type of change (create, update, delete)
            google_task_id: Google Task ID
            tasklist_id: Google Task List ID
            task_data: Optional task data from webhook
        """
        try:
            sync = await self.get_sync_by_google_id(google_task_id, tasklist_id)

            if change_type == "delete":
                if sync:
                    # Soft delete local task
                    await self.delete_local_task(str(sync['local_task_id']))
                    await self._log_sync_operation(
                        local_task_id=str(sync['local_task_id']),
                        google_task_id=google_task_id,
                        google_tasklist_id=tasklist_id,
                        operation="delete_local",
                        triggered_by="webhook"
                    )
                    return SyncResult(
                        success=True,
                        operation="webhook_delete",
                        local_task_id=str(sync['local_task_id']),
                        message="Task deleted locally"
                    )
                return SyncResult(
                    success=True,
                    operation="webhook_delete",
                    message="Task not found locally, nothing to delete"
                )

            # Fetch current task data from Google
            google_task = task_data or self.get_google_task(google_task_id, tasklist_id)
            if not google_task:
                return SyncResult(
                    success=False,
                    operation="webhook",
                    error="Could not fetch task from Google"
                )

            if change_type == "create":
                if sync:
                    # Task already exists locally
                    return SyncResult(
                        success=True,
                        operation="webhook_create",
                        message="Task already synced"
                    )
                # Pull new task
                return await self.pull_task_from_google(google_task, tasklist_id)

            elif change_type == "update":
                if not sync:
                    # New task via update notification
                    return await self.pull_task_from_google(google_task, tasklist_id)

                # Check for conflicts
                g_updated = datetime.fromisoformat(
                    google_task['updated'].replace('Z', '+00:00')
                )
                status = await self.detect_conflict(
                    str(sync['local_task_id']),
                    g_updated
                )

                if status == SyncStatus.CONFLICT:
                    # Auto-resolve or mark for manual resolution
                    return await self.resolve_conflict(
                        str(sync['local_task_id']),
                        self.default_resolution
                    )

                if status == SyncStatus.PENDING_PULL:
                    await self._apply_google_to_local(
                        str(sync['local_task_id']),
                        google_task
                    )
                    await self.update_sync_status(
                        str(sync['local_task_id']),
                        SyncStatus.SYNCED
                    )
                    return SyncResult(
                        success=True,
                        operation="webhook_update",
                        local_task_id=str(sync['local_task_id']),
                        message="Local task updated from Google"
                    )

                return SyncResult(
                    success=True,
                    operation="webhook_update",
                    message="No changes needed"
                )

        except Exception as e:
            logger.error(f"Webhook handler error: {e}")
            return SyncResult(
                success=False,
                operation="webhook",
                error=str(e)
            )

    # =========================================================================
    # Logging
    # =========================================================================

    async def _log_sync_operation(
        self,
        operation: str,
        local_task_id: Optional[str] = None,
        google_task_id: Optional[str] = None,
        google_tasklist_id: Optional[str] = None,
        before_data: Optional[dict] = None,
        after_data: Optional[dict] = None,
        triggered_by: str = "api",
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Log a sync operation."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO aria_tasks_sync_log (
                    local_task_id, google_task_id, google_tasklist_id,
                    operation, before_data, after_data,
                    triggered_by, success, error_message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                local_task_id,
                google_task_id,
                google_tasklist_id,
                operation,
                json.dumps(before_data) if before_data else None,
                json.dumps(after_data) if after_data else None,
                triggered_by,
                success,
                error_message
            )

    async def get_sync_stats(self, user_id: str = "damon") -> dict:
        """Get sync statistics."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aria_tasks_sync_stats($1)",
                user_id
            )
            return dict(row) if row else {}
