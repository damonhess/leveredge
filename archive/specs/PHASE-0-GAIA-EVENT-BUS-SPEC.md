# PHASE 0: GAIA + EVENT BUS + INTERACTION CHANNELS

*Created: January 16, 2026*
*Build Priority: CRITICAL - Safety net before everything else*
*Estimated Time: 4-6 hours*

---

## Overview

Phase 0 establishes:
1. **GAIA** - The genesis system that can rebuild everything from nothing
2. **Event Bus** - The nervous system connecting all agents
3. **Interaction Channels** - Multiple ways for you to interact with the control plane
4. **Control Plane Monitoring** - Watch every single change like a hawk

---

## GAIA: The Genesis System

### Purpose

GAIA exists OUTSIDE the entire n8n/Docker ecosystem. If everything dies, GAIA can rebuild it all from backups.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   WHEN EVERYTHING IS ON FIRE:                                               │
│                                                                              │
│   1. SSH into server                                                        │
│   2. Run: /opt/leveredge/gaia/restore.sh --full --latest                   │
│   3. Wait                                                                    │
│   4. Everything is back                                                      │
│                                                                              │
│   OR via emergency Telegram (separate from n8n):                            │
│   1. Message @GaiaEmergencyBot: /restore full                               │
│   2. Confirm with 2FA code                                                  │
│   3. Wait                                                                    │
│   4. Everything is back                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### GAIA Directory Structure

```
/opt/leveredge/gaia/
├── gaia.py                    # Main GAIA logic (Python stdlib only)
├── restore.sh                 # Shell wrapper for restore operations
├── bootstrap.sh               # Full system bootstrap from bare metal
├── verify-backup.sh           # Test backup integrity
├── emergency-telegram.py      # Standalone Telegram bot (no dependencies)
├── config.yaml                # GAIA configuration
├── requirements.txt           # Minimal: pyyaml, python-telegram-bot
├── gaia.service              # Systemd service for emergency bot
├── README.md                  # Manual recovery procedures
└── tests/
    ├── test-restore-control.sh
    ├── test-restore-prod.sh
    └── test-restore-dev.sh
```

### GAIA Configuration

```yaml
# /opt/leveredge/gaia/config.yaml

gaia:
  version: "1.0.0"
  
backup_locations:
  local: /opt/leveredge/shared/backups
  # Future: offsite backup locations
  # s3: s3://leveredge-backups
  # backblaze: b2://leveredge-backups

restore_targets:
  control-plane:
    n8n:
      compose: /opt/leveredge/control-plane/n8n/docker-compose.yml
      data_dir: /opt/leveredge/control-plane/n8n/data
      database: postgresql
    agents:
      dir: /opt/leveredge/control-plane/agents
      services:
        - atlas
        - hephaestus
        - athena
        - aegis
        - chronos
        - hades
        - hermes
        - argus
        - aloy
        
  data-plane:
    prod:
      compose: /opt/leveredge/data-plane/prod/docker-compose.yml
      n8n_data: /opt/leveredge/data-plane/prod/n8n/data
      supabase_data: /opt/leveredge/data-plane/prod/supabase/data
    dev:
      compose: /opt/leveredge/data-plane/dev/docker-compose.yml
      n8n_data: /opt/leveredge/data-plane/dev/n8n/data
      supabase_data: /opt/leveredge/data-plane/dev/supabase/data

emergency_telegram:
  bot_token_file: /opt/leveredge/gaia/.telegram_token
  authorized_users:
    - YOUR_TELEGRAM_USER_ID  # Replace with actual ID
  require_2fa: true
  2fa_secret_file: /opt/leveredge/gaia/.2fa_secret

health_check:
  endpoints:
    - name: control-n8n
      url: http://localhost:5679/healthz
    - name: prod-n8n
      url: http://localhost:5678/healthz
    - name: dev-n8n
      url: http://localhost:5680/healthz
    - name: atlas
      url: http://localhost:8007/health
    - name: aegis
      url: http://localhost:8012/health
    # ... all agents
```

### GAIA Main Script

