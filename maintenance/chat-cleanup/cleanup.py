#!/usr/bin/env python3
"""
n8n Chat Memory Cleanup Script

Archives old conversations from n8n_chat_histories to aria_chat_archives table,
then deletes archived records from the source table.

Safety features:
- Archive before delete (data is never lost)
- Dry-run mode for testing
- Detailed statistics reporting
- Transaction-based operations
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dateutil.relativedelta import relativedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ChatCleanup:
    """Handles archival and cleanup of old n8n chat conversations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "n8n",
        user: str = "n8n",
        password: str = "",
        retention_days: int = 30,
        dry_run: bool = False
    ):
        """
        Initialize the cleanup handler.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            retention_days: Number of days to retain conversations
            dry_run: If True, only report what would be done without making changes
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.retention_days = retention_days
        self.dry_run = dry_run
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.stats: Dict[str, Any] = {
            "started_at": None,
            "completed_at": None,
            "records_found": 0,
            "records_archived": 0,
            "records_deleted": 0,
            "sessions_affected": 0,
            "errors": [],
            "dry_run": dry_run
        }

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            self.stats["errors"].append(f"Connection error: {str(e)}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def ensure_archive_table(self) -> bool:
        """Ensure the archive table exists."""
        if not self.conn:
            return False

        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS aria_chat_archives (
                        id SERIAL PRIMARY KEY,
                        original_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        message JSONB,
                        created_at TIMESTAMP,
                        archived_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Create indexes
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_aria_chat_archives_session_id
                    ON aria_chat_archives(session_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_aria_chat_archives_created_at
                    ON aria_chat_archives(created_at)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_aria_chat_archives_archived_at
                    ON aria_chat_archives(archived_at)
                """)

                self.conn.commit()
                logger.info("Archive table verified/created")
                return True
        except psycopg2.Error as e:
            logger.error(f"Failed to create archive table: {e}")
            self.stats["errors"].append(f"Table creation error: {str(e)}")
            self.conn.rollback()
            return False

    def get_old_records(self) -> list:
        """
        Find records older than retention period.

        Returns:
            List of records to archive
        """
        if not self.conn:
            return []

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if n8n_chat_histories table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'n8n_chat_histories'
                    )
                """)
                if not cur.fetchone()['exists']:
                    logger.warning("Table n8n_chat_histories does not exist")
                    return []

                # Get old records
                cur.execute("""
                    SELECT id, "sessionId" as session_id, message, "createdAt" as created_at
                    FROM n8n_chat_histories
                    WHERE "createdAt" < %s
                    ORDER BY "createdAt" ASC
                """, (cutoff_date,))

                records = cur.fetchall()
                self.stats["records_found"] = len(records)

                # Count unique sessions
                session_ids = set(r['session_id'] for r in records)
                self.stats["sessions_affected"] = len(session_ids)

                logger.info(f"Found {len(records)} records older than {cutoff_date.date()} "
                           f"across {len(session_ids)} sessions")

                return records
        except psycopg2.Error as e:
            logger.error(f"Failed to query old records: {e}")
            self.stats["errors"].append(f"Query error: {str(e)}")
            return []

    def archive_records(self, records: list) -> bool:
        """
        Archive records to aria_chat_archives table.

        Args:
            records: List of records to archive

        Returns:
            True if successful, False otherwise
        """
        if not self.conn or not records:
            return True

        if self.dry_run:
            logger.info(f"[DRY RUN] Would archive {len(records)} records")
            self.stats["records_archived"] = len(records)
            return True

        try:
            with self.conn.cursor() as cur:
                for record in records:
                    cur.execute("""
                        INSERT INTO aria_chat_archives
                        (original_id, session_id, message, created_at)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        str(record['id']),
                        record['session_id'],
                        json.dumps(record['message']) if isinstance(record['message'], dict) else record['message'],
                        record['created_at']
                    ))

                self.stats["records_archived"] = len(records)
                logger.info(f"Archived {len(records)} records")
                return True
        except psycopg2.Error as e:
            logger.error(f"Failed to archive records: {e}")
            self.stats["errors"].append(f"Archive error: {str(e)}")
            return False

    def delete_archived_records(self, records: list) -> bool:
        """
        Delete records that have been archived.

        Args:
            records: List of records that were archived

        Returns:
            True if successful, False otherwise
        """
        if not self.conn or not records:
            return True

        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete {len(records)} records from n8n_chat_histories")
            self.stats["records_deleted"] = len(records)
            return True

        try:
            record_ids = [record['id'] for record in records]

            with self.conn.cursor() as cur:
                # Delete in batches to avoid very long queries
                batch_size = 1000
                for i in range(0, len(record_ids), batch_size):
                    batch = record_ids[i:i + batch_size]
                    cur.execute(
                        "DELETE FROM n8n_chat_histories WHERE id = ANY(%s)",
                        (batch,)
                    )

                self.stats["records_deleted"] = len(record_ids)
                logger.info(f"Deleted {len(record_ids)} records from n8n_chat_histories")
                return True
        except psycopg2.Error as e:
            logger.error(f"Failed to delete records: {e}")
            self.stats["errors"].append(f"Delete error: {str(e)}")
            return False

    def run_cleanup(self) -> Dict[str, Any]:
        """
        Execute the full cleanup process.

        Returns:
            Statistics dictionary with cleanup results
        """
        self.stats["started_at"] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info("Starting n8n Chat Memory Cleanup")
        if self.dry_run:
            logger.info("*** DRY RUN MODE - No changes will be made ***")
        logger.info(f"Retention period: {self.retention_days} days")
        logger.info("=" * 60)

        # Connect to database
        if not self.connect():
            self.stats["completed_at"] = datetime.now().isoformat()
            return self.stats

        try:
            # Ensure archive table exists
            if not self.ensure_archive_table():
                return self.stats

            # Get old records
            records = self.get_old_records()

            if not records:
                logger.info("No records to clean up")
                self.stats["completed_at"] = datetime.now().isoformat()
                return self.stats

            # Archive records first (safety: archive before delete)
            if not self.archive_records(records):
                logger.error("Archival failed, aborting cleanup")
                self.conn.rollback()
                return self.stats

            # Delete archived records
            if not self.delete_archived_records(records):
                logger.error("Deletion failed, rolling back")
                self.conn.rollback()
                self.stats["records_archived"] = 0
                return self.stats

            # Commit transaction
            if not self.dry_run:
                self.conn.commit()
                logger.info("Transaction committed successfully")

        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}")
            self.stats["errors"].append(f"Unexpected error: {str(e)}")
            if self.conn:
                self.conn.rollback()
        finally:
            self.disconnect()

        self.stats["completed_at"] = datetime.now().isoformat()

        # Print summary
        self._print_summary()

        return self.stats

    def _print_summary(self):
        """Print cleanup summary."""
        logger.info("=" * 60)
        logger.info("Cleanup Summary")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info(f"Records found: {self.stats['records_found']}")
        logger.info(f"Records archived: {self.stats['records_archived']}")
        logger.info(f"Records deleted: {self.stats['records_deleted']}")
        logger.info(f"Sessions affected: {self.stats['sessions_affected']}")
        if self.stats['errors']:
            logger.error(f"Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.error(f"  - {error}")
        logger.info("=" * 60)


def main():
    """Main entry point for the cleanup script."""
    parser = argparse.ArgumentParser(
        description="Clean up old n8n chat conversations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--host",
        default=os.environ.get("POSTGRES_HOST", "localhost"),
        help="PostgreSQL host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("POSTGRES_PORT", "5432")),
        help="PostgreSQL port"
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("POSTGRES_DB", "n8n"),
        help="Database name"
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("POSTGRES_USER", "n8n"),
        help="Database user"
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("POSTGRES_PASSWORD", ""),
        help="Database password"
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("RETENTION_DAYS", "30")),
        help="Number of days to retain conversations"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no changes made)"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output statistics as JSON"
    )

    args = parser.parse_args()

    cleanup = ChatCleanup(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password,
        retention_days=args.retention_days,
        dry_run=args.dry_run
    )

    stats = cleanup.run_cleanup()

    if args.json_output:
        print(json.dumps(stats, indent=2))

    # Exit with error code if there were errors
    sys.exit(1 if stats["errors"] else 0)


if __name__ == "__main__":
    main()
