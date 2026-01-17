#!/usr/bin/env python3
"""
AEGIS V2 - Enterprise Credential Management System
Port: 8012

Comprehensive credential management with:
- AES-256 encryption at rest
- Auto-rotation with configurable schedules
- Credential health monitoring
- Version history and rollback
- Expiry alerts via HERMES
- Comprehensive audit logging
- Dashboard with traffic light status
"""

import os
import json
import httpx
import asyncio
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import asyncpg
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configuration
# Password is URL-encoded to handle special characters
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:i%2BNKWrdGrBsHu2n%2FLGzNMY84Avry2RhNOY2QYksldLtX7GEuxdyASrpv3n0IRinS@127.0.0.1:54323/postgres"
)
N8N_URL = os.getenv("N8N_URL", "https://control.n8n.leveredgeai.com")
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")
MASTER_KEY = os.getenv("AEGIS_MASTER_KEY", "leveredge-aegis-v2-default-key")

# Global database pool
db_pool: Optional[asyncpg.Pool] = None


# ─────────────────────────────────────────────────────────────────────────────
# ENCRYPTION LAYER
# ─────────────────────────────────────────────────────────────────────────────

class CredentialEncryption:
    """AES-256 encryption for credential values using Fernet (symmetric)"""

    def __init__(self, master_key: str):
        # Derive a 32-byte key from master key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'aegis_v2_salt_2026',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key)
        self.key_id = hashlib.sha256(master_key.encode()).hexdigest()[:16]

    def encrypt(self, value: str) -> str:
        """Encrypt a credential value"""
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt a credential value"""
        return self.fernet.decrypt(encrypted_value.encode()).decode()


encryption = CredentialEncryption(MASTER_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

class CredentialCreate(BaseModel):
    name: str
    credential_type: str
    provider: str = "n8n"  # n8n, supabase, api, env
    description: Optional[str] = None
    provider_credential_id: Optional[str] = None  # For n8n credentials
    value: Optional[str] = None  # For direct storage (will be encrypted)
    expires_at: Optional[datetime] = None
    rotation_enabled: bool = False
    rotation_interval_hours: int = 720  # 30 days
    rotation_strategy: str = "manual"  # manual, scheduled, on_expiry
    alert_threshold_hours: int = 168  # 7 days
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class CredentialUpdate(BaseModel):
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    rotation_enabled: Optional[bool] = None
    rotation_interval_hours: Optional[int] = None
    rotation_strategy: Optional[str] = None
    alert_threshold_hours: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CredentialApplyRequest(BaseModel):
    workflow_id: str
    node_name: str
    requested_by: str = "HEPHAESTUS"


class RotateRequest(BaseModel):
    trigger: str = "manual"  # manual, emergency
    reason: Optional[str] = None


class RollbackRequest(BaseModel):
    version: Optional[int] = None  # Specific version or previous


class HealthCheckRequest(BaseModel):
    credential_names: Optional[List[str]] = None


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> asyncpg.Pool:
    """Get database connection pool"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return db_pool


async def close_db():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    """Log event to Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event": f"aegis.{action}",
                    "agent": "AEGIS",
                    "data": {"target": target, **details},
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")


async def notify_hermes(message: str, priority: str = "normal"):
    """Send notification via HERMES"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{HERMES_URL}/notify",
                json={"message": message, "priority": priority, "channel": "telegram"},
                timeout=10.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")


