"""
Google Calendar Sync Handler
Manages two-way synchronization between ARIA and Google Calendar
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
import json
import hashlib

import asyncpg
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from google_auth import get_calendar_service

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    """Sync status states."""
    SYNCED = "synced"
    PENDING_TO_GOOGLE = "pending_to_google"
    PENDING_TO_ARIA = "pending_to_aria"
    CONFLICT = "conflict"
    ERROR = "error"
    DELETED = "deleted"


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    GOOGLE_WINS = "google_wins"
    ARIA_WINS = "aria_wins"
    MOST_RECENT = "most_recent"
    MANUAL = "manual"


@dataclass
class CalendarEvent:
    """Represents a calendar event for sync operations."""
    id: Optional[str] = None
    google_event_id: Optional[str] = None
    local_event_id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: bool = False
    location: Optional[str] = None
    attendees: List[str] = field(default_factory=list)
    recurrence: Optional[str] = None
    reminders: List[Dict[str, Any]] = field(default_factory=list)
    color_id: Optional[str] = None
    visibility: str = "default"
    status: str = "confirmed"
    source: str = "aria"  # "aria" or "google"
    updated_at: Optional[datetime] = None
    etag: Optional[str] = None

    def to_google_format(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        event = {
            'summary': self.title,
            'description': self.description or '',
            'location': self.location or '',
            'status': self.status,
            'visibility': self.visibility,
        }

        if self.all_day:
            event['start'] = {'date': self.start_time.strftime('%Y-%m-%d')}
            event['end'] = {'date': self.end_time.strftime('%Y-%m-%d')}
        else:
            event['start'] = {
                'dateTime': self.start_time.isoformat(),
                'timeZone': 'UTC'
            }
            event['end'] = {
                'dateTime': self.end_time.isoformat(),
                'timeZone': 'UTC'
            }

        if self.attendees:
            event['attendees'] = [{'email': email} for email in self.attendees]

        if self.recurrence:
            event['recurrence'] = [self.recurrence]

        if self.reminders:
            event['reminders'] = {
                'useDefault': False,
                'overrides': self.reminders
            }
        else:
            event['reminders'] = {'useDefault': True}

        if self.color_id:
            event['colorId'] = self.color_id

        return event

    @classmethod
    def from_google_format(cls, google_event: Dict[str, Any]) -> 'CalendarEvent':
        """Create CalendarEvent from Google Calendar API response."""
        start = google_event.get('start', {})
        end = google_event.get('end', {})

        # Check if all-day event
        all_day = 'date' in start

        if all_day:
            start_time = datetime.strptime(start['date'], '%Y-%m-%d')
            end_time = datetime.strptime(end['date'], '%Y-%m-%d')
        else:
            start_time = datetime.fromisoformat(
                start.get('dateTime', '').replace('Z', '+00:00')
            )
            end_time = datetime.fromisoformat(
                end.get('dateTime', '').replace('Z', '+00:00')
            )

        attendees = [
            a['email'] for a in google_event.get('attendees', [])
        ]

        reminders = []
        if 'reminders' in google_event and not google_event['reminders'].get('useDefault', True):
            reminders = google_event['reminders'].get('overrides', [])

        recurrence = None
        if 'recurrence' in google_event and google_event['recurrence']:
            recurrence = google_event['recurrence'][0]

        return cls(
            google_event_id=google_event.get('id'),
            title=google_event.get('summary', 'Untitled'),
            description=google_event.get('description'),
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            location=google_event.get('location'),
            attendees=attendees,
            recurrence=recurrence,
            reminders=reminders,
            color_id=google_event.get('colorId'),
            visibility=google_event.get('visibility', 'default'),
            status=google_event.get('status', 'confirmed'),
            source='google',
            updated_at=datetime.fromisoformat(
                google_event.get('updated', '').replace('Z', '+00:00')
            ) if google_event.get('updated') else None,
            etag=google_event.get('etag')
        )

    def compute_hash(self) -> str:
        """Compute a hash of event content for change detection."""
        content = f"{self.title}|{self.description}|{self.start_time}|{self.end_time}|{self.location}"
        return hashlib.md5(content.encode()).hexdigest()


class CalendarSyncHandler:
    """
    Handles two-way synchronization between ARIA and Google Calendar.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        calendar_id: str = 'primary',
        conflict_resolution: ConflictResolution = ConflictResolution.GOOGLE_WINS
    ):
        """
        Initialize the sync handler.

        Args:
            db_pool: AsyncPG connection pool
            calendar_id: Google Calendar ID to sync with
            conflict_resolution: Strategy for resolving conflicts
        """
        self.db_pool = db_pool
        self.calendar_id = calendar_id
        self.conflict_resolution = conflict_resolution
        self._service: Optional[Resource] = None

    @property
    def service(self) -> Resource:
        """Get or create Google Calendar service."""
        if self._service is None:
            self._service = get_calendar_service()
        return self._service

    async def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """
        Create an event in Google Calendar.

        Args:
            event: CalendarEvent to create

        Returns:
            CalendarEvent with Google event ID
        """
        try:
            google_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event.to_google_format()
            ).execute()

            event.google_event_id = google_event['id']
            event.etag = google_event.get('etag')
            event.updated_at = datetime.now(timezone.utc)

            # Record in sync table
            await self._record_sync(
                google_event_id=event.google_event_id,
                local_event_id=event.local_event_id,
                status=SyncStatus.SYNCED,
                event_hash=event.compute_hash()
            )

            logger.info(f"Created Google Calendar event: {event.google_event_id}")
            return event

        except HttpError as e:
            logger.error(f"Failed to create event: {e}")
            await self._record_sync(
                google_event_id=None,
                local_event_id=event.local_event_id,
                status=SyncStatus.ERROR,
                error_message=str(e)
            )
            raise

    async def update_event(self, event: CalendarEvent) -> CalendarEvent:
        """
        Update an event in Google Calendar.

        Args:
            event: CalendarEvent with updates

        Returns:
            Updated CalendarEvent
        """
        if not event.google_event_id:
            raise ValueError("Cannot update event without google_event_id")

        try:
            google_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event.google_event_id,
                body=event.to_google_format()
            ).execute()

            event.etag = google_event.get('etag')
            event.updated_at = datetime.now(timezone.utc)

            await self._update_sync_status(
                google_event_id=event.google_event_id,
                status=SyncStatus.SYNCED,
                event_hash=event.compute_hash()
            )

            logger.info(f"Updated Google Calendar event: {event.google_event_id}")
            return event

        except HttpError as e:
            logger.error(f"Failed to update event: {e}")
            await self._update_sync_status(
                google_event_id=event.google_event_id,
                status=SyncStatus.ERROR,
                error_message=str(e)
            )
            raise

    async def delete_event(self, google_event_id: str) -> bool:
        """
        Delete an event from Google Calendar.

        Args:
            google_event_id: Google Calendar event ID

        Returns:
            True if successful
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()

            await self._update_sync_status(
                google_event_id=google_event_id,
                status=SyncStatus.DELETED
            )

            logger.info(f"Deleted Google Calendar event: {google_event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                # Already deleted
                await self._update_sync_status(
                    google_event_id=google_event_id,
                    status=SyncStatus.DELETED
                )
                return True
            logger.error(f"Failed to delete event: {e}")
            raise

    async def get_event(self, google_event_id: str) -> Optional[CalendarEvent]:
        """
        Get an event from Google Calendar.

        Args:
            google_event_id: Google Calendar event ID

        Returns:
            CalendarEvent or None if not found
        """
        try:
            google_event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()

            return CalendarEvent.from_google_format(google_event)

        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    async def get_today_events(self) -> List[CalendarEvent]:
        """Get all events for today."""
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.get_events_in_range(start_of_day, end_of_day)

    async def get_upcoming_events(self, days: int = 7, max_results: int = 50) -> List[CalendarEvent]:
        """
        Get upcoming events.

        Args:
            days: Number of days to look ahead
            max_results: Maximum number of events to return

        Returns:
            List of CalendarEvents
        """
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(days=days)

        return await self.get_events_in_range(now, end_time, max_results=max_results)

    async def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """
        Get events within a time range.

        Args:
            start_time: Start of range
            end_time: End of range
            max_results: Maximum number of events

        Returns:
            List of CalendarEvents
        """
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            return [CalendarEvent.from_google_format(e) for e in events]

        except HttpError as e:
            logger.error(f"Failed to get events: {e}")
            raise

    async def process_webhook(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook from Google Calendar.

        Args:
            change_data: Webhook payload data

        Returns:
            Processing result
        """
        resource_id = change_data.get('resourceId')
        channel_id = change_data.get('channelId')
        resource_state = change_data.get('resourceState')

        logger.info(f"Processing webhook: state={resource_state}, resource={resource_id}")

        if resource_state == 'sync':
            # Initial sync notification, no action needed
            return {'status': 'acknowledged', 'action': 'sync_notification'}

        if resource_state == 'exists':
            # Changes exist, need to fetch and process
            return await self._process_calendar_changes(resource_id)

        return {'status': 'ignored', 'reason': f'Unknown state: {resource_state}'}

    async def _process_calendar_changes(self, resource_id: str) -> Dict[str, Any]:
        """
        Fetch and process calendar changes.

        Args:
            resource_id: Resource that changed

        Returns:
            Processing result with counts
        """
        # Get sync token from database
        sync_token = await self._get_sync_token()

        changes = {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0}

        try:
            # Fetch changes using sync token or full sync
            request_params = {
                'calendarId': self.calendar_id,
                'singleEvents': True
            }

            if sync_token:
                request_params['syncToken'] = sync_token
            else:
                # Full sync - get last 30 days
                now = datetime.now(timezone.utc)
                request_params['timeMin'] = (now - timedelta(days=30)).isoformat()

            events_result = self.service.events().list(**request_params).execute()

            # Store new sync token
            new_sync_token = events_result.get('nextSyncToken')
            if new_sync_token:
                await self._store_sync_token(new_sync_token)

            # Process each changed event
            for google_event in events_result.get('items', []):
                try:
                    result = await self._process_single_change(google_event)
                    changes[result] += 1
                except Exception as e:
                    logger.error(f"Error processing event {google_event.get('id')}: {e}")
                    changes['errors'] += 1

            return {'status': 'processed', 'changes': changes}

        except HttpError as e:
            if e.resp.status == 410:
                # Sync token expired, need full sync
                await self._clear_sync_token()
                return await self._process_calendar_changes(resource_id)
            raise

    async def _process_single_change(self, google_event: Dict[str, Any]) -> str:
        """
        Process a single event change from Google Calendar.

        Args:
            google_event: Google Calendar event data

        Returns:
            Change type: 'created', 'updated', or 'deleted'
        """
        event_id = google_event.get('id')
        status = google_event.get('status')

        # Check if event exists in our sync table
        existing = await self._get_sync_record(event_id)

        if status == 'cancelled':
            # Event was deleted
            if existing:
                await self._mark_for_aria_delete(event_id, existing['local_event_id'])
            return 'deleted'

        event = CalendarEvent.from_google_format(google_event)
        new_hash = event.compute_hash()

        if not existing:
            # New event from Google
            await self._create_in_aria(event)
            await self._record_sync(
                google_event_id=event_id,
                local_event_id=None,  # Will be set after ARIA creation
                status=SyncStatus.PENDING_TO_ARIA,
                event_hash=new_hash
            )
            return 'created'

        # Check for actual changes
        if existing.get('event_hash') != new_hash:
            # Event was updated
            await self._handle_update_conflict(event, existing)
            return 'updated'

        return 'updated'  # No actual change detected

    async def _handle_update_conflict(
        self,
        google_event: CalendarEvent,
        existing: Dict[str, Any]
    ) -> None:
        """
        Handle potential conflict when Google event is updated.

        Args:
            google_event: Updated event from Google
            existing: Existing sync record
        """
        # Check if ARIA has pending changes
        if existing.get('sync_status') == SyncStatus.PENDING_TO_GOOGLE.value:
            # Conflict: both sides have changes
            if self.conflict_resolution == ConflictResolution.GOOGLE_WINS:
                await self._update_aria_from_google(google_event, existing['local_event_id'])
            elif self.conflict_resolution == ConflictResolution.ARIA_WINS:
                # Keep ARIA changes, they will sync to Google on next push
                pass
            elif self.conflict_resolution == ConflictResolution.MOST_RECENT:
                # Compare timestamps
                aria_updated = existing.get('last_synced')
                if google_event.updated_at and aria_updated:
                    if google_event.updated_at > aria_updated:
                        await self._update_aria_from_google(google_event, existing['local_event_id'])
            else:
                # Manual resolution needed
                await self._mark_conflict(google_event.google_event_id)
        else:
            # No conflict, just update ARIA
            await self._update_aria_from_google(google_event, existing['local_event_id'])

    async def _create_in_aria(self, event: CalendarEvent) -> None:
        """Create event in ARIA calendar table."""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO aria_calendar_events
                (google_event_id, title, description, start_time, end_time,
                 all_day, location, attendees, created_at, updated_at, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), 'google')
            ''', event.google_event_id, event.title, event.description,
                event.start_time, event.end_time, event.all_day, event.location,
                json.dumps(event.attendees))

    async def _update_aria_from_google(self, event: CalendarEvent, local_id: int) -> None:
        """Update ARIA event from Google Calendar data."""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE aria_calendar_events
                SET title = $2, description = $3, start_time = $4, end_time = $5,
                    all_day = $6, location = $7, attendees = $8, updated_at = NOW()
                WHERE id = $1
            ''', local_id, event.title, event.description,
                event.start_time, event.end_time, event.all_day, event.location,
                json.dumps(event.attendees))

        await self._update_sync_status(
            google_event_id=event.google_event_id,
            status=SyncStatus.SYNCED,
            event_hash=event.compute_hash()
        )

    async def _mark_for_aria_delete(self, google_event_id: str, local_id: Optional[int]) -> None:
        """Mark event for deletion in ARIA."""
        if local_id:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    UPDATE aria_calendar_events
                    SET deleted_at = NOW(), sync_status = 'deleted_from_google'
                    WHERE id = $1
                ''', local_id)

    async def _mark_conflict(self, google_event_id: str) -> None:
        """Mark sync record as having a conflict."""
        await self._update_sync_status(
            google_event_id=google_event_id,
            status=SyncStatus.CONFLICT
        )

    async def _record_sync(
        self,
        google_event_id: Optional[str],
        local_event_id: Optional[int],
        status: SyncStatus,
        event_hash: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Record a sync operation in the database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO aria_calendar_sync
                (google_event_id, local_event_id, sync_status, event_hash,
                 error_message, last_synced, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (google_event_id) DO UPDATE SET
                    local_event_id = COALESCE($2, aria_calendar_sync.local_event_id),
                    sync_status = $3,
                    event_hash = COALESCE($4, aria_calendar_sync.event_hash),
                    error_message = $5,
                    last_synced = NOW()
            ''', google_event_id, local_event_id, status.value, event_hash, error_message)

    async def _update_sync_status(
        self,
        google_event_id: str,
        status: SyncStatus,
        event_hash: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update sync status for an event."""
        async with self.db_pool.acquire() as conn:
            if event_hash:
                await conn.execute('''
                    UPDATE aria_calendar_sync
                    SET sync_status = $2, event_hash = $3, error_message = $4, last_synced = NOW()
                    WHERE google_event_id = $1
                ''', google_event_id, status.value, event_hash, error_message)
            else:
                await conn.execute('''
                    UPDATE aria_calendar_sync
                    SET sync_status = $2, error_message = $3, last_synced = NOW()
                    WHERE google_event_id = $1
                ''', google_event_id, status.value, error_message)

    async def _get_sync_record(self, google_event_id: str) -> Optional[Dict[str, Any]]:
        """Get sync record for a Google event."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM aria_calendar_sync WHERE google_event_id = $1
            ''', google_event_id)
            return dict(row) if row else None

    async def _get_sync_token(self) -> Optional[str]:
        """Get stored sync token from database."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT value FROM aria_calendar_metadata
                WHERE key = 'sync_token' AND calendar_id = $1
            ''', self.calendar_id)
            return row['value'] if row else None

    async def _store_sync_token(self, token: str) -> None:
        """Store sync token in database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO aria_calendar_metadata (key, value, calendar_id, updated_at)
                VALUES ('sync_token', $1, $2, NOW())
                ON CONFLICT (key, calendar_id) DO UPDATE SET value = $1, updated_at = NOW()
            ''', token, self.calendar_id)

    async def _clear_sync_token(self) -> None:
        """Clear stored sync token (for full resync)."""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM aria_calendar_metadata
                WHERE key = 'sync_token' AND calendar_id = $1
            ''', self.calendar_id)

    async def setup_webhook(self, webhook_url: str, expiration_hours: int = 168) -> Dict[str, Any]:
        """
        Set up a webhook to receive calendar change notifications.

        Args:
            webhook_url: HTTPS URL to receive notifications
            expiration_hours: How long the webhook should be active (max ~30 days)

        Returns:
            Channel information
        """
        import uuid

        channel_id = str(uuid.uuid4())
        expiration = int((datetime.now(timezone.utc) + timedelta(hours=expiration_hours)).timestamp() * 1000)

        try:
            channel = self.service.events().watch(
                calendarId=self.calendar_id,
                body={
                    'id': channel_id,
                    'type': 'web_hook',
                    'address': webhook_url,
                    'expiration': expiration
                }
            ).execute()

            # Store channel info for later management
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO aria_calendar_metadata (key, value, calendar_id, updated_at)
                    VALUES ('webhook_channel', $1, $2, NOW())
                    ON CONFLICT (key, calendar_id) DO UPDATE SET value = $1, updated_at = NOW()
                ''', json.dumps(channel), self.calendar_id)

            logger.info(f"Webhook set up successfully: channel_id={channel_id}")
            return channel

        except HttpError as e:
            logger.error(f"Failed to set up webhook: {e}")
            raise

    async def stop_webhook(self) -> bool:
        """Stop the current webhook channel."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT value FROM aria_calendar_metadata
                WHERE key = 'webhook_channel' AND calendar_id = $1
            ''', self.calendar_id)

            if not row:
                return False

            channel = json.loads(row['value'])

        try:
            self.service.channels().stop(
                body={
                    'id': channel['id'],
                    'resourceId': channel['resourceId']
                }
            ).execute()

            # Clear stored channel
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    DELETE FROM aria_calendar_metadata
                    WHERE key = 'webhook_channel' AND calendar_id = $1
                ''', self.calendar_id)

            logger.info("Webhook stopped successfully")
            return True

        except HttpError as e:
            logger.error(f"Failed to stop webhook: {e}")
            raise

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get overall sync status and statistics."""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE sync_status = 'synced') as synced,
                    COUNT(*) FILTER (WHERE sync_status = 'pending_to_google') as pending_to_google,
                    COUNT(*) FILTER (WHERE sync_status = 'pending_to_aria') as pending_to_aria,
                    COUNT(*) FILTER (WHERE sync_status = 'conflict') as conflicts,
                    COUNT(*) FILTER (WHERE sync_status = 'error') as errors,
                    MAX(last_synced) as last_sync_time
                FROM aria_calendar_sync
            ''')

            webhook_info = await conn.fetchrow('''
                SELECT value FROM aria_calendar_metadata
                WHERE key = 'webhook_channel' AND calendar_id = $1
            ''', self.calendar_id)

        return {
            'total_events': stats['total'],
            'synced': stats['synced'],
            'pending_to_google': stats['pending_to_google'],
            'pending_to_aria': stats['pending_to_aria'],
            'conflicts': stats['conflicts'],
            'errors': stats['errors'],
            'last_sync_time': stats['last_sync_time'].isoformat() if stats['last_sync_time'] else None,
            'webhook_active': webhook_info is not None,
            'conflict_resolution': self.conflict_resolution.value
        }