```python
#!/usr/bin/env python3
"""
GAIA - Genesis and Infrastructure Automation

The last line of defense. Can rebuild everything from nothing.
Uses ONLY Python standard library (no pip dependencies for core functions).
"""

import os
import sys
import json
import shutil
import subprocess
import tarfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - GAIA - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GAIA')

class GAIA:
    def __init__(self, config_path: str = "/opt/leveredge/gaia/config.yaml"):
        self.config = self._load_config(config_path)
        self.backup_dir = Path(self.config['backup_locations']['local'])
        
    def _load_config(self, path: str) -> dict:
        """Load config using basic parsing (no yaml dependency for core)"""
        # For core functionality, we parse yaml manually or use json fallback
        json_path = path.replace('.yaml', '.json')
        if os.path.exists(json_path):
            with open(json_path) as f:
                return json.load(f)
        # Fallback: try yaml if pyyaml available
        try:
            import yaml
            with open(path) as f:
                return yaml.safe_load(f)
        except ImportError:
            logger.error("No config found. Create config.json or install pyyaml")
            sys.exit(1)
    
    def list_backups(self, target: str = "all") -> List[Dict]:
        """List available backups"""
        backups = []
        
        if target in ["all", "control-plane"]:
            cp_dir = self.backup_dir / "control-plane"
            if cp_dir.exists():
                for backup in sorted(cp_dir.glob("*.tar.gz"), reverse=True):
                    backups.append({
                        "target": "control-plane",
                        "path": str(backup),
                        "name": backup.name,
                        "timestamp": self._parse_timestamp(backup.name),
                        "size": backup.stat().st_size
                    })
        
        if target in ["all", "prod"]:
            prod_dir = self.backup_dir / "prod"
            if prod_dir.exists():
                for backup in sorted(prod_dir.glob("*.tar.gz"), reverse=True):
                    backups.append({
                        "target": "prod",
                        "path": str(backup),
                        "name": backup.name,
                        "timestamp": self._parse_timestamp(backup.name),
                        "size": backup.stat().st_size
                    })
                    
        if target in ["all", "dev"]:
            dev_dir = self.backup_dir / "dev"
            if dev_dir.exists():
                for backup in sorted(dev_dir.glob("*.tar.gz"), reverse=True):
                    backups.append({
                        "target": "dev",
                        "path": str(backup),
                        "name": backup.name,
                        "timestamp": self._parse_timestamp(backup.name),
                        "size": backup.stat().st_size
                    })
        
        return backups
    
    def _parse_timestamp(self, filename: str) -> Optional[str]:
        """Extract timestamp from backup filename"""
        # Expected format: control-plane-2026-01-16-103000.tar.gz
        try:
            parts = filename.replace('.tar.gz', '').split('-')
            if len(parts) >= 4:
                return f"{parts[-4]}-{parts[-3]}-{parts[-2]} {parts[-1][:2]}:{parts[-1][2:4]}:{parts[-1][4:]}"
        except:
            pass
        return None
    
    def get_latest_backup(self, target: str) -> Optional[Dict]:
        """Get the most recent backup for a target"""
        backups = self.list_backups(target)
        target_backups = [b for b in backups if b['target'] == target]
        return target_backups[0] if target_backups else None
    
    def verify_backup(self, backup_path: str) -> bool:
        """Verify backup integrity"""
        logger.info(f"Verifying backup: {backup_path}")
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                # Check we can read the archive
                members = tar.getnames()
                logger.info(f"Backup contains {len(members)} files")
                
                # Check for required files based on target
                if 'docker-compose.yml' not in members and 'docker-compose.yaml' not in members:
                    logger.warning("No docker-compose file found in backup")
                
                return True
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    def stop_services(self, target: str) -> bool:
        """Stop services for a target"""
        logger.info(f"Stopping services for: {target}")
        
        compose_files = {
            "control-plane": "/opt/leveredge/control-plane/n8n/docker-compose.yml",
            "prod": "/opt/leveredge/data-plane/prod/docker-compose.yml",
            "dev": "/opt/leveredge/data-plane/dev/docker-compose.yml"
        }
        
        if target not in compose_files:
            logger.error(f"Unknown target: {target}")
            return False
        
        compose_file = compose_files[target]
        if not os.path.exists(compose_file):
            logger.warning(f"Compose file not found: {compose_file}")
            return True  # Nothing to stop
        
        try:
            subprocess.run(
                ["docker-compose", "-f", compose_file, "down"],
                check=True,
                capture_output=True
            )
            logger.info(f"Services stopped for {target}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop services: {e.stderr.decode()}")
            return False
    
    def restore_backup(self, backup_path: str, target: str) -> bool:
        """Restore a backup to target"""
        logger.info(f"Restoring {target} from {backup_path}")
        
        # Verify backup first
        if not self.verify_backup(backup_path):
            logger.error("Backup verification failed, aborting restore")
            return False
        
        # Stop services
        if not self.stop_services(target):
            logger.error("Failed to stop services, aborting restore")
            return False
        
        # Determine restore directory
        restore_dirs = {
            "control-plane": "/opt/leveredge/control-plane",
            "prod": "/opt/leveredge/data-plane/prod",
            "dev": "/opt/leveredge/data-plane/dev"
        }
        
        restore_dir = restore_dirs.get(target)
        if not restore_dir:
            logger.error(f"Unknown target: {target}")
            return False
        
        # Create temp directory for extraction
        temp_dir = f"/tmp/gaia-restore-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Extract backup
            logger.info(f"Extracting backup to {temp_dir}")
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # Backup current state (just in case)
            current_backup = f"{restore_dir}.pre-restore.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if os.path.exists(restore_dir):
                logger.info(f"Backing up current state to {current_backup}")
                shutil.move(restore_dir, current_backup)
            
            # Move extracted files to target
            logger.info(f"Moving restored files to {restore_dir}")
            extracted_contents = os.listdir(temp_dir)
            if len(extracted_contents) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_contents[0])):
                # Backup has a single root directory
                shutil.move(os.path.join(temp_dir, extracted_contents[0]), restore_dir)
            else:
                # Backup contents are at root level
                shutil.move(temp_dir, restore_dir)
            
            logger.info(f"Restore complete for {target}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            # Attempt to restore previous state
            if os.path.exists(current_backup):
                logger.info("Attempting to restore previous state...")
                if os.path.exists(restore_dir):
                    shutil.rmtree(restore_dir)
                shutil.move(current_backup, restore_dir)
            return False
        
        finally:
            # Cleanup temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def start_services(self, target: str) -> bool:
        """Start services for a target"""
        logger.info(f"Starting services for: {target}")
        
        compose_files = {
            "control-plane": "/opt/leveredge/control-plane/n8n/docker-compose.yml",
            "prod": "/opt/leveredge/data-plane/prod/docker-compose.yml",
            "dev": "/opt/leveredge/data-plane/dev/docker-compose.yml"
        }
        
        if target not in compose_files:
            logger.error(f"Unknown target: {target}")
            return False
        
        compose_file = compose_files[target]
        
        try:
            subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d"],
                check=True,
                capture_output=True
            )
            logger.info(f"Services started for {target}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start services: {e.stderr.decode()}")
            return False
    
    def start_agents(self) -> bool:
        """Start all FastAPI agents"""
        logger.info("Starting FastAPI agents...")
        
        agents = ['atlas', 'hephaestus', 'athena', 'aegis', 'chronos', 
                  'hades', 'hermes', 'argus', 'aloy']
        
        success = True
        for agent in agents:
            try:
                subprocess.run(
                    ["systemctl", "--user", "start", f"{agent}.service"],
                    check=True,
                    capture_output=True
                )
                logger.info(f"Started {agent}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to start {agent}: {e}")
                success = False
        
        return success
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all services"""
        import urllib.request
        
        results = {}
        
        for endpoint in self.config.get('health_check', {}).get('endpoints', []):
            name = endpoint['name']
            url = endpoint['url']
            
            try:
                req = urllib.request.Request(url, method='GET')
                with urllib.request.urlopen(req, timeout=5) as response:
                    results[name] = response.status == 200
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                results[name] = False
        
        return results
    
    def full_restore(self, use_latest: bool = True, backup_path: Optional[str] = None) -> bool:
        """Full system restore"""
        logger.info("=" * 60)
        logger.info("GAIA FULL SYSTEM RESTORE")
        logger.info("=" * 60)
        
        targets = ["control-plane", "prod", "dev"]
        
        for target in targets:
            logger.info(f"\n{'='*40}")
            logger.info(f"Restoring: {target}")
            logger.info(f"{'='*40}")
            
            if use_latest:
                backup = self.get_latest_backup(target)
                if not backup:
                    logger.error(f"No backup found for {target}")
                    continue
                backup_path = backup['path']
            
            if not self.restore_backup(backup_path, target):
                logger.error(f"Failed to restore {target}")
                return False
            
            if not self.start_services(target):
                logger.error(f"Failed to start services for {target}")
                return False
        
        # Start agents
        if not self.start_agents():
            logger.warning("Some agents failed to start")
        
        # Health check
        logger.info("\nRunning health checks...")
        health = self.health_check()
        
        logger.info("\nHealth Check Results:")
        for name, status in health.items():
            logger.info(f"  {name}: {'✅' if status else '❌'}")
        
        all_healthy = all(health.values())
        
        if all_healthy:
            logger.info("\n✅ FULL RESTORE COMPLETE - All systems healthy")
        else:
            logger.warning("\n⚠️ RESTORE COMPLETE - Some systems unhealthy")
        
        return all_healthy


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GAIA - Genesis and Infrastructure Automation')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List backups
    list_parser = subparsers.add_parser('list', help='List available backups')
    list_parser.add_argument('--target', choices=['all', 'control-plane', 'prod', 'dev'], 
                            default='all', help='Target to list backups for')
    
    # Verify backup
    verify_parser = subparsers.add_parser('verify', help='Verify backup integrity')
    verify_parser.add_argument('backup_path', help='Path to backup file')
    
    # Restore
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('target', choices=['control-plane', 'prod', 'dev', 'full'],
                               help='Target to restore')
    restore_parser.add_argument('--backup', help='Specific backup path (default: latest)')
    restore_parser.add_argument('--yes', '-y', action='store_true', 
                               help='Skip confirmation')
    
    # Health check
    health_parser = subparsers.add_parser('health', help='Check system health')
    
    args = parser.parse_args()
    
    gaia = GAIA()
    
    if args.command == 'list':
        backups = gaia.list_backups(args.target)
        if not backups:
            print("No backups found")
            return
        
        print(f"\n{'Target':<15} {'Timestamp':<20} {'Size':<12} {'Path'}")
        print("-" * 80)
        for b in backups:
            size = f"{b['size'] / 1024 / 1024:.1f} MB"
            print(f"{b['target']:<15} {b['timestamp'] or 'Unknown':<20} {size:<12} {b['name']}")
    
    elif args.command == 'verify':
        if gaia.verify_backup(args.backup_path):
            print("✅ Backup is valid")
        else:
            print("❌ Backup verification failed")
            sys.exit(1)
    
    elif args.command == 'restore':
        if args.target == 'full':
            if not args.yes:
                print("\n⚠️  WARNING: This will restore the ENTIRE system!")
                print("All current data will be replaced with backup data.\n")
                confirm = input("Type 'RESTORE EVERYTHING' to confirm: ")
                if confirm != 'RESTORE EVERYTHING':
                    print("Aborted.")
                    sys.exit(0)
            
            success = gaia.full_restore(use_latest=not args.backup, backup_path=args.backup)
            sys.exit(0 if success else 1)
        else:
            if not args.yes:
                print(f"\n⚠️  WARNING: This will restore {args.target}!")
                confirm = input(f"Type 'RESTORE {args.target.upper()}' to confirm: ")
                if confirm != f'RESTORE {args.target.upper()}':
                    print("Aborted.")
                    sys.exit(0)
            
            if args.backup:
                backup_path = args.backup
            else:
                backup = gaia.get_latest_backup(args.target)
                if not backup:
                    print(f"No backup found for {args.target}")
                    sys.exit(1)
                backup_path = backup['path']
            
            if gaia.restore_backup(backup_path, args.target):
                gaia.start_services(args.target)
                if args.target == 'control-plane':
                    gaia.start_agents()
                print("✅ Restore complete")
            else:
                print("❌ Restore failed")
                sys.exit(1)
    
    elif args.command == 'health':
        health = gaia.health_check()
        print("\nSystem Health:")
        print("-" * 40)
        for name, status in health.items():
            print(f"  {name}: {'✅ Healthy' if status else '❌ Down'}")
        
        if all(health.values()):
            print("\n✅ All systems healthy")
        else:
            print("\n⚠️ Some systems unhealthy")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
```