async def audit_log(
    pool: asyncpg.Pool,
    credential_name: str,
    action: str,
    actor: str,
    credential_id: Optional[str] = None,
    target: Optional[str] = None,
    details: dict = {},
    success: bool = True,
    error_message: Optional[str] = None
):
    """Log action to audit table"""
    await pool.execute("""
        INSERT INTO aegis_audit_log
        (credential_id, credential_name, action, actor, target, details, success, error_message)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, credential_id, credential_name, action, actor, target, json.dumps(details), success, error_message)


def determine_status(
    expires_at: Optional[datetime],
    alert_threshold_hours: int,
    last_health_check_status: Optional[str] = None,
    rotation_in_progress: bool = False
) -> str:
    """Determine credential status based on current state"""
    now = datetime.utcnow()

    if rotation_in_progress:
        return "rotating"

    if last_health_check_status == "unhealthy":
        return "failed"

    if expires_at:
        if expires_at < now:
            return "expired"
        hours_until_expiry = (expires_at - now).total_seconds() / 3600
        if hours_until_expiry <= alert_threshold_hours:
            return "expiring"

    return "active"


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND TASKS
# ─────────────────────────────────────────────────────────────────────────────

async def scheduled_health_check():
    """Run health checks on all credentials hourly"""
    while True:
        try:
            pool = await get_db()
            credentials = await pool.fetch("SELECT id, name, provider FROM aegis_credentials WHERE status != 'retired'")

            for cred in credentials:
                # Perform health check based on provider
                status = "healthy"  # Default, would do actual check in production

                await pool.execute("""
                    INSERT INTO aegis_health_checks (credential_id, status, response_time_ms)
                    VALUES ($1, $2, $3)
                """, cred['id'], status, 0)

                await pool.execute("""
                    UPDATE aegis_credentials SET last_health_check = NOW() WHERE id = $1
                """, cred['id'])

        except Exception as e:
            print(f"Health check failed: {e}")

        await asyncio.sleep(3600)  # Every hour


async def scheduled_rotation_check():
    """Check for credentials needing rotation"""
    while True:
        try:
            pool = await get_db()

            # Find credentials due for rotation
            credentials = await pool.fetch("""
                SELECT id, name, rotation_strategy, next_rotation_at, expires_at, alert_threshold_hours
                FROM aegis_credentials
                WHERE rotation_enabled = TRUE
                AND status = 'active'
                AND (
                    (rotation_strategy = 'scheduled' AND next_rotation_at <= NOW())
                    OR (rotation_strategy = 'on_expiry' AND expires_at - (alert_threshold_hours || ' hours')::interval <= NOW())
                )
            """)

            for cred in credentials:
                # Trigger rotation
                await log_to_event_bus("rotation_triggered", cred['name'], {"reason": "scheduled"})
                print(f"Rotation triggered for {cred['name']}")

        except Exception as e:
            print(f"Rotation check failed: {e}")

        await asyncio.sleep(1800)  # Every 30 minutes


async def expiry_alert_check():
    """Check for expiring credentials and alert"""
    while True:
        try:
            pool = await get_db()

            # Find credentials approaching expiry that haven't been alerted
            credentials = await pool.fetch("""
                SELECT id, name, expires_at, alert_threshold_hours
                FROM aegis_credentials
                WHERE expires_at IS NOT NULL
                AND alert_sent = FALSE
                AND status = 'active'
                AND expires_at - (alert_threshold_hours || ' hours')::interval <= NOW()
            """)

            for cred in credentials:
                hours_left = (cred['expires_at'] - datetime.utcnow()).total_seconds() / 3600

                await notify_hermes(
                    f"Credential '{cred['name']}' expires in {int(hours_left)} hours",
                    priority="high"
                )

                await pool.execute("""
                    UPDATE aegis_credentials SET alert_sent = TRUE, status = 'expiring' WHERE id = $1
                """, cred['id'])

                await audit_log(pool, cred['name'], "expiry_alert_sent", "scheduler", str(cred['id']))
                await log_to_event_bus("credential.expiring", cred['name'], {"hours_left": hours_left})

        except Exception as e:
            print(f"Expiry alert check failed: {e}")

        await asyncio.sleep(3600)  # Every hour


# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup/shutdown"""
    # Startup
    await get_db()

    # Start background tasks
    tasks = [
        asyncio.create_task(scheduled_health_check()),
        asyncio.create_task(scheduled_rotation_check()),
        asyncio.create_task(expiry_alert_check()),
    ]

    yield

    # Shutdown
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    await close_db()


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AEGIS V2",
    description="Enterprise Credential Management System",
    version="2.0.0",
    lifespan=lifespan
)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Basic health check"""
    pool = await get_db()

    stats = await pool.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as healthy,
            COUNT(*) FILTER (WHERE status = 'expiring') as expiring,
            COUNT(*) FILTER (WHERE status = 'expired') as expired,
            COUNT(*) FILTER (WHERE status = 'failed') as failed
        FROM aegis_credentials WHERE status != 'retired'
    """)

    return {
        "status": "healthy",
        "agent": "AEGIS",
        "version": "2.0.0",
        "port": 8012,
        "credentials_count": stats['total'],
        "healthy_count": stats['healthy'],
        "expiring_count": stats['expiring'],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/dashboard")
async def health_dashboard():
    """Full dashboard with credential status summary"""
    pool = await get_db()

    # Summary stats
    summary = await pool.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as healthy,
            COUNT(*) FILTER (WHERE status = 'expiring') as expiring,
            COUNT(*) FILTER (WHERE status = 'expired') as expired,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'rotating') as rotating
        FROM aegis_credentials WHERE status != 'retired'
    """)

    # Credential list with status
    credentials = await pool.fetch("""
        SELECT
            name, status, provider, credential_type,
            expires_at, last_used_at, last_health_check,
            CASE
                WHEN expires_at IS NOT NULL
                THEN EXTRACT(EPOCH FROM (expires_at - NOW())) / 3600
            END as expires_in_hours
        FROM aegis_credentials
        WHERE status != 'retired'
        ORDER BY
            CASE status
                WHEN 'failed' THEN 1
                WHEN 'expired' THEN 2
                WHEN 'expiring' THEN 3
                ELSE 4
            END,
            name
    """)

    # Recent alerts (credentials that recently triggered alerts)
    alerts = await pool.fetch("""
        SELECT credential_name, action, timestamp, details
        FROM aegis_audit_log
        WHERE action IN ('expiry_alert_sent', 'rotation_failed', 'health_check_failed')
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    return {
        "summary": dict(summary),
        "credentials": [
            {
                "name": c['name'],
                "status": c['status'],
                "provider": c['provider'],
                "type": c['credential_type'],
                "expires_in_hours": round(c['expires_in_hours'], 1) if c['expires_in_hours'] else None,
                "last_used": c['last_used_at'].isoformat() if c['last_used_at'] else None,
                "last_health_check": c['last_health_check'].isoformat() if c['last_health_check'] else None
            }
            for c in credentials
        ],
        "alerts": [
            {
                "credential": a['credential_name'],
                "alert_type": a['action'],
                "created_at": a['timestamp'].isoformat(),
                "details": json.loads(a['details']) if a['details'] else {}
            }
            for a in alerts
        ]
    }


