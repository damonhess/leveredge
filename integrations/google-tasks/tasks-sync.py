"""
Google Tasks Two-Way Sync - FastAPI Application
Port: 8069

Provides REST API for bidirectional sync between aria_tasks and Google Tasks.
Includes webhook endpoint for real-time updates from Google.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from google_auth import get_auth_manager, get_tasks_service, GoogleTasksAuthManager
from sync_handler import (
    TasksSyncHandler,
    SyncStatus,
    ConflictResolution,
    SyncResult
)

# ============================================================================
# Configuration
# ============================================================================

class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/leveredge"

    # Google Tasks
    default_tasklist_id: str = "@default"
    default_conflict_resolution: str = "newest_wins"

    # Webhook
    webhook_secret: Optional[str] = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8069

    class Config:
        env_prefix = "GOOGLE_TASKS_"
        env_file = ".env"


settings = Settings()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("tasks-sync")


# ============================================================================
# Application Lifespan
# ============================================================================

db_pool: Optional[asyncpg.Pool] = None
sync_handler: Optional[TasksSyncHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global db_pool, sync_handler

    # Startup
    logger.info("Starting Google Tasks Sync Service...")

    try:
        # Initialize database pool
        db_pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10
        )
        logger.info("Database pool created")

        # Initialize sync handler if auth is ready
        auth_manager = get_auth_manager()
        if auth_manager.has_valid_credentials():
            tasks_service = get_tasks_service()
            resolution = ConflictResolution(settings.default_conflict_resolution)
            sync_handler = TasksSyncHandler(
                db_pool=db_pool,
                tasks_service=tasks_service,
                default_resolution=resolution,
                default_tasklist_id=settings.default_tasklist_id
            )
            logger.info("Sync handler initialized")
        else:
            logger.warning("Google credentials not configured - sync disabled")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    if db_pool:
        await db_pool.close()
    logger.info("Shutdown complete")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Google Tasks Sync",
    description="Two-way sync between aria_tasks and Google Tasks",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Request/Response Models
# ============================================================================

class TaskCreate(BaseModel):
    """Request model for creating a task."""
    title: str
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "normal"
    category: Optional[str] = None
    tasklist_id: Optional[str] = None
    sync_to_google: bool = True


class TaskUpdate(BaseModel):
    """Request model for updating a task."""
    local_task_id: str
    title: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    sync_to_google: bool = True


class TaskComplete(BaseModel):
    """Request model for completing a task."""
    local_task_id: str
    sync_to_google: bool = True


class WebhookPayload(BaseModel):
    """Webhook payload from Google Tasks."""
    change_type: str = Field(..., description="create, update, or delete")
    task_id: str
    tasklist_id: str
    task_data: Optional[dict] = None
    resource_id: Optional[str] = None
    channel_id: Optional[str] = None


class SyncRequest(BaseModel):
    """Request for full sync operation."""
    tasklist_id: Optional[str] = None
    conflict_resolution: Optional[str] = "newest_wins"


class ConflictResolveRequest(BaseModel):
    """Request to resolve a conflict."""
    local_task_id: str
    resolution: str = Field(..., description="google_wins, local_wins, or newest_wins")


class TaskResponse(BaseModel):
    """Standard task response."""
    success: bool
    message: str
    task: Optional[dict] = None
    google_task_id: Optional[str] = None
    local_task_id: Optional[str] = None


class SyncStatsResponse(BaseModel):
    """Sync statistics response."""
    total_tasks: int
    synced_tasks: int
    pending_push: int
    pending_pull: int
    conflicts: int
    errors: int
    last_sync: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_sync_handler() -> TasksSyncHandler:
    """Get initialized sync handler or raise error."""
    if not sync_handler:
        raise HTTPException(
            status_code=503,
            detail="Sync service not initialized. Check Google credentials."
        )
    return sync_handler


async def ensure_db() -> asyncpg.Pool:
    """Get database pool or raise error."""
    if not db_pool:
        raise HTTPException(
            status_code=503,
            detail="Database not available"
        )
    return db_pool


# ============================================================================
# Health & Auth Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status and component health.
    """
    auth_manager = get_auth_manager()
    auth_status = auth_manager.get_auth_status()

    db_healthy = False
    try:
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_healthy = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_healthy and auth_status['credentials_valid'] else "degraded",
        "service": "google-tasks-sync",
        "port": settings.port,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": "connected" if db_healthy else "disconnected",
            "google_auth": "authenticated" if auth_status['credentials_valid'] else "not_authenticated",
            "sync_handler": "ready" if sync_handler else "not_initialized"
        },
        "auth_details": {
            "client_secrets_configured": auth_status['client_secrets_configured'],
            "token_exists": auth_status['token_exists'],
            "credentials_expired": auth_status['credentials_expired'],
            "has_refresh_token": auth_status['has_refresh_token']
        }
    }


