#!/usr/bin/env python3
"""
APOLLO Migration Manager

Handles database migration tracking and execution for DEV/PROD Supabase.
Tracks applied migrations in apollo_migrations table.
"""

import os
import hashlib
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

# Configuration
MIGRATIONS_DIR = Path("/opt/leveredge/data-plane/dev/supabase/migrations")

DB_CONTAINERS = {
    "dev": "supabase-db-dev",
    "prod": "supabase-db-prod"
}

REALTIME_CONTAINERS = {
    "dev": "realtime-dev.supabase-realtime-dev",
    "prod": "realtime-dev.supabase-realtime"  # PROD realtime container
}


@dataclass
class Migration:
    """Represents a single migration file"""
    filename: str
    filepath: Path
    checksum: str
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None


@dataclass
class MigrationStatus:
    """Status of migrations for an environment"""
    environment: str
    applied: List[Migration] = field(default_factory=list)
    pending: List[Migration] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class MigrationResult:
    """Result of running migrations"""
    success: bool
    applied_count: int = 0
    failed_count: int = 0
    applied_migrations: List[str] = field(default_factory=list)
    failed_migrations: List[str] = field(default_factory=list)
    error: Optional[str] = None
    schema_changed: bool = False


def _run_sql(container: str, sql: str) -> tuple[bool, str]:
    """Execute SQL on a container and return (success, output)"""
    try:
        result = subprocess.run(
            ["docker", "exec", container, "psql", "-U", "postgres", "-d", "postgres", "-t", "-c", sql],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Query timed out"
    except Exception as e:
        return False, str(e)


def _run_sql_file(container: str, filepath: Path) -> tuple[bool, str]:
    """Execute a SQL file on a container"""
    try:
        with open(filepath, 'r') as f:
            sql_content = f.read()

        result = subprocess.run(
            ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", "postgres"],
            input=sql_content,
            capture_output=True,
            text=True,
            timeout=120
        )

        output = result.stdout + result.stderr
        # Check for actual errors (not just notices)
        if result.returncode != 0 and "ERROR:" in output:
            return False, output
        return True, output
    except subprocess.TimeoutExpired:
        return False, "Migration timed out"
    except Exception as e:
        return False, str(e)


def _calculate_checksum(filepath: Path) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def ensure_migrations_table(env: str) -> bool:
    """Ensure the apollo_migrations table exists"""
    container = DB_CONTAINERS.get(env)
    if not container:
        return False

    sql = """
        CREATE TABLE IF NOT EXISTS apollo_migrations (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ DEFAULT NOW(),
            checksum VARCHAR(64),
            applied_by VARCHAR(100) DEFAULT 'apollo'
        );
        CREATE INDEX IF NOT EXISTS idx_apollo_migrations_filename
            ON apollo_migrations(filename);
    """

    success, _ = _run_sql(container, sql)
    return success


def get_migration_status(env: str) -> MigrationStatus:
    """Get the current migration status for an environment"""
    status = MigrationStatus(environment=env)

    container = DB_CONTAINERS.get(env)
    if not container:
        status.error = f"Unknown environment: {env}"
        return status

    # Ensure table exists
    if not ensure_migrations_table(env):
        status.error = "Failed to ensure migrations table exists"
        return status

    # Get applied migrations from database
    success, output = _run_sql(
        container,
        "SELECT filename, applied_at, applied_by FROM apollo_migrations ORDER BY filename;"
    )

    applied_filenames = set()
    if success and output:
        for line in output.strip().split('\n'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 1 and parts[0]:
                    applied_filenames.add(parts[0])
                    status.applied.append(Migration(
                        filename=parts[0],
                        filepath=MIGRATIONS_DIR / parts[0],
                        checksum="",
                        applied_at=parts[1] if len(parts) > 1 else None,
                        applied_by=parts[2] if len(parts) > 2 else None
                    ))

    # Get all migration files
    if MIGRATIONS_DIR.exists():
        for filepath in sorted(MIGRATIONS_DIR.glob("*.sql")):
            filename = filepath.name
            if filename not in applied_filenames:
                status.pending.append(Migration(
                    filename=filename,
                    filepath=filepath,
                    checksum=_calculate_checksum(filepath)
                ))

    return status


def run_migrations(env: str, dry_run: bool = False) -> MigrationResult:
    """Run pending migrations for an environment"""
    result = MigrationResult(success=True)

    container = DB_CONTAINERS.get(env)
    if not container:
        result.success = False
        result.error = f"Unknown environment: {env}"
        return result

    # Get pending migrations
    status = get_migration_status(env)
    if status.error:
        result.success = False
        result.error = status.error
        return result

    if not status.pending:
        return result  # Nothing to do

    if dry_run:
        result.applied_migrations = [m.filename for m in status.pending]
        return result

    # Run each pending migration
    for migration in status.pending:
        print(f"[APOLLO] Applying migration: {migration.filename}")

        success, output = _run_sql_file(container, migration.filepath)

        if success:
            # Record in migrations table
            insert_sql = f"""
                INSERT INTO apollo_migrations (filename, checksum, applied_by)
                VALUES ('{migration.filename}', '{migration.checksum}', 'apollo')
                ON CONFLICT (filename) DO NOTHING;
            """
            _run_sql(container, insert_sql)

            result.applied_count += 1
            result.applied_migrations.append(migration.filename)
            result.schema_changed = True
            print(f"[APOLLO] Applied: {migration.filename}")
        else:
            result.failed_count += 1
            result.failed_migrations.append(migration.filename)
            result.error = f"Failed to apply {migration.filename}: {output[:500]}"
            result.success = False
            print(f"[APOLLO] Failed: {migration.filename} - {output[:200]}")
            break  # Stop on first failure

    return result


def restart_realtime(env: str) -> bool:
    """Restart the realtime container for an environment"""
    container = REALTIME_CONTAINERS.get(env)
    if not container:
        return False

    try:
        result = subprocess.run(
            ["docker", "restart", container],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[APOLLO] Failed to restart realtime: {e}")
        return False


def get_status_dict(env: str) -> Dict[str, Any]:
    """Get migration status as a dictionary for API responses"""
    status = get_migration_status(env)

    return {
        "environment": env,
        "applied_count": len(status.applied),
        "pending_count": len(status.pending),
        "applied": [m.filename for m in status.applied],
        "pending": [m.filename for m in status.pending],
        "error": status.error
    }