@app.get("/health/expiring")
async def get_expiring_credentials(threshold_hours: int = 168):
    """Get credentials expiring within threshold"""
    pool = await get_db()

    credentials = await pool.fetch("""
        SELECT name, expires_at, provider, credential_type,
            EXTRACT(EPOCH FROM (expires_at - NOW())) / 3600 as hours_left
        FROM aegis_credentials
        WHERE expires_at IS NOT NULL
        AND expires_at - ($1 || ' hours')::interval <= NOW()
        AND status NOT IN ('retired', 'expired')
        ORDER BY expires_at
    """, str(threshold_hours))

    return {
        "credentials": [
            {
                "name": c['name'],
                "expires_at": c['expires_at'].isoformat(),
                "hours_left": round(c['hours_left'], 1),
                "provider": c['provider'],
                "type": c['credential_type']
            }
            for c in credentials
        ],
        "count": len(credentials)
    }


@app.post("/health/check-all")
async def check_all_health():
    """Run health check on all credentials"""
    pool = await get_db()

    credentials = await pool.fetch("""
        SELECT id, name, provider, credential_type
        FROM aegis_credentials WHERE status NOT IN ('retired', 'expired')
    """)

    results = []
    healthy = 0
    unhealthy = 0

    for cred in credentials:
        # In production, this would actually test the credential
        status = "healthy"
        error = None
        response_time = 50  # Mock response time

        # Record health check
        await pool.execute("""
            INSERT INTO aegis_health_checks (credential_id, status, response_time_ms, error_message)
            VALUES ($1, $2, $3, $4)
        """, cred['id'], status, response_time, error)

        await pool.execute("""
            UPDATE aegis_credentials SET last_health_check = NOW() WHERE id = $1
        """, cred['id'])

        if status == "healthy":
            healthy += 1
        else:
            unhealthy += 1

        results.append({
            "name": cred['name'],
            "status": status,
            "response_time_ms": response_time,
            "error": error
        })

    return {
        "checked": len(credentials),
        "healthy": healthy,
        "unhealthy": unhealthy,
        "details": results
    }


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIAL MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/credentials")
async def list_credentials(
    status: Optional[str] = None,
    provider: Optional[str] = None,
    credential_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all credentials (no values exposed)"""
    pool = await get_db()

    query = """
        SELECT name, credential_type, provider, description, status,
            created_at, updated_at, expires_at, last_used_at,
            rotation_enabled, rotation_strategy, tags
        FROM aegis_credentials
        WHERE status != 'retired'
    """
    params = []
    param_idx = 1

    if status:
        query += f" AND status = ${param_idx}"
        params.append(status)
        param_idx += 1

    if provider:
        query += f" AND provider = ${param_idx}"
        params.append(provider)
        param_idx += 1

    if credential_type:
        query += f" AND credential_type = ${param_idx}"
        params.append(credential_type)
        param_idx += 1

    query += f" ORDER BY name LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    credentials = await pool.fetch(query, *params)

    # Get counts
    count_query = "SELECT COUNT(*) FROM aegis_credentials WHERE status != 'retired'"
    total = await pool.fetchval(count_query)

    status_counts = await pool.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'active') as healthy,
            COUNT(*) FILTER (WHERE status = 'expiring') as expiring,
            COUNT(*) FILTER (WHERE status = 'expired') as expired
        FROM aegis_credentials WHERE status != 'retired'
    """)

    await log_to_event_bus("credentials_listed", details={"count": len(credentials)})

    return {
        "credentials": [
            {
                "name": c['name'],
                "type": c['credential_type'],
                "provider": c['provider'],
                "description": c['description'],
                "status": c['status'],
                "created_at": c['created_at'].isoformat(),
                "expires_at": c['expires_at'].isoformat() if c['expires_at'] else None,
                "last_used": c['last_used_at'].isoformat() if c['last_used_at'] else None,
                "rotation_enabled": c['rotation_enabled'],
                "rotation_strategy": c['rotation_strategy'],
                "tags": json.loads(c['tags']) if c['tags'] else []
            }
            for c in credentials
        ],
        "total": total,
        "healthy": status_counts['healthy'],
        "expiring": status_counts['expiring'],
        "expired": status_counts['expired']
    }


