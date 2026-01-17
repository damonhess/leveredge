#!/usr/bin/env python3
"""
Google Calendar Sync API
FastAPI application for two-way sync between ARIA and Google Calendar

Port: 8068
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Request, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from google_auth import get_auth_manager, GoogleAuthManager
from sync_handler import (
    CalendarSyncHandler,
    CalendarEvent,
    SyncStatus,
    ConflictResolution
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/leveredge"
    db_pool_min: int = 2
    db_pool_max: int = 10

    # Google Calendar
    google_calendar_id: str = "primary"
    conflict_resolution: str = "google_wins"

    # Webhook
    webhook_base_url: str = "https://calendar.leveredge.ai"

    # Server
    host: str = "0.0.0.0"
    port: int = 8068

    class Config:
        env_prefix = "CALENDAR_SYNC_"
        env_file = ".env"


settings = Settings()


# ============================================================================
# Pydantic Models
# ============================================================================

class EventCreate(BaseModel):
    """Request model for creating an event."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = None
    attendees: List[str] = []
    recurrence: Optional[str] = None
    reminders: List[dict] = []
    color_id: Optional[str] = None
    local_event_id: Optional[int] = None


class EventUpdate(BaseModel):
    """Request model for updating an event."""
    google_event_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    recurrence: Optional[str] = None
    reminders: Optional[List[dict]] = None
    color_id: Optional[str] = None


class EventResponse(BaseModel):
    """Response model for event operations."""
    success: bool
    google_event_id: Optional[str] = None
    local_event_id: Optional[int] = None
    message: str = ""
    event: Optional[dict] = None


class WebhookSetup(BaseModel):
    """Request model for webhook setup."""
    webhook_url: Optional[str] = None
    expiration_hours: int = 168  # 1 week default


class AuthCallbackRequest(BaseModel):
    """Request model for OAuth callback."""
    code: str
    state: Optional[str] = None
    redirect_uri: str


# ============================================================================
# Application Setup
# ============================================================================

# Global resources
db_pool: Optional[asyncpg.Pool] = None
sync_handler: Optional[CalendarSyncHandler] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool."""
    global db_pool
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_pool


async def get_sync_handler() -> CalendarSyncHandler:
    """Get sync handler instance."""
    global sync_handler
    if sync_handler is None:
        raise HTTPException(status_code=503, detail="Sync handler not initialized")
    return sync_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global db_pool, sync_handler

    logger.info("Starting Google Calendar Sync API...")

    # Initialize database pool
    try:
        db_pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max
        )
        logger.info("Database pool created")
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise

    # Initialize sync handler
    conflict_res = ConflictResolution(settings.conflict_resolution)
    sync_handler = CalendarSyncHandler(
        db_pool=db_pool,
        calendar_id=settings.google_calendar_id,
        conflict_resolution=conflict_res
    )
    logger.info(f"Sync handler initialized (conflict resolution: {conflict_res.value})")

    yield

    # Cleanup
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


app = FastAPI(
    title="Google Calendar Sync API",
    description="Two-way synchronization between ARIA and Google Calendar",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status and component health.
    """
    auth_manager = get_auth_manager()
    auth_status = auth_manager.get_auth_status()

    # Check database
    db_healthy = False
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy" if db_healthy and auth_status['credentials_valid'] else "degraded",
        "service": "google-calendar-sync",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "google_auth": "authenticated" if auth_status['credentials_valid'] else "needs_auth",
            "sync_handler": "ready" if sync_handler else "not_initialized"
        },
        "auth_status": auth_status
    }


# ============================================================================
# OAuth Endpoints
# ============================================================================

@app.get("/auth/status")
async def get_auth_status():
    """Get current authentication status."""
    auth_manager = get_auth_manager()
    return auth_manager.get_auth_status()