### GAIA Shell Wrapper

```bash
#!/bin/bash
# /opt/leveredge/gaia/restore.sh
# Shell wrapper for GAIA operations

set -e

GAIA_DIR="/opt/leveredge/gaia"
GAIA_PY="$GAIA_DIR/gaia.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${GREEN}"
    echo "  ██████╗  █████╗ ██╗ █████╗ "
    echo " ██╔════╝ ██╔══██╗██║██╔══██╗"
    echo " ██║  ███╗███████║██║███████║"
    echo " ██║   ██║██╔══██║██║██╔══██║"
    echo " ╚██████╔╝██║  ██║██║██║  ██║"
    echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo " Genesis and Infrastructure Automation"
    echo ""
}

usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list [target]           List available backups"
    echo "  verify <backup_path>    Verify backup integrity"
    echo "  restore <target>        Restore from backup"
    echo "  health                  Check system health"
    echo "  full                    Full system restore (DANGEROUS)"
    echo ""
    echo "Targets: control-plane, prod, dev, full"
    echo ""
    echo "Options:"
    echo "  --backup <path>    Use specific backup file"
    echo "  --yes, -y          Skip confirmation prompts"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 restore control-plane --yes"
    echo "  $0 full --yes"
}

case "$1" in
    list)
        python3 "$GAIA_PY" list ${2:+--target $2}
        ;;
    verify)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: backup path required${NC}"
            exit 1
        fi
        python3 "$GAIA_PY" verify "$2"
        ;;
    restore)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: target required${NC}"
            exit 1
        fi
        print_banner
        shift
        python3 "$GAIA_PY" restore "$@"
        ;;
    health)
        python3 "$GAIA_PY" health
        ;;
    full)
        print_banner
        echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║           FULL SYSTEM RESTORE                             ║${NC}"
        echo -e "${RED}║                                                           ║${NC}"
        echo -e "${RED}║  This will restore EVERYTHING:                            ║${NC}"
        echo -e "${RED}║  - Control plane n8n                                      ║${NC}"
        echo -e "${RED}║  - All FastAPI agents                                     ║${NC}"
        echo -e "${RED}║  - Production environment                                 ║${NC}"
        echo -e "${RED}║  - Development environment                                ║${NC}"
        echo -e "${RED}║                                                           ║${NC}"
        echo -e "${RED}║  ALL CURRENT DATA WILL BE REPLACED                        ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
        echo ""
        shift
        python3 "$GAIA_PY" restore full "$@"
        ;;
    *)
        print_banner
        usage
        exit 1
        ;;
esac
```