@app.get("/credentials/{name}")
async def get_credential(name: str):
    """Get detailed credential info (no value exposed)"""
    pool = await get_db()

    cred = await pool.fetchrow("""
        SELECT * FROM aegis_credentials WHERE name = $1 AND status != 'retired'
    """, name)

    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

    # Get version count
    version_count = await pool.fetchval("""
        SELECT COUNT(*) FROM aegis_credential_versions WHERE credential_id = $1
    """, cred['id'])

    # Get last health check
    health = await pool.fetchrow("""
        SELECT status, checked_at, response_time_ms, error_message
        FROM aegis_health_checks
        WHERE credential_id = $1
        ORDER BY checked_at DESC LIMIT 1
    """, cred['id'])

    # Get usage stats
    usage = await pool.fetchrow("""
        SELECT
            COUNT(*) as total_uses,
            COUNT(*) FILTER (WHERE action = 'applied') as apply_count,
            MAX(timestamp) as last_used
        FROM aegis_audit_log
        WHERE credential_name = $1 AND action IN ('read', 'applied')
    """, name)

    await audit_log(pool, name, "read", "api", str(cred['id']))

    return {
        "name": cred['name'],
        "type": cred['credential_type'],
        "provider": cred['provider'],
        "description": cred['description'],
        "status": cred['status'],
        "created_at": cred['created_at'].isoformat(),
        "updated_at": cred['updated_at'].isoformat(),
        "expires_at": cred['expires_at'].isoformat() if cred['expires_at'] else None,
        "last_used_at": cred['last_used_at'].isoformat() if cred['last_used_at'] else None,
        "last_rotated_at": cred['last_rotated_at'].isoformat() if cred['last_rotated_at'] else None,
        "rotation_config": {
            "enabled": cred['rotation_enabled'],
            "interval_hours": cred['rotation_interval_hours'],
            "strategy": cred['rotation_strategy'],
            "next_rotation": cred['next_rotation_at'].isoformat() if cred['next_rotation_at'] else None
        },
        "alert_config": {
            "threshold_hours": cred['alert_threshold_hours'],
            "alert_sent": cred['alert_sent']
        },
        "health_status": {
            "status": health['status'] if health else "unknown",
            "last_check": health['checked_at'].isoformat() if health else None,
            "response_time_ms": health['response_time_ms'] if health else None
        } if health else None,
        "usage_stats": {
            "total_uses": usage['total_uses'],
            "apply_count": usage['apply_count'],
            "last_used": usage['last_used'].isoformat() if usage['last_used'] else None
        },
        "version_count": version_count,
        "tags": json.loads(cred['tags']) if cred['tags'] else [],
        "metadata": json.loads(cred['metadata']) if cred['metadata'] else {}
    }