@app.get("/auth/url")
async def get_auth_url(redirect_uri: str = Query(...), state: Optional[str] = None):
    """
    Get OAuth2 authorization URL.
    Redirect user to this URL to authorize the application.
    """
    auth_manager = get_auth_manager()

    if not auth_manager.has_client_secrets():
        raise HTTPException(
            status_code=400,
            detail="Client secrets not configured. Please add client_secrets.json"
        )

    auth_url, state = auth_manager.get_authorization_url(redirect_uri, state)

    return {
        "authorization_url": auth_url,
        "state": state
    }


@app.post("/auth/callback")
async def auth_callback(request: AuthCallbackRequest):
    """
    Handle OAuth2 callback.
    Exchange authorization code for credentials.
    """
    auth_manager = get_auth_manager()

    try:
        creds = auth_manager.exchange_code(request.code, request.redirect_uri)
        return {
            "success": True,
            "message": "Authorization successful",
            "scopes": list(creds.scopes) if creds.scopes else []
        }
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/revoke")
async def revoke_auth():
    """Revoke current credentials."""
    auth_manager = get_auth_manager()
    auth_manager.revoke_credentials()
    return {"success": True, "message": "Credentials revoked"}


# ============================================================================
# Event Endpoints
# ============================================================================

@app.post("/events/create", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Create an event in Google Calendar.
    Used by ARIA to create calendar events.
    """
    try:
        event = CalendarEvent(
            title=event_data.title,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            all_day=event_data.all_day,
            location=event_data.location,
            attendees=event_data.attendees,
            recurrence=event_data.recurrence,
            reminders=event_data.reminders,
            color_id=event_data.color_id,
            local_event_id=event_data.local_event_id,
            source="aria"
        )

        created_event = await handler.create_event(event)

        return EventResponse(
            success=True,
            google_event_id=created_event.google_event_id,
            local_event_id=created_event.local_event_id,
            message="Event created successfully",
            event=created_event.to_google_format()
        )

    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events/update", response_model=EventResponse)
async def update_event(
    event_data: EventUpdate,
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Update an event in Google Calendar.
    Used by ARIA to update existing calendar events.
    """
    try:
        # Get existing event first
        existing = await handler.get_event(event_data.google_event_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Event not found")

        # Apply updates
        if event_data.title is not None:
            existing.title = event_data.title
        if event_data.description is not None:
            existing.description = event_data.description
        if event_data.start_time is not None:
            existing.start_time = event_data.start_time
        if event_data.end_time is not None:
            existing.end_time = event_data.end_time
        if event_data.all_day is not None:
            existing.all_day = event_data.all_day
        if event_data.location is not None:
            existing.location = event_data.location
        if event_data.attendees is not None:
            existing.attendees = event_data.attendees
        if event_data.recurrence is not None:
            existing.recurrence = event_data.recurrence
        if event_data.reminders is not None:
            existing.reminders = event_data.reminders
        if event_data.color_id is not None:
            existing.color_id = event_data.color_id

        updated_event = await handler.update_event(existing)

        return EventResponse(
            success=True,
            google_event_id=updated_event.google_event_id,
            message="Event updated successfully",
            event=updated_event.to_google_format()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Delete an event from Google Calendar.
    Used by ARIA to remove calendar events.
    """
    try:
        await handler.delete_event(event_id)
        return {
            "success": True,
            "message": f"Event {event_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Failed to delete event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/today")
async def get_today_events(
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Get all events for today.
    Returns events from midnight to midnight in UTC.
    """
    try:
        events = await handler.get_today_events()
        return {
            "success": True,
            "count": len(events),
            "events": [e.to_google_format() | {"google_event_id": e.google_event_id} for e in events]
        }
    except Exception as e:
        logger.error(f"Failed to get today's events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/upcoming")
async def get_upcoming_events(
    days: int = Query(7, ge=1, le=90),
    max_results: int = Query(50, ge=1, le=200),
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Get upcoming events.
    Returns events for the next N days.
    """
    try:
        events = await handler.get_upcoming_events(days=days, max_results=max_results)
        return {
            "success": True,
            "count": len(events),
            "days_ahead": days,
            "events": [e.to_google_format() | {"google_event_id": e.google_event_id} for e in events]
        }
    except Exception as e:
        logger.error(f"Failed to get upcoming events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/{event_id}")
async def get_event(
    event_id: str,
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """Get a specific event by ID."""
    try:
        event = await handler.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return {
            "success": True,
            "event": event.to_google_format() | {"google_event_id": event.google_event_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Webhook Endpoints
# ============================================================================

@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None),
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Receive webhook notifications from Google Calendar.
    This endpoint is called by Google when calendar changes occur.
    """
    # Log webhook receipt
    logger.info(f"Webhook received: state={x_goog_resource_state}, channel={x_goog_channel_id}")

    # Build change data from headers
    change_data = {
        "channelId": x_goog_channel_id,
        "resourceId": x_goog_resource_id,
        "resourceState": x_goog_resource_state,
        "messageNumber": x_goog_message_number
    }

    try:
        result = await handler.process_webhook(change_data)
        return result
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        # Return 200 to prevent Google from retrying
        return {"status": "error", "message": str(e)}


@app.post("/webhook/setup")
async def setup_webhook(
    config: WebhookSetup,
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Set up webhook for receiving Google Calendar change notifications.
    """
    webhook_url = config.webhook_url or f"{settings.webhook_base_url}/webhook"

    try:
        channel = await handler.setup_webhook(
            webhook_url=webhook_url,
            expiration_hours=config.expiration_hours
        )
        return {
            "success": True,
            "message": "Webhook set up successfully",
            "channel": channel
        }
    except Exception as e:
        logger.error(f"Failed to set up webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/stop")
async def stop_webhook(
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """Stop receiving webhook notifications."""
    try:
        await handler.stop_webhook()
        return {"success": True, "message": "Webhook stopped"}
    except Exception as e:
        logger.error(f"Failed to stop webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Sync Status Endpoints
# ============================================================================

@app.get("/sync/status")
async def get_sync_status(
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """Get overall sync status and statistics."""
    try:
        status = await handler.get_sync_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/conflicts")
async def get_conflicts(
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get list of events with sync conflicts."""
    try:
        async with pool.acquire() as conn:
            conflicts = await conn.fetch('''
                SELECT s.*, e.title, e.start_time
                FROM aria_calendar_sync s
                LEFT JOIN aria_calendar_events e ON s.local_event_id = e.id
                WHERE s.sync_status = 'conflict'
                ORDER BY s.last_synced DESC
            ''')

        return {
            "success": True,
            "count": len(conflicts),
            "conflicts": [dict(c) for c in conflicts]
        }
    except Exception as e:
        logger.error(f"Failed to get conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/resolve/{google_event_id}")
async def resolve_conflict(
    google_event_id: str,
    resolution: str = Query(..., regex="^(google_wins|aria_wins)$"),
    handler: CalendarSyncHandler = Depends(get_sync_handler)
):
    """
    Manually resolve a sync conflict.

    Args:
        google_event_id: The Google event ID with conflict
        resolution: Either "google_wins" or "aria_wins"
    """
    try:
        if resolution == "google_wins":
            # Fetch from Google and update ARIA
            event = await handler.get_event(google_event_id)
            if event:
                # Get local event ID
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow('''
                        SELECT local_event_id FROM aria_calendar_sync
                        WHERE google_event_id = $1
                    ''', google_event_id)

                if row and row['local_event_id']:
                    await handler._update_aria_from_google(event, row['local_event_id'])
        else:
            # ARIA wins - push local changes to Google
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT e.* FROM aria_calendar_events e
                    JOIN aria_calendar_sync s ON e.id = s.local_event_id
                    WHERE s.google_event_id = $1
                ''', google_event_id)

            if row:
                event = CalendarEvent(
                    google_event_id=google_event_id,
                    title=row['title'],
                    description=row['description'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    all_day=row['all_day'],
                    location=row['location']
                )
                await handler.update_event(event)

        return {
            "success": True,
            "message": f"Conflict resolved using {resolution}"
        }

    except Exception as e:
        logger.error(f"Failed to resolve conflict: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "calendar-sync:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info"
    )