### GAIA Emergency Telegram Bot

```python
#!/usr/bin/env python3
"""
GAIA Emergency Telegram Bot

Standalone bot that can trigger GAIA restores remotely.
Requires 2FA confirmation for any destructive action.

This bot runs independently of n8n and all other services.
"""

import os
import sys
import logging
import subprocess
import pyotp
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configuration
CONFIG_DIR = Path("/opt/leveredge/gaia")
TOKEN_FILE = CONFIG_DIR / ".telegram_token"
SECRET_FILE = CONFIG_DIR / ".2fa_secret"
AUTHORIZED_USERS_FILE = CONFIG_DIR / ".authorized_users"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - GAIA-BOT - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/gaia-emergency-bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GAIA-BOT')

# Load configuration
def load_config():
    config = {}
    
    if TOKEN_FILE.exists():
        config['token'] = TOKEN_FILE.read_text().strip()
    else:
        logger.error(f"Token file not found: {TOKEN_FILE}")
        sys.exit(1)
    
    if SECRET_FILE.exists():
        config['2fa_secret'] = SECRET_FILE.read_text().strip()
    else:
        # Generate new 2FA secret
        secret = pyotp.random_base32()
        SECRET_FILE.write_text(secret)
        SECRET_FILE.chmod(0o600)
        config['2fa_secret'] = secret
        logger.info(f"Generated new 2FA secret. Add to authenticator app:")
        logger.info(f"Secret: {secret}")
    
    if AUTHORIZED_USERS_FILE.exists():
        config['authorized_users'] = [
            int(uid.strip()) 
            for uid in AUTHORIZED_USERS_FILE.read_text().strip().split('\n')
            if uid.strip()
        ]
    else:
        logger.error(f"Authorized users file not found: {AUTHORIZED_USERS_FILE}")
        sys.exit(1)
    
    return config

CONFIG = load_config()
TOTP = pyotp.TOTP(CONFIG['2fa_secret'])

# Pending operations (waiting for 2FA)
pending_operations = {}

def is_authorized(user_id: int) -> bool:
    return user_id in CONFIG['authorized_users']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized. This incident has been logged.")
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return
    
    await update.message.reply_text(
        "🌍 *GAIA Emergency Control*\n\n"
        "Available commands:\n"
        "/status - System health check\n"
        "/list - List available backups\n"
        "/restore <target> - Restore (requires 2FA)\n"
        "/fullrestore - Full system restore (requires 2FA)\n\n"
        "Targets: control-plane, prod, dev",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check system health"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    await update.message.reply_text("🔍 Checking system health...")
    
    try:
        result = subprocess.run(
            ['python3', '/opt/leveredge/gaia/gaia.py', 'health'],
            capture_output=True,
            text=True,
            timeout=30
        )
        await update.message.reply_text(f"```\n{result.stdout}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def list_backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available backups"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    try:
        result = subprocess.run(
            ['python3', '/opt/leveredge/gaia/gaia.py', 'list'],
            capture_output=True,
            text=True,
            timeout=30
        )
        await update.message.reply_text(f"```\n{result.stdout}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate restore (requires 2FA)"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /restore <target>\n"
            "Targets: control-plane, prod, dev"
        )
        return
    
    target = context.args[0]
    if target not in ['control-plane', 'prod', 'dev']:
        await update.message.reply_text("Invalid target. Use: control-plane, prod, dev")
        return
    
    # Store pending operation
    pending_operations[user_id] = {
        'action': 'restore',
        'target': target
    }
    
    await update.message.reply_text(
        f"⚠️ *Restore {target}*\n\n"
        f"This will restore {target} from the latest backup.\n"
        f"Current data will be replaced.\n\n"
        f"Enter your 2FA code to confirm:",
        parse_mode='Markdown'
    )