@app.get("/auth/status")
async def auth_status():
    """Get detailed authentication status."""
    auth_manager = get_auth_manager()
    return auth_manager.get_auth_status()


@app.get("/auth/url")
async def get_auth_url(redirect_uri: str = Query(..., description="OAuth callback URL")):
    """
    Get Google OAuth authorization URL.
    Use this to initiate the OAuth flow.
    """
    auth_manager = get_auth_manager()
    if not auth_manager.has_client_secrets():
        raise HTTPException(
            status_code=400,
            detail="Client secrets not configured. Add client_secrets.json to credentials folder."
        )

    auth_url, state = auth_manager.get_authorization_url(redirect_uri)
    return {
        "authorization_url": auth_url,
        "state": state,
        "redirect_uri": redirect_uri
    }


@app.post("/auth/callback")
async def auth_callback(code: str, redirect_uri: str, state: Optional[str] = None):
    """
    Handle OAuth callback with authorization code.
    Exchanges code for credentials and stores them.
    """
    auth_manager = get_auth_manager()
    try:
        creds = auth_manager.exchange_code(code, redirect_uri)

        # Initialize sync handler now that we have credentials
        global sync_handler
        if db_pool:
            tasks_service = get_tasks_service()
            resolution = ConflictResolution(settings.default_conflict_resolution)
            sync_handler = TasksSyncHandler(
                db_pool=db_pool,
                tasks_service=tasks_service,
                default_resolution=resolution,
                default_tasklist_id=settings.default_tasklist_id
            )
            logger.info("Sync handler initialized after auth")

        return {
            "success": True,
            "message": "Authentication successful",
            "scopes": list(creds.scopes) if creds.scopes else []
        }
    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/revoke")
async def revoke_auth():
    """Revoke Google credentials."""
    auth_manager = get_auth_manager()
    success = auth_manager.revoke_credentials()

    global sync_handler
    sync_handler = None

    return {
        "success": success,
        "message": "Credentials revoked" if success else "Failed to revoke"
    }


# ============================================================================
# Task CRUD Endpoints
# ============================================================================

@app.post("/tasks/create", response_model=TaskResponse)
async def create_task(request: TaskCreate, background_tasks: BackgroundTasks):
    """
    Create a new task locally and optionally sync to Google Tasks.
    """
    handler = get_sync_handler()
    pool = await ensure_db()

    try:
        # Create local task
        local_task = await handler.create_local_task(
            title=request.title,
            notes=request.notes,
            due_date=request.due_date,
            priority=request.priority,
            category=request.category
        )

        google_task_id = None

        # Sync to Google if requested
        if request.sync_to_google:
            tasklist_id = request.tasklist_id or settings.default_tasklist_id
            result = await handler.push_task_to_google(
                str(local_task['id']),
                tasklist_id
            )
            if result.success:
                google_task_id = result.google_task_id
            else:
                logger.warning(f"Failed to sync to Google: {result.error}")

        return TaskResponse(
            success=True,
            message="Task created successfully",
            task=local_task,
            local_task_id=str(local_task['id']),
            google_task_id=google_task_id
        )

    except Exception as e:
        logger.error(f"Create task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/update", response_model=TaskResponse)
