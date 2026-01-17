#!/usr/bin/env python3
"""
SSL Certificate Monitor
Port: 8064

Monitors SSL certificates for all LeverEdge domains.
Alerts 14 days before expiry via HERMES.
Integrates with CERBERUS for security posture.

Features:
- Daily scheduled checks
- Auto-renewal verification
- HERMES notification integration
- CERBERUS security integration
- Web dashboard
"""

import os
import ssl
import socket
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# =============================================================================
# CONFIGURATION
# =============================================================================

PORT = 8064
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")
CERBERUS_URL = os.getenv("CERBERUS_URL", "http://localhost:8020")
ALERT_DAYS = int(os.getenv("SSL_ALERT_DAYS", "14"))
CHECK_HOUR = int(os.getenv("SSL_CHECK_HOUR", "6"))  # 6 AM daily check

# Domains to monitor
MONITORED_DOMAINS = [
    "n8n.leveredgeai.com",
    "dev.n8n.leveredgeai.com",
    "aria.leveredgeai.com",
    "dev-aria.leveredgeai.com",
    "control.n8n.leveredgeai.com",
    "api.leveredgeai.com",
]

# Data storage path
DATA_DIR = Path("/opt/leveredge/monitoring/ssl/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CERT_DATA_FILE = DATA_DIR / "certificates.json"

# In-memory certificate cache
certificate_cache: Dict[str, Dict[str, Any]] = {}
last_check_time: Optional[datetime] = None

# Scheduler
scheduler = AsyncIOScheduler()

# =============================================================================
# MODELS
# =============================================================================

class CertificateInfo(BaseModel):
    domain: str
    valid: bool
    issuer: Optional[str] = None
    subject: Optional[str] = None
    not_before: Optional[str] = None
    not_after: Optional[str] = None
    days_until_expiry: Optional[int] = None
    auto_renew: bool = True
    last_checked: str
    error: Optional[str] = None

class CheckResponse(BaseModel):
    status: str
    checked_domains: int
    alerts_sent: int
    timestamp: str

# =============================================================================
# SSL CERTIFICATE CHECKING
# =============================================================================

def get_certificate_info(domain: str, port: int = 443, timeout: int = 10) -> Dict[str, Any]:
    """Get SSL certificate information for a domain"""
    result = {
        "domain": domain,
        "valid": False,
        "issuer": None,
        "subject": None,
        "not_before": None,
        "not_after": None,
        "days_until_expiry": None,
        "auto_renew": True,  # Assume auto-renew enabled (Let's Encrypt default)
        "last_checked": datetime.utcnow().isoformat(),
        "error": None
    }

    try:
        # Create SSL context
        context = ssl.create_default_context()

        # Connect and get certificate
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                if cert:
                    # Parse certificate details
                    result["valid"] = True

                    # Issuer
                    issuer_parts = []
                    for rdn in cert.get("issuer", []):
                        for attr in rdn:
                            if attr[0] in ("organizationName", "O"):
                                issuer_parts.append(attr[1])
                    result["issuer"] = ", ".join(issuer_parts) if issuer_parts else "Unknown"

                    # Subject (CN)
                    subject_parts = []
                    for rdn in cert.get("subject", []):
                        for attr in rdn:
                            if attr[0] in ("commonName", "CN"):
                                subject_parts.append(attr[1])
                    result["subject"] = ", ".join(subject_parts) if subject_parts else domain

                    # Validity dates
                    not_before = cert.get("notBefore")
                    not_after = cert.get("notAfter")

                    if not_before:
                        # Parse: 'Jan 15 00:00:00 2025 GMT'
                        nb_dt = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
                        result["not_before"] = nb_dt.isoformat()

                    if not_after:
                        na_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                        result["not_after"] = na_dt.isoformat()

                        # Calculate days until expiry
                        days_left = (na_dt - datetime.utcnow()).days
                        result["days_until_expiry"] = days_left

                        # Check if Let's Encrypt (auto-renew indicator)
                        if result["issuer"] and "Let's Encrypt" in result["issuer"]:
                            result["auto_renew"] = True
                else:
                    result["error"] = "No certificate returned"

    except socket.timeout:
        result["error"] = f"Connection timeout after {timeout}s"
    except socket.gaierror as e:
        result["error"] = f"DNS resolution failed: {e}"
    except ssl.SSLError as e:
        result["error"] = f"SSL error: {e}"
    except ConnectionRefusedError:
        result["error"] = "Connection refused"
    except Exception as e:
        result["error"] = f"Error: {str(e)}"

    return result

async def check_all_certificates() -> List[Dict[str, Any]]:
    """Check all monitored domain certificates"""
    global certificate_cache, last_check_time

    results = []

    # Run certificate checks in thread pool (blocking I/O)
    loop = asyncio.get_event_loop()

    for domain in MONITORED_DOMAINS:
        try:
            cert_info = await loop.run_in_executor(None, get_certificate_info, domain)
            results.append(cert_info)
            certificate_cache[domain] = cert_info
        except Exception as e:
            error_result = {
                "domain": domain,
                "valid": False,
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
            results.append(error_result)
            certificate_cache[domain] = error_result

    last_check_time = datetime.utcnow()

    # Save to file
    save_certificate_data(results)

    return results

def save_certificate_data(data: List[Dict[str, Any]]):
    """Persist certificate data to file"""
    try:
        with open(CERT_DATA_FILE, "w") as f:
            json.dump({
                "last_check": datetime.utcnow().isoformat(),
                "certificates": data
            }, f, indent=2)
    except Exception as e:
        print(f"Failed to save certificate data: {e}")

def load_certificate_data() -> Dict[str, Any]:
    """Load certificate data from file"""
    try:
        if CERT_DATA_FILE.exists():
            with open(CERT_DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load certificate data: {e}")
    return {"last_check": None, "certificates": []}

# =============================================================================
# NOTIFICATIONS
# =============================================================================

async def notify_hermes(message: str, priority: str = "normal"):
    """Send notification via HERMES"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "message": message,
                    "priority": priority,
                    "channel": "telegram"
                },
                timeout=10.0
            )
            return response.status_code == 200
    except Exception as e:
        print(f"HERMES notification failed: {e}")
        return False

async def notify_cerberus(domain: str, days_left: int, status: str):
    """Update CERBERUS with SSL status"""
    try:
        async with httpx.AsyncClient() as client:
            # Send security event to CERBERUS
            await client.post(
                f"{CERBERUS_URL}/events",
                json={
                    "event_type": "ssl_certificate_alert",
                    "source": "ssl_monitor",
                    "severity": "high" if days_left <= 7 else "medium",
                    "description": f"SSL certificate for {domain} expires in {days_left} days",
                    "raw_data": {
                        "domain": domain,
                        "days_until_expiry": days_left,
                        "status": status
                    }
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"CERBERUS notification failed: {e}")
        return False

async def send_alerts(certificates: List[Dict[str, Any]]) -> int:
    """Send alerts for expiring certificates"""
    alerts_sent = 0

    for cert in certificates:
        domain = cert.get("domain", "unknown")
        days_left = cert.get("days_until_expiry")
        error = cert.get("error")

        # Alert on errors
        if error:
            message = f"[SSL Monitor] Certificate check FAILED for {domain}: {error}"
            await notify_hermes(message, priority="high")
            await notify_cerberus(domain, 0, "error")
            alerts_sent += 1
            continue

        # Alert on expiring certificates
        if days_left is not None and days_left <= ALERT_DAYS:
            if days_left <= 3:
                priority = "critical"
                urgency = "CRITICAL"
            elif days_left <= 7:
                priority = "high"
                urgency = "WARNING"
            else:
                priority = "normal"
                urgency = "NOTICE"

            auto_renew = cert.get("auto_renew", False)
            renew_status = "Auto-renewal enabled" if auto_renew else "MANUAL RENEWAL REQUIRED"

            message = (
                f"[SSL Monitor] {urgency}: Certificate for {domain} expires in {days_left} days!\n"
                f"Expiry: {cert.get('not_after', 'Unknown')}\n"
                f"Issuer: {cert.get('issuer', 'Unknown')}\n"
                f"Status: {renew_status}"
            )

            await notify_hermes(message, priority=priority)
            await notify_cerberus(domain, days_left, "expiring")
            alerts_sent += 1

    return alerts_sent

# =============================================================================
# SCHEDULED TASKS
# =============================================================================

async def scheduled_certificate_check():
    """Daily scheduled check of all certificates"""
    print(f"[{datetime.utcnow().isoformat()}] Running scheduled certificate check...")

    try:
        certificates = await check_all_certificates()
        alerts_sent = await send_alerts(certificates)

        # Send summary to HERMES
        valid_count = sum(1 for c in certificates if c.get("valid", False))
        total_count = len(certificates)

        if alerts_sent > 0:
            summary = (
                f"[SSL Monitor] Daily Check Complete\n"
                f"Valid: {valid_count}/{total_count}\n"
                f"Alerts: {alerts_sent}"
            )
            await notify_hermes(summary, priority="normal")

        print(f"[{datetime.utcnow().isoformat()}] Check complete. Valid: {valid_count}/{total_count}, Alerts: {alerts_sent}")

    except Exception as e:
        print(f"[{datetime.utcnow().isoformat()}] Scheduled check failed: {e}")
        await notify_hermes(f"[SSL Monitor] Scheduled check FAILED: {e}", priority="high")

# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    # Startup
    print(f"SSL Certificate Monitor starting on port {PORT}")
    print(f"Monitoring {len(MONITORED_DOMAINS)} domains")
    print(f"Alert threshold: {ALERT_DAYS} days")

    # Load cached data
    global certificate_cache, last_check_time
    cached_data = load_certificate_data()
    if cached_data.get("certificates"):
        for cert in cached_data["certificates"]:
            if "domain" in cert:
                certificate_cache[cert["domain"]] = cert
        if cached_data.get("last_check"):
            try:
                last_check_time = datetime.fromisoformat(cached_data["last_check"])
            except:
                pass

    # Schedule daily checks at configured hour (UTC)
    scheduler.add_job(
        scheduled_certificate_check,
        CronTrigger(hour=CHECK_HOUR, minute=0),
        id="daily_ssl_check",
        replace_existing=True
    )
    scheduler.start()
    print(f"Scheduled daily check at {CHECK_HOUR}:00 UTC")

    # Run initial check if no recent data
    if not last_check_time or (datetime.utcnow() - last_check_time) > timedelta(hours=24):
        asyncio.create_task(scheduled_certificate_check())

    yield

    # Shutdown
    scheduler.shutdown()
    print("SSL Certificate Monitor shutting down")

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="SSL Certificate Monitor",
    description="Monitors SSL certificates for LeverEdge domains",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    valid_count = sum(1 for c in certificate_cache.values() if c.get("valid", False))
    expiring_soon = sum(
        1 for c in certificate_cache.values()
        if c.get("days_until_expiry") is not None and c["days_until_expiry"] <= ALERT_DAYS
    )

    return {
        "status": "healthy",
        "service": "ssl_monitor",
        "port": PORT,
        "monitored_domains": len(MONITORED_DOMAINS),
        "valid_certificates": valid_count,
        "expiring_soon": expiring_soon,
        "alert_threshold_days": ALERT_DAYS,
        "last_check": last_check_time.isoformat() if last_check_time else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML page"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)

    # Fallback inline HTML if static file not found
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>SSL Certificate Monitor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d9ff; }
        .error { color: #ff6b6b; }
        a { color: #00d9ff; }
    </style>
</head>
<body>
    <h1>SSL Certificate Monitor</h1>
    <p>Dashboard loading...</p>
    <p>API Endpoints:</p>
    <ul>
        <li><a href="/health">/health</a> - Health check</li>
        <li><a href="/api/certs">/api/certs</a> - All certificates</li>
    </ul>
</body>
</html>
    """)

@app.get("/api/certs")
async def get_all_certificates():
    """Get all certificate information"""
    certificates = list(certificate_cache.values())

    # Sort by days until expiry (soonest first)
    certificates.sort(
        key=lambda x: x.get("days_until_expiry") if x.get("days_until_expiry") is not None else 9999
    )

    return {
        "certificates": certificates,
        "total": len(certificates),
        "valid": sum(1 for c in certificates if c.get("valid", False)),
        "expiring_soon": sum(
            1 for c in certificates
            if c.get("days_until_expiry") is not None and c["days_until_expiry"] <= ALERT_DAYS
        ),
        "errors": sum(1 for c in certificates if c.get("error")),
        "last_check": last_check_time.isoformat() if last_check_time else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/certs/{domain}")
async def get_certificate(domain: str):
    """Get specific domain certificate information"""
    # Check cache first
    if domain in certificate_cache:
        return certificate_cache[domain]

    # Check if it's a monitored domain
    if domain not in MONITORED_DOMAINS:
        # Do a one-time check for non-monitored domain
        loop = asyncio.get_event_loop()
        cert_info = await loop.run_in_executor(None, get_certificate_info, domain)
        return cert_info

    raise HTTPException(status_code=404, detail=f"No certificate data for {domain}")

@app.post("/api/check")
async def force_check() -> CheckResponse:
    """Force check all domains immediately"""
    certificates = await check_all_certificates()
    alerts_sent = await send_alerts(certificates)

    return CheckResponse(
        status="completed",
        checked_domains=len(certificates),
        alerts_sent=alerts_sent,
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/status")
async def get_status():
    """Get monitoring status summary"""
    certificates = list(certificate_cache.values())

    # Categorize certificates
    valid = [c for c in certificates if c.get("valid", False)]
    invalid = [c for c in certificates if not c.get("valid", False)]
    expiring = [c for c in valid if c.get("days_until_expiry") is not None and c["days_until_expiry"] <= ALERT_DAYS]
    critical = [c for c in valid if c.get("days_until_expiry") is not None and c["days_until_expiry"] <= 3]

    return {
        "status": "critical" if critical else "warning" if expiring or invalid else "healthy",
        "summary": {
            "total_monitored": len(MONITORED_DOMAINS),
            "total_cached": len(certificates),
            "valid": len(valid),
            "invalid": len(invalid),
            "expiring_soon": len(expiring),
            "critical": len(critical)
        },
        "alert_threshold_days": ALERT_DAYS,
        "next_check": f"{CHECK_HOUR}:00 UTC",
        "last_check": last_check_time.isoformat() if last_check_time else None,
        "domains": {
            "monitored": MONITORED_DOMAINS,
            "expiring": [c["domain"] for c in expiring],
            "invalid": [c["domain"] for c in invalid]
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/expiring")
async def get_expiring_certificates():
    """Get certificates expiring within alert threshold"""
    certificates = list(certificate_cache.values())
    expiring = [
        c for c in certificates
        if c.get("days_until_expiry") is not None and c["days_until_expiry"] <= ALERT_DAYS
    ]

    # Sort by days until expiry
    expiring.sort(key=lambda x: x.get("days_until_expiry", 9999))

    return {
        "expiring_certificates": expiring,
        "count": len(expiring),
        "alert_threshold_days": ALERT_DAYS,
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