async def fullrestore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate full system restore (requires 2FA)"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    pending_operations[user_id] = {
        'action': 'fullrestore'
    }
    
    await update.message.reply_text(
        "🚨 *FULL SYSTEM RESTORE*\n\n"
        "This will restore EVERYTHING:\n"
        "- Control plane\n"
        "- Production environment\n"
        "- Development environment\n\n"
        "⚠️ ALL CURRENT DATA WILL BE REPLACED\n\n"
        "Enter your 2FA code to confirm:",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages (for 2FA codes)"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        return
    
    if user_id not in pending_operations:
        return
    
    code = update.message.text.strip()
    
    # Verify 2FA
    if not TOTP.verify(code):
        await update.message.reply_text("❌ Invalid 2FA code. Try again or /cancel")
        return
    
    operation = pending_operations.pop(user_id)
    
    if operation['action'] == 'restore':
        target = operation['target']
        await update.message.reply_text(f"🔄 Starting restore of {target}...")
        
        try:
            result = subprocess.run(
                ['python3', '/opt/leveredge/gaia/gaia.py', 'restore', target, '--yes'],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                await update.message.reply_text(f"✅ Restore of {target} complete!")
            else:
                await update.message.reply_text(f"❌ Restore failed:\n```\n{result.stderr}\n```", parse_mode='Markdown')
                
        except subprocess.TimeoutExpired:
            await update.message.reply_text("❌ Restore timed out")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif operation['action'] == 'fullrestore':
        await update.message.reply_text("🔄 Starting FULL SYSTEM RESTORE...")
        await update.message.reply_text("This may take several minutes...")
        
        try:
            result = subprocess.run(
                ['python3', '/opt/leveredge/gaia/gaia.py', 'restore', 'full', '--yes'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                await update.message.reply_text("✅ FULL SYSTEM RESTORE complete!")
            else:
                await update.message.reply_text(f"❌ Restore failed:\n```\n{result.stderr}\n```", parse_mode='Markdown')
                
        except subprocess.TimeoutExpired:
            await update.message.reply_text("❌ Restore timed out")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending operation"""
    user_id = update.effective_user.id
    
    if user_id in pending_operations:
        del pending_operations[user_id]
        await update.message.reply_text("Operation cancelled.")
    else:
        await update.message.reply_text("No pending operation.")

def main():
    """Run the bot"""
    logger.info("Starting GAIA Emergency Bot...")
    
    application = Application.builder().token(CONFIG['token']).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("list", list_backups))
    application.add_handler(CommandHandler("restore", restore))
    application.add_handler(CommandHandler("fullrestore", fullrestore))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Handle text messages (for 2FA codes)
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

---

## Event Bus

### Event Bus Schema

```sql
-- /opt/leveredge/control-plane/event-bus-schema.sql
-- 
-- The nervous system of the agent fleet.
-- All agent actions are published here.
-- Relevant agents subscribe and react.

-- Main events table
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  timestamp TEXT DEFAULT (datetime('now')),
  
  -- Source
  source_agent TEXT NOT NULL,
  source_workflow_id TEXT,
  source_execution_id TEXT,
  
  -- Action
  action TEXT NOT NULL,
  target TEXT,
  details TEXT,  -- JSON string
  
  -- Human interaction
  requires_human INTEGER DEFAULT 0,
  human_question TEXT,
  human_options TEXT,  -- JSON array string
  human_timeout_minutes INTEGER,
  human_fallback TEXT,
  human_response TEXT,
  human_responded_at TEXT,
  human_notified INTEGER DEFAULT 0,
  
  -- Subscriptions
  subscribed_agents TEXT,  -- JSON array string
  acknowledged_by TEXT DEFAULT '{}',  -- JSON object string
  
  -- Status
  status TEXT DEFAULT 'pending',  -- pending, acknowledged, completed, failed, timeout
  
  -- Audit
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_agent);
CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_requires_human ON events(requires_human);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);

-- Agent subscriptions table (what each agent listens for)
CREATE TABLE IF NOT EXISTS agent_subscriptions (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  agent_name TEXT NOT NULL,
  action_pattern TEXT NOT NULL,  -- Can use wildcards: workflow_*, *_failed
  priority INTEGER DEFAULT 5,    -- 1 = highest, 10 = lowest
  enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Default subscriptions
INSERT OR IGNORE INTO agent_subscriptions (agent_name, action_pattern, priority) VALUES
  -- AEGIS watches for credential-related events
  ('AEGIS', 'workflow_created', 1),
  ('AEGIS', 'workflow_modified', 1),
  ('AEGIS', 'container_deployed', 1),
  ('AEGIS', 'credential_*', 1),
  ('AEGIS', 'config_changed', 2),
  
  -- CHRONOS watches for deployment events (backup before)
  ('CHRONOS', 'build_started', 1),
  ('CHRONOS', 'deploy_started', 1),
  ('CHRONOS', 'upgrade_started', 1),
  ('CHRONOS', 'config_changed', 2),
  
  -- HADES watches for failures (prepare rollback)
  ('HADES', '*_failed', 1),
  ('HADES', 'audit_failed', 1),
  ('HADES', 'health_check_failed', 1),
  
  -- ALOY watches for deployments (audit after)
  ('ALOY', 'workflow_deployed', 1),
  ('ALOY', 'container_started', 1),
  ('ALOY', 'restore_completed', 1),
  ('ALOY', 'config_changed', 2),
  
  -- ATHENA watches everything (documents)
  ('ATHENA', '*', 10),
  
  -- ARIA watches everything (stays informed)
  ('ARIA', '*', 10),
  ('ARIA', 'human_input_required', 1),
  
  -- HERMES watches for notification-worthy events
  ('HERMES', '*_completed', 5),
  ('HERMES', '*_failed', 1),
  ('HERMES', 'human_input_required', 1),
  ('HERMES', 'credential_expiring', 1),
  ('HERMES', 'backup_completed', 5),
  
  -- ARGUS watches for health events
  ('ARGUS', 'health_*', 1),
  ('ARGUS', '*_started', 5),
  ('ARGUS', '*_completed', 5);

-- View for pending human requests
CREATE VIEW IF NOT EXISTS pending_human_requests AS
SELECT 
  id,
  source_agent,
  action,
  human_question,
  human_options,
  human_timeout_minutes,
  human_fallback,
  timestamp,
  datetime(timestamp, '+' || human_timeout_minutes || ' minutes') as timeout_at
FROM events
WHERE requires_human = 1 
  AND human_response IS NULL
  AND status = 'pending';

-- View for recent events
CREATE VIEW IF NOT EXISTS recent_events AS
SELECT 
  id,
  timestamp,
  source_agent,
  action,
  target,
  status,
  requires_human,
  human_response
FROM events
ORDER BY timestamp DESC
LIMIT 100;
```

### Event Bus API (FastAPI)

```python
#!/usr/bin/env python3
"""
Event Bus API

Lightweight FastAPI service for the event bus.
All agents publish/subscribe through this service.

Location: /opt/leveredge/control-plane/event-bus/event_bus.py
Port: 8099
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import contextmanager

app = FastAPI(title="Event Bus", version="1.0.0")

DB_PATH = Path("/opt/leveredge/control-plane/event-bus/events.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Models
class EventCreate(BaseModel):
    source_agent: str
    action: str
    target: Optional[str] = None
    details: Optional[dict] = None
    source_workflow_id: Optional[str] = None
    source_execution_id: Optional[str] = None
    requires_human: bool = False
    human_question: Optional[str] = None
    human_options: Optional[List[str]] = None
    human_timeout_minutes: Optional[int] = None
    human_fallback: Optional[str] = None

class HumanResponse(BaseModel):
    response: str
    responder: str = "human"

# Endpoints
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "event-bus", "port": 8099}

@app.post("/events")
async def create_event(event: EventCreate):
    """Publish an event to the bus"""
    
    # Determine subscribed agents
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get matching subscriptions
        cursor.execute("""
            SELECT DISTINCT agent_name 
            FROM agent_subscriptions 
            WHERE enabled = 1
            AND (
                action_pattern = ? 
                OR action_pattern = '*'
                OR (action_pattern LIKE '%*' AND ? LIKE REPLACE(action_pattern, '*', '%'))
                OR (action_pattern LIKE '*%' AND ? LIKE REPLACE(action_pattern, '*', '%'))
            )
        """, (event.action, event.action, event.action))
        
        subscribed = [row['agent_name'] for row in cursor.fetchall()]
        
        # Insert event
        cursor.execute("""
            INSERT INTO events (
                source_agent, action, target, details,
                source_workflow_id, source_execution_id,
                requires_human, human_question, human_options,
                human_timeout_minutes, human_fallback,
                subscribed_agents, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.source_agent,
            event.action,
            event.target,
            json.dumps(event.details) if event.details else None,
            event.source_workflow_id,
            event.source_execution_id,
            1 if event.requires_human else 0,
            event.human_question,
            json.dumps(event.human_options) if event.human_options else None,
            event.human_timeout_minutes,
            event.human_fallback,
            json.dumps(subscribed),
            'pending'
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        
        # Get the created event
        cursor.execute("SELECT * FROM events WHERE rowid = ?", (event_id,))
        row = cursor.fetchone()
        
        return {
            "id": row['id'],
            "status": "created",
            "subscribed_agents": subscribed
        }

@app.get("/events")
async def list_events(
    limit: int = 50,
    source_agent: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None
):
    """List recent events"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if source_agent:
            query += " AND source_agent = ?"
            params.append(source_agent)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            # Parse JSON fields
            if event.get('details'):
                event['details'] = json.loads(event['details'])
            if event.get('subscribed_agents'):
                event['subscribed_agents'] = json.loads(event['subscribed_agents'])
            if event.get('human_options'):
                event['human_options'] = json.loads(event['human_options'])
            if event.get('acknowledged_by'):
                event['acknowledged_by'] = json.loads(event['acknowledged_by'])
            events.append(event)
        
        return {"events": events, "count": len(events)}

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get a specific event"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event = dict(row)
        if event.get('details'):
            event['details'] = json.loads(event['details'])
        if event.get('subscribed_agents'):
            event['subscribed_agents'] = json.loads(event['subscribed_agents'])
        
        return event

@app.post("/events/{event_id}/acknowledge")
async def acknowledge_event(event_id: str, agent: str):
    """Mark event as acknowledged by an agent"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT acknowledged_by FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        
        acknowledged = json.loads(row['acknowledged_by'] or '{}')
        acknowledged[agent] = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE events 
            SET acknowledged_by = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (json.dumps(acknowledged), event_id))
        
        conn.commit()
        
        return {"status": "acknowledged", "agent": agent}

@app.post("/events/{event_id}/respond")
async def respond_to_event(event_id: str, response: HumanResponse):
    """Respond to an event that requires human input"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        
        if not row['requires_human']:
            raise HTTPException(status_code=400, detail="Event does not require human response")
        
        cursor.execute("""
            UPDATE events 
            SET human_response = ?, 
                human_responded_at = datetime('now'),
                status = 'completed',
                updated_at = datetime('now')
            WHERE id = ?
        """, (response.response, event_id))
        
        conn.commit()
        
        return {"status": "responded", "response": response.response}

@app.get("/events/pending/human")
async def get_pending_human_events():
    """Get events waiting for human response"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_human_requests")
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event.get('human_options'):
                event['human_options'] = json.loads(event['human_options'])
            events.append(event)
        
        return {"pending": events, "count": len(events)}

@app.get("/agents/{agent}/events")
async def get_agent_events(agent: str, limit: int = 20, unacknowledged_only: bool = False):
    """Get events for a specific agent"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if unacknowledged_only:
            cursor.execute("""
                SELECT * FROM events 
                WHERE subscribed_agents LIKE ?
                AND NOT (acknowledged_by LIKE ?)
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (f'%"{agent}"%', f'%"{agent}"%', limit))
        else:
            cursor.execute("""
                SELECT * FROM events 
                WHERE subscribed_agents LIKE ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (f'%"{agent}"%', limit))
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event.get('details'):
                event['details'] = json.loads(event['details'])
            events.append(event)
        
        return {"agent": agent, "events": events, "count": len(events)}
```

---

## Interaction Channels

### Channel Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           INTERACTION CHANNELS                                           │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                                  │    │
│  │   1. CONTROL PLANE N8N (Primary)                                                │    │
│  │      URL: control.n8n.leveredgeai.com                                           │    │
│  │      Access: Cloudflare Access (your email)                                     │    │
│  │                                                                                  │    │
│  │      Features:                                                                   │    │
│  │      ├─ Direct workflow editing                                                 │    │
│  │      ├─ Chat triggers for each agent                                            │    │
│  │      ├─ Execution history (SEE everything)                                      │    │
│  │      ├─ n8n Project Agent (helps you build)                                     │    │
│  │      └─ n8n Workflow Agent (helps you edit)                                     │    │
│  │                                                                                  │    │
│  │      Every interaction is logged to Event Bus                                   │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                                  │    │
│  │   2. TELEGRAM (Mobile/Quick Access)                                             │    │
│  │                                                                                  │    │
│  │      @LeveredgeControlBot                                                        │    │
│  │      ├─ Routes to ATLAS                                                         │    │
│  │      ├─ Quick status checks                                                     │    │
│  │      ├─ Approve/reject pending requests                                         │    │
│  │      └─ Trigger backups/restores                                                │    │
│  │                                                                                  │    │
│  │      @GaiaEmergencyBot                                                          │    │
│  │      ├─ Standalone (works when n8n is down)                                     │    │
│  │      ├─ Emergency restores with 2FA                                             │    │
│  │      └─ System health checks                                                    │    │
│  │                                                                                  │    │
│  │      ARIA (via existing Telegram)                                               │    │
│  │      ├─ Notifies you of agent events                                            │    │
│  │      ├─ Relays human input requests                                             │    │
│  │      └─ "What's happening with X?"                                              │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                                  │    │
│  │   3. WEB DASHBOARDS (Specific Functions)                                        │    │
│  │                                                                                  │    │
│  │      aegis.leveredgeai.com    - Manage credentials                              │    │
│  │      chronos.leveredgeai.com  - Manage backups                                  │    │
│  │      hades.leveredgeai.com    - Manage rollbacks                                │    │
│  │      aloy.leveredgeai.com     - View audit history                              │    │
│  │      grafana.leveredgeai.com  - System monitoring                               │    │
│  │                                                                                  │    │
│  │      All behind Cloudflare Access                                               │    │
│  │      All interactions logged to Event Bus                                       │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                                  │    │
│  │   4. CLI (Server-side/Emergency)                                                │    │
│  │                                                                                  │    │
│  │      SSH into server, then:                                                     │    │
│  │      ├─ gaia restore full              # Full system restore                    │    │
│  │      ├─ atlas "check system health"    # Talk to ATLAS                          │    │
│  │      ├─ aegis list                     # List credentials                       │    │
│  │      ├─ chronos list                   # List backups                           │    │
│  │      └─ hades rollback dev             # Rollback dev environment               │    │
│  │                                                                                  │    │
│  │      For when everything else is down                                           │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                                  │    │
│  │   5. MCP (Programmatic Access)                                                  │    │
│  │                                                                                  │    │
│  │      Instance-level MCP on control n8n                                          │    │
│  │      ├─ ARIA can call control plane agents                                      │    │
│  │      ├─ Agents can call each other                                              │    │
│  │      └─ External systems can integrate                                          │    │
│  │                                                                                  │    │
│  │      MCP Trigger (Server mode)                                                  │    │
│  │      ├─ Expose agents as MCP tools                                              │    │
│  │      └─ Claude Desktop can call them                                            │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Telegram Control Bot

```python
#!/usr/bin/env python3
"""
Leveredge Control Bot

Routes commands to ATLAS through n8n webhook.
"""

import os
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get('TELEGRAM_CONTROL_BOT_TOKEN')
ATLAS_WEBHOOK = "https://control.n8n.leveredgeai.com/webhook/atlas"
AUTHORIZED_USERS = [YOUR_TELEGRAM_ID]  # Replace

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    await update.message.reply_text(
        "🏛️ *Leveredge Control*\n\n"
        "Commands:\n"
        "/status - System health\n"
        "/agents - Agent status\n"
        "/pending - Pending human requests\n"
        "/backup [target] - Trigger backup\n"
        "/events - Recent events\n\n"
        "Or just type a message to talk to ATLAS.",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.post(ATLAS_WEBHOOK, json={
            "command": "status",
            "source": "telegram"
        })
        result = response.json()
        await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')

async def agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.post(ATLAS_WEBHOOK, json={
            "command": "agent_status",
            "source": "telegram"
        })
        result = response.json()
        await update.message.reply_text(f"```\n{result}\n```", parse_mode='Markdown')

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8099/events/pending/human")
        result = response.json()
        
        if not result['pending']:
            await update.message.reply_text("No pending requests.")
            return
        
        for event in result['pending']:
            msg = (
                f"🔔 *{event['source_agent']}*\n"
                f"{event['human_question']}\n\n"
                f"Options: {', '.join(event['human_options'] or [])}\n"
                f"Timeout: {event['timeout_at']}\n"
                f"Reply: /respond {event['id']} <answer>"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')

async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /respond <event_id> <response>")
        return
    
    event_id = context.args[0]
    response = ' '.join(context.args[1:])
    
    async with httpx.AsyncClient() as client:
        result = await client.post(
            f"http://localhost:8099/events/{event_id}/respond",
            json={"response": response}
        )
        
        if result.status_code == 200:
            await update.message.reply_text(f"✅ Response recorded: {response}")
        else:
            await update.message.reply_text(f"❌ Error: {result.text}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward messages to ATLAS"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    message = update.message.text
    
    async with httpx.AsyncClient() as client:
        response = await client.post(ATLAS_WEBHOOK, json={
            "message": message,
            "source": "telegram",
            "user": update.effective_user.username
        })
        result = response.json()
        await update.message.reply_text(result.get('response', 'No response'))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("agents", agents))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("respond", respond))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()
```

---

## Control Plane Monitoring

### Every Interaction Is Logged

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     CONTROL PLANE MONITORING                                             │
│                                                                                          │
│   WATCHED LIKE A HAWK:                                                                  │
│                                                                                          │
│   1. Every workflow execution                                                           │
│      └─ Event: { action: "workflow_executed", details: { ... } }                       │
│                                                                                          │
│   2. Every workflow modification                                                        │
│      └─ Event: { action: "workflow_modified", details: { old: ..., new: ... } }        │
│                                                                                          │
│   3. Every credential access                                                            │
│      └─ Event: { action: "credential_accessed", details: { ... } }                     │
│                                                                                          │
│   4. Every chat message (to any agent)                                                  │
│      └─ Event: { action: "chat_received", details: { ... } }                           │
│                                                                                          │
│   5. Every webhook call                                                                 │
│      └─ Event: { action: "webhook_received", details: { ... } }                        │
│                                                                                          │
│   6. Every login attempt                                                                │
│      └─ Event: { action: "login_attempt", details: { ... } }                           │
│                                                                                          │
│   7. Every configuration change                                                         │
│      └─ Event: { action: "config_changed", details: { ... } }                          │
│                                                                                          │
│   ALERTS:                                                                               │
│   - ARGUS monitors all events in real-time                                             │
│   - Anomaly detection: unusual patterns                                                │
│   - HERMES sends Telegram on any suspicious activity                                   │
│   - Daily summary sent to ARIA for your review                                         │
│                                                                                          │
│   AUDIT TRAIL:                                                                          │
│   - ALOY maintains complete history                                                    │
│   - ATHENA documents all changes                                                       │
│   - CHRONOS backs up event database                                                    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### n8n Audit Workflow

```json
{
  "name": "ARGUS - Control Plane Monitor",
  "nodes": [
    {
      "name": "On Any Workflow Execution",
      "type": "n8n-nodes-base.n8nTrigger",
      "parameters": {
        "events": ["workflow.completed", "workflow.failed"]
      }
    },
    {
      "name": "Log to Event Bus",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8099/events",
        "body": {
          "source_agent": "ARGUS",
          "action": "workflow_executed",
          "target": "={{ $json.workflowName }}",
          "details": {
            "execution_id": "={{ $json.executionId }}",
            "status": "={{ $json.status }}",
            "started_at": "={{ $json.startedAt }}",
            "finished_at": "={{ $json.finishedAt }}"
          }
        }
      }
    }
  ]
}
```

---

## Build Commands for Claude Code

```
## PHASE 0: GAIA + EVENT BUS + INTERACTION CHANNELS

Execute in this exact order:

### Step 1: Create Base Directory Structure

```bash
sudo mkdir -p /opt/leveredge/{gaia,control-plane,data-plane,shared,monitoring}
sudo mkdir -p /opt/leveredge/control-plane/{n8n,agents,workflows,dashboards,docs,event-bus}
sudo mkdir -p /opt/leveredge/data-plane/{prod,dev}
sudo mkdir -p /opt/leveredge/shared/{scripts,templates,backups,credentials}
sudo mkdir -p /opt/leveredge/shared/backups/{control-plane,prod,dev}/{hourly,daily,weekly,monthly}
sudo mkdir -p /opt/leveredge/monitoring/{prometheus,grafana}

sudo chown -R damon:damon /opt/leveredge
chmod 755 /opt/leveredge
```

### Step 2: Create GAIA

Create all files in /opt/leveredge/gaia/:
- gaia.py (main script from spec)
- restore.sh (shell wrapper from spec)
- emergency-telegram.py (telegram bot from spec)
- config.yaml (configuration)
- requirements.txt: pyyaml, python-telegram-bot, pyotp

```bash
cd /opt/leveredge/gaia
pip install -r requirements.txt --break-system-packages

# Create token files (placeholder - will fill in manually)
touch .telegram_token .2fa_secret .authorized_users
chmod 600 .telegram_token .2fa_secret .authorized_users

# Make scripts executable
chmod +x gaia.py restore.sh emergency-telegram.py
```

### Step 3: Create Event Bus

Create /opt/leveredge/control-plane/event-bus/:
- event_bus.py (FastAPI from spec)
- events.db (SQLite database)
- event-bus.service (systemd)

```bash
cd /opt/leveredge/control-plane/event-bus

# Initialize database
sqlite3 events.db < event-bus-schema.sql

# Create systemd service
cat > ~/.config/systemd/user/event-bus.service << 'EOF'
[Unit]
Description=Event Bus API
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/leveredge/control-plane/event-bus
ExecStart=/home/damon/.local/bin/uvicorn event_bus:app --host 0.0.0.0 --port 8099
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable event-bus
systemctl --user start event-bus
```

### Step 4: Create GAIA Service

```bash
cat > ~/.config/systemd/user/gaia-emergency.service << 'EOF'
[Unit]
Description=GAIA Emergency Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/leveredge/gaia
ExecStart=/usr/bin/python3 /opt/leveredge/gaia/emergency-telegram.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable gaia-emergency
# Don't start yet - need to configure tokens first
```

### Step 5: Verify Everything

```bash
# Test GAIA
/opt/leveredge/gaia/restore.sh list

# Test Event Bus
curl http://localhost:8099/health

# Test Event Bus publish
curl -X POST http://localhost:8099/events \
  -H "Content-Type: application/json" \
  -d '{"source_agent": "TEST", "action": "test_event", "target": "phase0"}'

# Test Event Bus read
curl http://localhost:8099/events
```

### Step 6: Create Initial Documentation

Create /opt/leveredge/README.md with:
- Architecture overview
- Directory structure
- Quick start guide
- Emergency procedures

Create /opt/leveredge/control-plane/docs/ARCHITECTURE.md with:
- Full architecture diagram
- Agent descriptions
- Event bus documentation
- Interaction channels

### Output Required

Show:
1. `ls -la /opt/leveredge/`
2. `ls -la /opt/leveredge/gaia/`
3. `/opt/leveredge/gaia/restore.sh list`
4. `curl http://localhost:8099/health`
5. `curl http://localhost:8099/events`
6. `systemctl --user status event-bus`
```

---

## What's Next After Phase 0

Phase 1: Deploy control plane n8n + ATLAS workflow
Phase 2: HEPHAESTUS + AEGIS (active credential management)
Phase 3: CHRONOS + HADES (backup/rollback)
Phase 4: Remaining agents
Phase 5: Data plane sync

---

## Ready?

**Copy this spec to Claude Code and let it build Phase 0.**

When done, you'll have:
- GAIA emergency system (can rebuild everything)
- Event Bus (all agents can communicate)
- Foundation for all other phases

**LET'S GOOOOO!!! 🚀**