async def update_task(request: TaskUpdate):
    """
    Update an existing task and optionally sync to Google Tasks.
    """
    handler = get_sync_handler()

    try:
        # Update local task
        local_task = await handler.update_local_task(
            task_id=request.local_task_id,
            title=request.title,
            notes=request.notes,
            due_date=request.due_date
        )

        if not local_task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get sync record
        sync_record = await handler.get_sync_record(request.local_task_id)
        google_task_id = sync_record['google_task_id'] if sync_record else None

        # Sync to Google if requested and synced
        if request.sync_to_google and sync_record:
            try:
                due = None
                if local_task.get('due_date'):
                    due = local_task['due_date'].isoformat()

                handler.update_google_task(
                    task_id=sync_record['google_task_id'],
                    tasklist_id=sync_record['google_tasklist_id'],
                    title=local_task.get('title'),
                    notes=local_task.get('notes'),
                    due=due
                )

                await handler.update_sync_status(
                    request.local_task_id,
                    SyncStatus.SYNCED
                )
            except Exception as e:
                logger.warning(f"Failed to sync update to Google: {e}")

        return TaskResponse(
            success=True,
            message="Task updated successfully",
            task=local_task,
            local_task_id=request.local_task_id,
            google_task_id=google_task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/complete", response_model=TaskResponse)
async def complete_task(request: TaskComplete):
    """
    Mark a task as completed and optionally sync to Google Tasks.
    """
    handler = get_sync_handler()

    try:
        # Update local task
        completed_at = datetime.now(timezone.utc)
        local_task = await handler.update_local_task(
            task_id=request.local_task_id,
            status="completed",
            completed_at=completed_at
        )

        if not local_task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get sync record
        sync_record = await handler.get_sync_record(request.local_task_id)
        google_task_id = sync_record['google_task_id'] if sync_record else None

        # Sync to Google if requested and synced
        if request.sync_to_google and sync_record:
            try:
                handler.complete_google_task(
                    task_id=sync_record['google_task_id'],
                    tasklist_id=sync_record['google_tasklist_id']
                )
                await handler.update_sync_status(
                    request.local_task_id,
                    SyncStatus.SYNCED
                )
            except Exception as e:
                logger.warning(f"Failed to sync completion to Google: {e}")

        return TaskResponse(
            success=True,
            message="Task marked as completed",
            task=local_task,
            local_task_id=request.local_task_id,
            google_task_id=google_task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, sync_to_google: bool = True):
    """
    Delete a task (soft delete) and optionally remove from Google Tasks.
    """
    handler = get_sync_handler()

    try:
        # Get sync record before deletion
        sync_record = await handler.get_sync_record(task_id)

        # Soft delete local task
        success = await handler.delete_local_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        # Delete from Google if synced
        if sync_to_google and sync_record:
            try:
                handler.delete_google_task(
                    task_id=sync_record['google_task_id'],
                    tasklist_id=sync_record['google_tasklist_id']
                )
            except Exception as e:
                logger.warning(f"Failed to delete from Google: {e}")

        return {
            "success": True,
            "message": "Task deleted",
            "local_task_id": task_id,
            "google_task_id": sync_record['google_task_id'] if sync_record else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    Get a task by ID with sync status.
    """
    handler = get_sync_handler()

    try:
        local_task = await handler.get_local_task(task_id)
        if not local_task:
            raise HTTPException(status_code=404, detail="Task not found")

        sync_record = await handler.get_sync_record(task_id)

        return {
            "task": local_task,
            "sync": sync_record
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Sync Endpoints
# ============================================================================

@app.get("/tasks/pending")
async def get_pending_tasks():
    """
    Get all tasks pending synchronization.
    """
    handler = get_sync_handler()

    try:
        pending = await handler.get_pending_tasks()
        conflicts = await handler.get_conflicts()

        return {
            "pending_count": len(pending),
            "conflict_count": len(conflicts),
            "pending_tasks": pending,
            "conflicts": conflicts
        }

    except Exception as e:
        logger.error(f"Get pending tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/full")
async def full_sync(request: SyncRequest, background_tasks: BackgroundTasks):
    """
    Trigger a full bidirectional sync.
    """
    handler = get_sync_handler()

    try:
        # Set conflict resolution if provided
        if request.conflict_resolution:
            handler.default_resolution = ConflictResolution(request.conflict_resolution)

        # Run sync
        results = await handler.full_sync(
            tasklist_id=request.tasklist_id
        )

        return {
            "success": True,
            "message": "Full sync completed",
            "results": results
        }

    except Exception as e:
        logger.error(f"Full sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/stats")
async def get_sync_stats():
    """
    Get sync statistics.
    """
    handler = get_sync_handler()

    try:
        stats = await handler.get_sync_stats()
        return stats

    except Exception as e:
        logger.error(f"Get sync stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/resolve-conflict")
async def resolve_conflict(request: ConflictResolveRequest):
    """
    Manually resolve a sync conflict.
    """
    handler = get_sync_handler()

    try:
        resolution = ConflictResolution(request.resolution)
        result = await handler.resolve_conflict(
            request.local_task_id,
            resolution
        )

        if result.success:
            return {
                "success": True,
                "message": result.message,
                "local_task_id": result.local_task_id,
                "google_task_id": result.google_task_id
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid resolution: {e}")
    except Exception as e:
        logger.error(f"Resolve conflict failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Webhook Endpoint
# ============================================================================

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive task change notifications from Google Tasks.

    This endpoint handles push notifications from Google's webhook system.
    Validates the request and processes task changes asynchronously.
    """
    # Get headers for validation
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_state = request.headers.get("X-Goog-Resource-State")
    resource_id = request.headers.get("X-Goog-Resource-ID")

    # Log webhook receipt
    logger.info(f"Webhook received: state={resource_state}, channel={channel_id}")

    # Handle sync message (initial setup confirmation)
    if resource_state == "sync":
        return JSONResponse(
            status_code=200,
            content={"status": "sync acknowledged"}
        )

    # For exists/not_exists states, we need to fetch the actual change
    if resource_state in ("exists", "not_exists"):
        try:
            # Try to parse body for task details
            body = await request.json()
            payload = WebhookPayload(**body)
        except Exception:
            # If no body, we need to determine change from headers
            # This requires polling Google for changes
            return JSONResponse(
                status_code=200,
                content={
                    "status": "received",
                    "note": "Change notification received, polling required for details"
                }
            )

        # Process webhook
        handler = get_sync_handler()
        result = await handler.handle_webhook(
            change_type=payload.change_type,
            google_task_id=payload.task_id,
            tasklist_id=payload.tasklist_id,
            task_data=payload.task_data
        )

        return {
            "success": result.success,
            "operation": result.operation,
            "message": result.message,
            "error": result.error
        }

    return JSONResponse(
        status_code=200,
        content={"status": "unknown state", "state": resource_state}
    )


@app.post("/webhook/n8n")
async def receive_n8n_webhook(payload: WebhookPayload):
    """
    Receive task change notifications forwarded from n8n workflow.

    This is a simplified webhook endpoint designed to receive
    pre-processed notifications from an n8n workflow.
    """
    logger.info(f"n8n webhook: type={payload.change_type}, task={payload.task_id}")

    handler = get_sync_handler()

    try:
        result = await handler.handle_webhook(
            change_type=payload.change_type,
            google_task_id=payload.task_id,
            tasklist_id=payload.tasklist_id,
            task_data=payload.task_data
        )

        return {
            "success": result.success,
            "operation": result.operation,
            "message": result.message,
            "local_task_id": result.local_task_id,
            "error": result.error
        }

    except Exception as e:
        logger.error(f"n8n webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Task Lists Endpoints
# ============================================================================

@app.get("/tasklists")
async def list_tasklists():
    """
    Get all Google Task Lists.
    """
    handler = get_sync_handler()

    try:
        tasklists = handler.list_google_tasklists()
        return {
            "tasklists": tasklists,
            "count": len(tasklists)
        }

    except Exception as e:
        logger.error(f"List tasklists failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasklists/{tasklist_id}/tasks")
async def list_tasklist_tasks(
    tasklist_id: str,
    show_completed: bool = True,
    updated_since: Optional[str] = None
):
    """
    Get all tasks from a specific Google Task List.
    """
    handler = get_sync_handler()

    try:
        tasks = handler.list_google_tasks(
            tasklist_id=tasklist_id,
            show_completed=show_completed,
            updated_min=updated_since
        )
        return {
            "tasks": tasks,
            "count": len(tasks),
            "tasklist_id": tasklist_id
        }

    except Exception as e:
        logger.error(f"List tasklist tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tasks-sync:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
