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
            logger.info(f"  {name}: {'OK' if status else 'FAILED'}")

        all_healthy = all(health.values())

        if all_healthy:
            logger.info("\nFULL RESTORE COMPLETE - All systems healthy")
        else:
            logger.warning("\nRESTORE COMPLETE - Some systems unhealthy")

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
            print("Backup is valid")
        else:
            print("Backup verification failed")
            sys.exit(1)

    elif args.command == 'restore':
        if args.target == 'full':
            if not args.yes:
                print("\nWARNING: This will restore the ENTIRE system!")
                print("All current data will be replaced with backup data.\n")
                confirm = input("Type 'RESTORE EVERYTHING' to confirm: ")
                if confirm != 'RESTORE EVERYTHING':
                    print("Aborted.")
                    sys.exit(0)

            success = gaia.full_restore(use_latest=not args.backup, backup_path=args.backup)
            sys.exit(0 if success else 1)
        else:
            if not args.yes:
                print(f"\nWARNING: This will restore {args.target}!")
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
                print("Restore complete")
            else:
                print("Restore failed")
                sys.exit(1)

    elif args.command == 'health':
        health = gaia.health_check()
        print("\nSystem Health:")
        print("-" * 40)
        for name, status in health.items():
            print(f"  {name}: {'Healthy' if status else 'Down'}")

        if all(health.values()):
            print("\nAll systems healthy")
        else:
            print("\nSome systems unhealthy")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