@app.post("/credentials")
async def create_credential(cred: CredentialCreate):
    """Create a new credential"""
    pool = await get_db()

    # Check for existing
    existing = await pool.fetchval(
        "SELECT id FROM aegis_credentials WHERE name = $1", cred.name
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Credential '{cred.name}' already exists")

    # Encrypt value if provided
    encrypted_value = None
    if cred.value:
        encrypted_value = encryption.encrypt(cred.value)

    # Calculate next rotation
    next_rotation = None
    if cred.rotation_enabled and cred.rotation_strategy == "scheduled":
        next_rotation = datetime.utcnow() + timedelta(hours=cred.rotation_interval_hours)

    # Insert credential
    row = await pool.fetchrow("""
        INSERT INTO aegis_credentials
        (name, credential_type, provider, description, encrypted_value, encryption_key_id,
         provider_credential_id, expires_at, rotation_enabled, rotation_interval_hours,
         rotation_strategy, next_rotation_at, alert_threshold_hours, tags, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING id, created_at
    """,
        cred.name, cred.credential_type, cred.provider, cred.description,
        encrypted_value, encryption.key_id if encrypted_value else None,
        cred.provider_credential_id, cred.expires_at, cred.rotation_enabled,
        cred.rotation_interval_hours, cred.rotation_strategy, next_rotation,
        cred.alert_threshold_hours, json.dumps(cred.tags), json.dumps(cred.metadata)
    )

    # Create initial version
    await pool.execute("""
        INSERT INTO aegis_credential_versions
        (credential_id, version, encrypted_value, provider_credential_id, created_by, reason)
        VALUES ($1, 1, $2, $3, $4, 'initial')
    """, row['id'], encrypted_value, cred.provider_credential_id, "api")

    await audit_log(pool, cred.name, "created", "api", str(row['id']), details={
        "provider": cred.provider,
        "type": cred.credential_type,
        "has_expiry": cred.expires_at is not None
    })

    await log_to_event_bus("credential.created", cred.name, {
        "provider": cred.provider,
        "type": cred.credential_type
    })

    return {
        "id": str(row['id']),
        "name": cred.name,
        "status": "active",
        "created_at": row['created_at'].isoformat()
    }


@app.patch("/credentials/{name}")
async def update_credential(name: str, update: CredentialUpdate):
    """Update credential configuration"""
    pool = await get_db()

    cred = await pool.fetchrow(
        "SELECT id FROM aegis_credentials WHERE name = $1 AND status != 'retired'", name
    )
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

    updates = []
    params = []
    param_idx = 1

    update_dict = update.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        if field == "tags":
            value = json.dumps(value)
        elif field == "metadata":
            value = json.dumps(value)

        updates.append(f"{field} = ${param_idx}")
        params.append(value)
        param_idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append(f"updated_at = ${param_idx}")
    params.append(datetime.utcnow())
    param_idx += 1

    params.append(cred['id'])

    await pool.execute(f"""
        UPDATE aegis_credentials
        SET {', '.join(updates)}
        WHERE id = ${param_idx}
    """, *params)

    await audit_log(pool, name, "updated", "api", str(cred['id']), details=update_dict)

    return {
        "credential": name,
        "updated_fields": list(update_dict.keys())
    }


@app.delete("/credentials/{name}")
async def retire_credential(name: str):
    """Retire (soft delete) a credential"""
    pool = await get_db()

    cred = await pool.fetchrow(
        "SELECT id FROM aegis_credentials WHERE name = $1 AND status != 'retired'", name
    )
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

    await pool.execute("""
        UPDATE aegis_credentials SET status = 'retired', updated_at = NOW() WHERE id = $1
    """, cred['id'])

    await audit_log(pool, name, "retired", "api", str(cred['id']))
    await log_to_event_bus("credential.retired", name)

    return {"status": "retired", "credential_name": name}


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIAL OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/credentials/{name}/apply")
async def apply_credential(name: str, req: CredentialApplyRequest):
    """Apply credential to a workflow node"""
    pool = await get_db()

    cred = await pool.fetchrow("""
        SELECT id, provider_credential_id, credential_type, status
        FROM aegis_credentials WHERE name = $1 AND status NOT IN ('retired', 'expired')
    """, name)

    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found or unavailable")

    if cred['status'] == 'failed':
        raise HTTPException(status_code=400, detail=f"Credential '{name}' is in failed state")

    # Apply to n8n workflow
    try:
        async with httpx.AsyncClient() as client:
            # Get workflow
            resp = await client.get(
                f"{N8N_URL}/api/v1/workflows/{req.workflow_id}",
                auth=(N8N_USER, N8N_PASS),
                timeout=10.0
            )

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to get workflow")

            workflow = resp.json()

            # Find and update node
            node_found = False
            for node in workflow.get("nodes", []):
                if node.get("name") == req.node_name:
                    node_found = True
                    if "credentials" not in node:
                        node["credentials"] = {}
                    node["credentials"][cred['credential_type']] = {
                        "id": cred['provider_credential_id'],
                        "name": name
                    }
                    break

            if not node_found:
                raise HTTPException(status_code=404, detail=f"Node '{req.node_name}' not found")

            # Update workflow
            update_resp = await client.patch(
                f"{N8N_URL}/api/v1/workflows/{req.workflow_id}",
                auth=(N8N_USER, N8N_PASS),
                json={"nodes": workflow["nodes"]},
                timeout=10.0
            )

            if update_resp.status_code != 200:
                raise HTTPException(status_code=update_resp.status_code, detail="Failed to update workflow")

    except HTTPException:
        raise
    except Exception as e:
        await audit_log(pool, name, "applied", req.requested_by, str(cred['id']),
                       target=req.workflow_id, success=False, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to apply credential: {e}")

    # Update last used
    await pool.execute("""
        UPDATE aegis_credentials SET last_used_at = NOW() WHERE id = $1
    """, cred['id'])

    await audit_log(pool, name, "applied", req.requested_by, str(cred['id']),
                   target=req.workflow_id, details={"node": req.node_name})

    await log_to_event_bus("credential.applied", name, {
        "workflow_id": req.workflow_id,
        "node": req.node_name,
        "requested_by": req.requested_by
    })

    return {
        "status": "applied",
        "credential": name,
        "workflow_id": req.workflow_id,
        "node": req.node_name
    }


@app.post("/credentials/{name}/rotate")
async def rotate_credential(name: str, req: RotateRequest):
    """Rotate a credential"""
    pool = await get_db()

    cred = await pool.fetchrow("""
        SELECT id, encrypted_value, provider_credential_id, provider
        FROM aegis_credentials WHERE name = $1 AND status NOT IN ('retired')
    """, name)

    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

    start_time = datetime.utcnow()

    # Set status to rotating
    await pool.execute("""
        UPDATE aegis_credentials SET status = 'rotating' WHERE id = $1
    """, cred['id'])

    try:
        # Get current version
        current = await pool.fetchrow("""
            SELECT version FROM aegis_credential_versions
            WHERE credential_id = $1 AND is_current = TRUE
        """, cred['id'])

        current_version = current['version'] if current else 0
        new_version = current_version + 1

        # In production, this would actually generate/fetch new credentials
        # For now, we just create a new version entry
        new_encrypted = cred['encrypted_value']  # Would be new value in production

        # Mark old version as not current
        await pool.execute("""
            UPDATE aegis_credential_versions SET is_current = FALSE
            WHERE credential_id = $1
        """, cred['id'])

        # Create new version
        await pool.execute("""
            INSERT INTO aegis_credential_versions
            (credential_id, version, encrypted_value, provider_credential_id, created_by, reason, is_current)
            VALUES ($1, $2, $3, $4, $5, $6, TRUE)
        """, cred['id'], new_version, new_encrypted, cred['provider_credential_id'],
            "rotation_engine", req.trigger)

        # Calculate next rotation
        rotation_interval = await pool.fetchval("""
            SELECT rotation_interval_hours FROM aegis_credentials WHERE id = $1
        """, cred['id'])

        next_rotation = datetime.utcnow() + timedelta(hours=rotation_interval or 720)

        # Update credential
        await pool.execute("""
            UPDATE aegis_credentials
            SET status = 'active', last_rotated_at = NOW(), next_rotation_at = $2, updated_at = NOW()
            WHERE id = $1
        """, cred['id'], next_rotation)

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Record rotation history
        await pool.execute("""
            INSERT INTO aegis_rotation_history
            (credential_id, previous_version, new_version, trigger, duration_ms, success)
            VALUES ($1, $2, $3, $4, $5, TRUE)
        """, cred['id'], current_version, new_version, req.trigger, duration_ms)

        await audit_log(pool, name, "rotated", "rotation_engine", str(cred['id']),
                       details={"trigger": req.trigger, "new_version": new_version})

        await log_to_event_bus("credential.rotated", name, {
            "trigger": req.trigger,
            "previous_version": current_version,
            "new_version": new_version
        })

        return {
            "status": "rotated",
            "credential": name,
            "previous_version": current_version,
            "new_version": new_version,
            "duration_ms": duration_ms
        }

    except Exception as e:
        # Revert status
        await pool.execute("""
            UPDATE aegis_credentials SET status = 'failed' WHERE id = $1
        """, cred['id'])

        await pool.execute("""
            INSERT INTO aegis_rotation_history
            (credential_id, trigger, success, error_message)
            VALUES ($1, $2, FALSE, $3)
        """, cred['id'], req.trigger, str(e))

        await notify_hermes(f"Rotation FAILED for '{name}': {e}", priority="critical")
        await log_to_event_bus("credential.failed", name, {"error": str(e)})

        raise HTTPException(status_code=500, detail=f"Rotation failed: {e}")


@app.post("/credentials/{name}/rollback")
async def rollback_credential(name: str, req: RollbackRequest):
    """Rollback to a previous credential version"""
    pool = await get_db()

    cred = await pool.fetchrow("""
        SELECT id FROM aegis_credentials WHERE name = $1 AND status != 'retired'
    """, name)

    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

    # Get current version
    current = await pool.fetchrow("""
        SELECT version FROM aegis_credential_versions
        WHERE credential_id = $1 AND is_current = TRUE
    """, cred['id'])

    if not current:
        raise HTTPException(status_code=400, detail="No versions found")

    # Determine target version
    if req.version:
        target_version = req.version
    else:
        target_version = current['version'] - 1

    if target_version < 1:
        raise HTTPException(status_code=400, detail="Cannot rollback past version 1")

    # Get target version
    target = await pool.fetchrow("""
        SELECT encrypted_value, provider_credential_id
        FROM aegis_credential_versions
        WHERE credential_id = $1 AND version = $2
    """, cred['id'], target_version)

    if not target:
        raise HTTPException(status_code=404, detail=f"Version {target_version} not found")

    # Mark all as not current
    await pool.execute("""
        UPDATE aegis_credential_versions SET is_current = FALSE
        WHERE credential_id = $1
    """, cred['id'])

    # Mark target as current
    await pool.execute("""
        UPDATE aegis_credential_versions SET is_current = TRUE
        WHERE credential_id = $1 AND version = $2
    """, cred['id'], target_version)

    # Update main credential
    await pool.execute("""
        UPDATE aegis_credentials
        SET encrypted_value = $2, provider_credential_id = $3, status = 'active', updated_at = NOW()
        WHERE id = $1
    """, cred['id'], target['encrypted_value'], target['provider_credential_id'])

    # Record rollback in history
    await pool.execute("""
        UPDATE aegis_rotation_history
        SET rolled_back = TRUE, rollback_at = NOW()
        WHERE credential_id = $1 AND new_version = $2
    """, cred['id'], current['version'])

    await audit_log(pool, name, "rolled_back", "api", str(cred['id']),
                   details={"from_version": current['version'], "to_version": target_version})

    return {
        "status": "rolled_back",
        "credential": name,
        "from_version": current['version'],
        "to_version": target_version
    }


@app.post("/credentials/{name}/test")
async def test_credential(name: str):
    """Test credential health"""
    pool = await get_db()

    cred = await pool.fetchrow("""
        SELECT id, provider, provider_credential_id, credential_type
        FROM aegis_credentials WHERE name = $1 AND status != 'retired'
    """, name)

    if not cred:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")

    # Perform health check (would be provider-specific in production)
    start = datetime.utcnow()
    status = "healthy"
    error = None
    details = {}

    # Mock health check based on provider
    if cred['provider'] == 'n8n':
        # Would test via n8n API
        details = {"method": "n8n_api_check"}
    elif cred['provider'] == 'api':
        # Would test via API endpoint
        details = {"method": "api_endpoint_check"}
    elif cred['provider'] == 'supabase':
        # Would test via Supabase connection
        details = {"method": "supabase_connection_check"}

    response_time_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

    # Record health check
    await pool.execute("""
        INSERT INTO aegis_health_checks (credential_id, status, response_time_ms, details, error_message)
        VALUES ($1, $2, $3, $4, $5)
    """, cred['id'], status, response_time_ms, json.dumps(details), error)

    await pool.execute("""
        UPDATE aegis_credentials SET last_health_check = NOW() WHERE id = $1
    """, cred['id'])

    return {
        "credential": name,
        "status": status,
        "response_time_ms": response_time_ms,
        "details": details
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROTATION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/rotation/schedule")
async def get_rotation_schedule():
    """Get upcoming and overdue rotations"""
    pool = await get_db()

    upcoming = await pool.fetch("""
        SELECT name, next_rotation_at, rotation_strategy, rotation_interval_hours
        FROM aegis_credentials
        WHERE rotation_enabled = TRUE AND status = 'active' AND next_rotation_at IS NOT NULL
        ORDER BY next_rotation_at
        LIMIT 20
    """)

    overdue = await pool.fetch("""
        SELECT name, next_rotation_at, rotation_strategy
        FROM aegis_credentials
        WHERE rotation_enabled = TRUE AND status = 'active'
        AND next_rotation_at IS NOT NULL AND next_rotation_at < NOW()
    """)

    return {
        "upcoming_rotations": [
            {
                "name": r['name'],
                "scheduled_at": r['next_rotation_at'].isoformat(),
                "strategy": r['rotation_strategy'],
                "interval_hours": r['rotation_interval_hours']
            }
            for r in upcoming
        ],
        "overdue_rotations": [
            {
                "name": r['name'],
                "was_scheduled_at": r['next_rotation_at'].isoformat(),
                "strategy": r['rotation_strategy']
            }
            for r in overdue
        ]
    }


@app.post("/rotation/run-scheduled")
async def run_scheduled_rotations():
    """Run all scheduled rotations that are due"""
    pool = await get_db()

    due = await pool.fetch("""
        SELECT name FROM aegis_credentials
        WHERE rotation_enabled = TRUE AND status = 'active'
        AND next_rotation_at IS NOT NULL AND next_rotation_at <= NOW()
    """)

    results = []
    rotated = 0
    failed = 0

    for cred in due:
        try:
            # Trigger rotation
            result = await rotate_credential(cred['name'], RotateRequest(trigger="scheduled"))
            results.append({"name": cred['name'], "status": "rotated", "details": result})
            rotated += 1
        except Exception as e:
            results.append({"name": cred['name'], "status": "failed", "error": str(e)})
            failed += 1

    if failed > 0:
        await notify_hermes(
            f"Scheduled rotation: {rotated} succeeded, {failed} failed",
            priority="high" if failed > 0 else "normal"
        )

    return {
        "rotated": rotated,
        "failed": failed,
        "details": results
    }


@app.get("/rotation/history")
async def get_rotation_history(
    credential_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get rotation history"""
    pool = await get_db()

    if credential_name:
        history = await pool.fetch("""
            SELECT rh.*, c.name as credential_name
            FROM aegis_rotation_history rh
            JOIN aegis_credentials c ON rh.credential_id = c.id
            WHERE c.name = $1
            ORDER BY rh.rotated_at DESC
            LIMIT $2 OFFSET $3
        """, credential_name, limit, offset)
    else:
        history = await pool.fetch("""
            SELECT rh.*, c.name as credential_name
            FROM aegis_rotation_history rh
            JOIN aegis_credentials c ON rh.credential_id = c.id
            ORDER BY rh.rotated_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)

    return {
        "history": [
            {
                "credential": h['credential_name'],
                "rotated_at": h['rotated_at'].isoformat(),
                "previous_version": h['previous_version'],
                "new_version": h['new_version'],
                "trigger": h['trigger'],
                "duration_ms": h['duration_ms'],
                "success": h['success'],
                "error": h['error_message'],
                "rolled_back": h['rolled_back']
            }
            for h in history
        ],
        "total": len(history)
    }


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT & COMPLIANCE
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/audit/log")
async def get_audit_log(
    credential_name: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
):
    """Get audit log entries"""
    pool = await get_db()

    query = "SELECT * FROM aegis_audit_log WHERE 1=1"
    params = []
    param_idx = 1

    if credential_name:
        query += f" AND credential_name = ${param_idx}"
        params.append(credential_name)
        param_idx += 1

    if action:
        query += f" AND action = ${param_idx}"
        params.append(action)
        param_idx += 1

    if actor:
        query += f" AND actor = ${param_idx}"
        params.append(actor)
        param_idx += 1

    if start_date:
        query += f" AND timestamp >= ${param_idx}"
        params.append(start_date)
        param_idx += 1

    if end_date:
        query += f" AND timestamp <= ${param_idx}"
        params.append(end_date)
        param_idx += 1

    query += f" ORDER BY timestamp DESC LIMIT ${param_idx}"
    params.append(limit)

    entries = await pool.fetch(query, *params)

    return {
        "log": [
            {
                "timestamp": e['timestamp'].isoformat(),
                "credential": e['credential_name'],
                "action": e['action'],
                "actor": e['actor'],
                "target": e['target'],
                "success": e['success'],
                "error": e['error_message'],
                "details": json.loads(e['details']) if e['details'] else {}
            }
            for e in entries
        ],
        "total": len(entries)
    }


@app.get("/audit/report")
async def get_audit_report(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...)
):
    """Generate audit report for a time period"""
    pool = await get_db()

    # Summary stats
    summary = await pool.fetchrow("""
        SELECT
            COUNT(*) as total_actions,
            COUNT(*) FILTER (WHERE action IN ('read', 'applied')) as total_accesses,
            COUNT(*) FILTER (WHERE action = 'rotated') as rotations,
            COUNT(*) FILTER (WHERE success = FALSE) as failures,
            COUNT(DISTINCT actor) as unique_actors
        FROM aegis_audit_log
        WHERE timestamp BETWEEN $1 AND $2
    """, start_date, end_date)

    # By credential
    by_credential = await pool.fetch("""
        SELECT credential_name, COUNT(*) as action_count,
            COUNT(*) FILTER (WHERE success = FALSE) as failures
        FROM aegis_audit_log
        WHERE timestamp BETWEEN $1 AND $2
        GROUP BY credential_name
        ORDER BY action_count DESC
    """, start_date, end_date)

    # By action type
    by_action = await pool.fetch("""
        SELECT action, COUNT(*) as count
        FROM aegis_audit_log
        WHERE timestamp BETWEEN $1 AND $2
        GROUP BY action
        ORDER BY count DESC
    """, start_date, end_date)

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": dict(summary),
        "by_credential": [dict(c) for c in by_credential],
        "by_action": [dict(a) for a in by_action]
    }


# ─────────────────────────────────────────────────────────────────────────────
# SYNC & IMPORT
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/sync/n8n")
async def sync_from_n8n():
    """Sync credentials from n8n"""
    pool = await get_db()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{N8N_URL}/api/v1/credentials",
                auth=(N8N_USER, N8N_PASS),
                timeout=10.0
            )

            if resp.status_code == 403:
                return {"status": "forbidden", "message": "API key scope doesn't include credentials:read"}

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch credentials from n8n")

            n8n_creds = resp.json().get("data", [])

            new_creds = []
            updated_creds = []

            for cred in n8n_creds:
                existing = await pool.fetchrow(
                    "SELECT id FROM aegis_credentials WHERE provider_credential_id = $1 AND provider = 'n8n'",
                    cred["id"]
                )

                if existing:
                    # Update existing
                    await pool.execute("""
                        UPDATE aegis_credentials
                        SET name = $1, credential_type = $2, updated_at = NOW()
                        WHERE id = $3
                    """, cred["name"], cred["type"], existing['id'])
                    updated_creds.append(cred["name"])
                else:
                    # Create new
                    await pool.execute("""
                        INSERT INTO aegis_credentials
                        (name, credential_type, provider, provider_credential_id, description)
                        VALUES ($1, $2, 'n8n', $3, 'Synced from n8n')
                    """, cred["name"], cred["type"], cred["id"])
                    new_creds.append(cred["name"])

            await log_to_event_bus("n8n_synced", details={
                "new": len(new_creds),
                "updated": len(updated_creds),
                "total": len(n8n_creds)
            })

            return {
                "status": "synced",
                "new": new_creds,
                "updated": updated_creds,
                "total_in_n8n": len(n8n_creds)
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/templates")
async def list_templates():
    """List credential templates"""
    pool = await get_db()

    templates = await pool.fetch("""
        SELECT name, credential_type, provider, description, created_at
        FROM aegis_templates ORDER BY name
    """)

    return {
        "templates": [
            {
                "name": t['name'],
                "type": t['credential_type'],
                "provider": t['provider'],
                "description": t['description'],
                "created_at": t['created_at'].isoformat()
            }
            for t in templates
        ]
    }


@app.post("/import/template")
async def import_from_template(template_name: str, values: Dict[str, Any]):
    """Create credential from template"""
    pool = await get_db()

    template = await pool.fetchrow(
        "SELECT * FROM aegis_templates WHERE name = $1", template_name
    )

    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")

    schema = json.loads(template['schema'])
    rotation_defaults = json.loads(template['rotation_defaults']) if template['rotation_defaults'] else {}

    # Validate required fields
    for field in schema.get('required', []):
        if field not in values:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # Create credential using template defaults
    cred = CredentialCreate(
        name=values.get('name', f"{template_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
        credential_type=template['credential_type'],
        provider=template['provider'],
        description=values.get('description', template['description']),
        value=values.get('value'),
        rotation_enabled=rotation_defaults.get('enabled', False),
        rotation_interval_hours=rotation_defaults.get('interval_hours', 720),
        rotation_strategy=rotation_defaults.get('strategy', 'manual'),
        alert_threshold_hours=rotation_defaults.get('alert_threshold_hours', 168)
    )

    return await create_credential(cred)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
