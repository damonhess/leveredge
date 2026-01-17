#!/usr/bin/env python3
"""
Storage Cleanup Automation for Supabase Storage
================================================

This script handles:
- Orphaned file detection in Supabase Storage
- Storage usage calculation per bucket
- Safe deletion of old/orphaned files
- Comprehensive cleanup reporting

Author: LeverEdge Maintenance Team
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

import yaml
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class CleanupStats:
    """Statistics for cleanup operation."""
    total_files_scanned: int = 0
    orphaned_files_found: int = 0
    old_files_found: int = 0
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: list = field(default_factory=list)
    skipped_files: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['start_time'] = self.start_time.isoformat() if self.start_time else None
        result['end_time'] = self.end_time.isoformat() if self.end_time else None
        result['duration_seconds'] = (
            (self.end_time - self.start_time).total_seconds()
            if self.start_time and self.end_time else None
        )
        return result


@dataclass
class FileInfo:
    """Information about a storage file."""
    bucket: str
    path: str
    name: str
    size: int
    created_at: datetime
    updated_at: datetime
    metadata: dict = field(default_factory=dict)

    @property
    def full_path(self) -> str:
        return f"{self.bucket}/{self.path}"

    @property
    def age_days(self) -> int:
        return (datetime.now() - self.created_at).days


class SupabaseStorageClient:
    """Client for interacting with Supabase Storage API."""

    def __init__(self, url: str, service_key: str):
        self.base_url = url.rstrip('/')
        self.storage_url = f"{self.base_url}/storage/v1"
        self.headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/json"
        }
        self.client = httpx.Client(timeout=30.0)

    def list_buckets(self) -> list[dict]:
        """List all storage buckets."""
        response = self.client.get(
            f"{self.storage_url}/bucket",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def list_files(self, bucket: str, path: str = "", limit: int = 1000, offset: int = 0) -> list[dict]:
        """List files in a bucket/path."""
        response = self.client.post(
            f"{self.storage_url}/object/list/{bucket}",
            headers=self.headers,
            json={
                "prefix": path,
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"}
            }
        )
        response.raise_for_status()
        return response.json()

    def list_all_files(self, bucket: str, path: str = "") -> list[dict]:
        """List all files in a bucket (handles pagination)."""
        all_files = []
        offset = 0
        limit = 1000

        while True:
            files = self.list_files(bucket, path, limit, offset)
            if not files:
                break
            all_files.extend(files)
            if len(files) < limit:
                break
            offset += limit

        return all_files

    def get_file_info(self, bucket: str, path: str) -> dict:
        """Get metadata for a specific file."""
        response = self.client.get(
            f"{self.storage_url}/object/info/{bucket}/{path}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def delete_file(self, bucket: str, paths: list[str]) -> dict:
        """Delete files from a bucket."""
        response = self.client.delete(
            f"{self.storage_url}/object/{bucket}",
            headers=self.headers,
            json={"prefixes": paths}
        )
        response.raise_for_status()
        return response.json()

    def get_bucket_size(self, bucket: str) -> int:
        """Calculate total size of a bucket."""
        files = self.list_all_files(bucket)
        return sum(f.get('metadata', {}).get('size', 0) for f in files if f.get('metadata'))

    def close(self):
        """Close the HTTP client."""
        self.client.close()


class DatabaseClient:
    """Client for checking file references in database."""

    def __init__(self, url: str, service_key: str):
        self.base_url = url.rstrip('/')
        self.rest_url = f"{self.base_url}/rest/v1"
        self.headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.client = httpx.Client(timeout=30.0)

    def get_referenced_paths(self, table: str, columns: list[str]) -> set[str]:
        """Get all file paths referenced in specified table columns."""
        referenced_paths = set()

        for column in columns:
            try:
                response = self.client.get(
                    f"{self.rest_url}/{table}",
                    headers=self.headers,
                    params={"select": column, f"{column}": "not.is.null"}
                )
                response.raise_for_status()
                data = response.json()

                for row in data:
                    value = row.get(column)
                    if value:
                        if isinstance(value, list):
                            referenced_paths.update(value)
                        else:
                            referenced_paths.add(value)

            except Exception as e:
                logging.warning(f"Could not query {table}.{column}: {e}")

        return referenced_paths

    def close(self):
        """Close the HTTP client."""
        self.client.close()


class StorageCleanup:
    """Main storage cleanup orchestrator."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()

        # Get connection details
        supabase_url = os.getenv("SUPABASE_URL", self.config["supabase"]["url"])
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        if not service_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

        self.storage = SupabaseStorageClient(supabase_url, service_key)
        self.db = DatabaseClient(supabase_url, service_key)
        self.stats = CleanupStats()
        self.logger = logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            config_file = Path(__file__).parent / config_path

        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        """Configure logging."""
        log_config = self.config.get("logging", {})
        log_file = log_config.get("file")

        if log_file:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, log_config.get("level", "INFO")),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file) if log_file else logging.NullHandler()
            ]
        )

    def _matches_exclude_pattern(self, filename: str) -> bool:
        """Check if filename matches any exclude pattern."""
        from fnmatch import fnmatch
        patterns = self.config["cleanup"].get("exclude_patterns", [])
        return any(fnmatch(filename, pattern) for pattern in patterns)

    def _get_all_referenced_paths(self) -> set[str]:
        """Get all file paths referenced across configured tables."""
        all_paths = set()
        ref_tables = self.config["orphan_detection"].get("reference_tables", {})

        for table, columns in ref_tables.items():
            self.logger.info(f"Scanning references in {table}...")
            paths = self.db.get_referenced_paths(table, columns)
            all_paths.update(paths)
            self.logger.debug(f"Found {len(paths)} references in {table}")

        return all_paths

    def _normalize_path(self, path: str, bucket: str) -> str:
        """Normalize file path for comparison."""
        # Handle various path formats
        path = path.strip()

        # Remove leading slash if present
        if path.startswith('/'):
            path = path[1:]

        # If path doesn't start with bucket name, prepend it
        if not path.startswith(f"{bucket}/"):
            path = f"{bucket}/{path}"

        return path

    def find_orphaned_files(self, bucket: str, referenced_paths: set[str]) -> list[FileInfo]:
        """Find files that are not referenced in any database table."""
        orphaned = []
        files = self.storage.list_all_files(bucket)

        for file_data in files:
            if file_data.get('id') is None:  # Skip folders
                continue

            file_path = file_data.get('name', '')
            full_path = f"{bucket}/{file_path}"

            # Check if file is referenced (try multiple path formats)
            is_referenced = any([
                full_path in referenced_paths,
                file_path in referenced_paths,
                f"/{full_path}" in referenced_paths,
                self.storage.storage_url + f"/object/public/{full_path}" in referenced_paths
            ])

            if not is_referenced:
                metadata = file_data.get('metadata', {})
                created_at = datetime.fromisoformat(
                    file_data.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')
                )
                updated_at = datetime.fromisoformat(
                    file_data.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')
                )

                orphaned.append(FileInfo(
                    bucket=bucket,
                    path=file_path,
                    name=file_data.get('name', ''),
                    size=metadata.get('size', 0),
                    created_at=created_at.replace(tzinfo=None),
                    updated_at=updated_at.replace(tzinfo=None),
                    metadata=metadata
                ))

        return orphaned

    def find_old_files(self, bucket: str, retention_days: int) -> list[FileInfo]:
        """Find files older than retention period."""
        old_files = []
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        files = self.storage.list_all_files(bucket)

        for file_data in files:
            if file_data.get('id') is None:  # Skip folders
                continue

            created_at = datetime.fromisoformat(
                file_data.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')
            )
            created_at = created_at.replace(tzinfo=None)

            if created_at < cutoff_date:
                metadata = file_data.get('metadata', {})
                updated_at = datetime.fromisoformat(
                    file_data.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')
                )

                old_files.append(FileInfo(
                    bucket=bucket,
                    path=file_data.get('name', ''),
                    name=file_data.get('name', ''),
                    size=metadata.get('size', 0),
                    created_at=created_at,
                    updated_at=updated_at.replace(tzinfo=None),
                    metadata=metadata
                ))

        return old_files

    def delete_files(self, files: list[FileInfo], dry_run: bool = True) -> tuple[int, int]:
        """Delete files and return (count, bytes_freed)."""
        if not files:
            return 0, 0

        deleted_count = 0
        bytes_freed = 0

        # Group files by bucket
        files_by_bucket: dict[str, list[FileInfo]] = {}
        for f in files:
            if f.bucket not in files_by_bucket:
                files_by_bucket[f.bucket] = []
            files_by_bucket[f.bucket].append(f)

        for bucket, bucket_files in files_by_bucket.items():
            # Filter out excluded files
            to_delete = []
            for f in bucket_files:
                if self._matches_exclude_pattern(f.name):
                    self.logger.info(f"Skipping excluded file: {f.full_path}")
                    self.stats.skipped_files += 1
                    continue
                to_delete.append(f)

            if not to_delete:
                continue

            if dry_run:
                self.logger.info(f"[DRY RUN] Would delete {len(to_delete)} files from {bucket}")
                for f in to_delete:
                    self.logger.info(f"  [DRY RUN] Would delete: {f.full_path} ({f.size} bytes)")
                    deleted_count += 1
                    bytes_freed += f.size
            else:
                try:
                    paths = [f.path for f in to_delete]
                    self.storage.delete_file(bucket, paths)
                    for f in to_delete:
                        self.logger.info(f"Deleted: {f.full_path} ({f.size} bytes)")
                        deleted_count += 1
                        bytes_freed += f.size
                except Exception as e:
                    self.logger.error(f"Error deleting files from {bucket}: {e}")
                    self.stats.errors.append(str(e))

        return deleted_count, bytes_freed

    def run_cleanup(self, dry_run: Optional[bool] = None) -> CleanupStats:
        """Execute the cleanup process."""
        self.stats = CleanupStats()
        self.stats.start_time = datetime.now()

        if dry_run is None:
            dry_run = self.config["cleanup"].get("dry_run", True)

        retention_days = self.config["cleanup"]["retention_days"]
        buckets_to_clean = self.config["cleanup"]["buckets_to_clean"]
        buckets_exclude = self.config["cleanup"].get("buckets_exclude", [])

        self.logger.info("=" * 60)
        self.logger.info("Storage Cleanup Started")
        self.logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE DELETE'}")
        self.logger.info(f"Retention: {retention_days} days")
        self.logger.info("=" * 60)

        # Get all referenced paths
        referenced_paths = set()
        if self.config["orphan_detection"].get("enabled", True):
            self.logger.info("Building reference map from database...")
            referenced_paths = self._get_all_referenced_paths()
            self.logger.info(f"Found {len(referenced_paths)} referenced file paths")

        # Process each bucket
        all_orphaned: list[FileInfo] = []
        all_old: list[FileInfo] = []

        available_buckets = self.storage.list_buckets()
        bucket_names = [b['name'] for b in available_buckets]

        for bucket in buckets_to_clean:
            if bucket in buckets_exclude:
                self.logger.info(f"Skipping excluded bucket: {bucket}")
                continue

            if bucket not in bucket_names:
                self.logger.warning(f"Bucket not found: {bucket}")
                continue

            self.logger.info(f"\nProcessing bucket: {bucket}")

            # Find orphaned files
            if self.config["orphan_detection"].get("enabled", True):
                orphaned = self.find_orphaned_files(bucket, referenced_paths)
                self.stats.orphaned_files_found += len(orphaned)
                all_orphaned.extend(orphaned)
                self.logger.info(f"  Found {len(orphaned)} orphaned files")

            # Find old files
            old = self.find_old_files(bucket, retention_days)
            self.stats.old_files_found += len(old)
            all_old.extend(old)
            self.logger.info(f"  Found {len(old)} files older than {retention_days} days")

        # Combine and deduplicate files to delete
        files_to_delete = {f.full_path: f for f in all_orphaned}
        for f in all_old:
            if f.full_path not in files_to_delete:
                files_to_delete[f.full_path] = f

        self.stats.total_files_scanned = len(files_to_delete)

        # Delete files
        if files_to_delete:
            self.logger.info(f"\nFiles to delete: {len(files_to_delete)}")
            deleted, freed = self.delete_files(list(files_to_delete.values()), dry_run)
            self.stats.files_deleted = deleted
            self.stats.bytes_freed = freed

        self.stats.end_time = datetime.now()

        # Log summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Cleanup Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Files scanned: {self.stats.total_files_scanned}")
        self.logger.info(f"Orphaned files: {self.stats.orphaned_files_found}")
        self.logger.info(f"Old files: {self.stats.old_files_found}")
        self.logger.info(f"Files deleted: {self.stats.files_deleted}")
        self.logger.info(f"Space freed: {self._format_bytes(self.stats.bytes_freed)}")
        self.logger.info(f"Skipped: {self.stats.skipped_files}")
        self.logger.info(f"Errors: {len(self.stats.errors)}")
        if dry_run:
            self.logger.info("\n*** DRY RUN - No files were actually deleted ***")

        return self.stats

    def generate_report(self, stats: CleanupStats, output_path: Optional[str] = None) -> str:
        """Generate a cleanup report."""
        report_format = self.config["reporting"].get("output_format", "markdown")

        if report_format == "json":
            report = json.dumps(stats.to_dict(), indent=2)
        elif report_format == "markdown":
            report = self._generate_markdown_report(stats)
        else:
            report = self._generate_markdown_report(stats)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            self.logger.info(f"Report saved to: {output_path}")

        return report

    def _generate_markdown_report(self, stats: CleanupStats) -> str:
        """Generate a Markdown cleanup report."""
        duration = (
            (stats.end_time - stats.start_time).total_seconds()
            if stats.start_time and stats.end_time else 0
        )

        report = f"""# Storage Cleanup Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration:.2f} seconds

## Summary

| Metric | Value |
|--------|-------|
| Total Files Scanned | {stats.total_files_scanned} |
| Orphaned Files Found | {stats.orphaned_files_found} |
| Old Files Found | {stats.old_files_found} |
| Files Deleted | {stats.files_deleted} |
| Space Freed | {self._format_bytes(stats.bytes_freed)} |
| Skipped Files | {stats.skipped_files} |
| Errors | {len(stats.errors)} |

## Configuration

- **Retention Days:** {self.config['cleanup']['retention_days']}
- **Dry Run:** {self.config['cleanup'].get('dry_run', True)}
- **Buckets Cleaned:** {', '.join(self.config['cleanup']['buckets_to_clean'])}

"""
        if stats.errors:
            report += "## Errors\n\n"
            for error in stats.errors:
                report += f"- {error}\n"
            report += "\n"

        report += "---\n*Generated by LeverEdge Storage Cleanup Automation*\n"

        return report

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def close(self):
        """Clean up resources."""
        self.storage.close()
        self.db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Storage Cleanup Automation for Supabase Storage"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Run in dry-run mode (don't delete files)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually delete files (override config dry_run setting)"
    )
    parser.add_argument(
        "--report", "-r",
        help="Output path for cleanup report"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output stats as JSON to stdout"
    )

    args = parser.parse_args()

    # Determine dry_run mode
    dry_run = None
    if args.dry_run:
        dry_run = True
    elif args.no_dry_run:
        dry_run = False

    try:
        cleanup = StorageCleanup(args.config)
        stats = cleanup.run_cleanup(dry_run)

        # Generate report
        report_path = args.report
        if not report_path:
            reports_dir = cleanup.config["reporting"].get(
                "reports_directory",
                "/opt/leveredge/maintenance/storage-cleanup/reports"
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"{reports_dir}/cleanup_report_{timestamp}.md"

        cleanup.generate_report(stats, report_path)

        if args.json:
            print(json.dumps(stats.to_dict(), indent=2))

        cleanup.close()

        # Exit with error code if there were errors
        sys.exit(1 if stats.errors else 0)

    except Exception as e:
        logging.error(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
