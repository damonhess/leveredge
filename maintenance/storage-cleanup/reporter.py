#!/usr/bin/env python3
"""
Storage Usage Reporter for Supabase Storage
============================================

This script generates comprehensive storage usage reports including:
- Total storage used
- Usage by bucket
- Largest files
- Growth trends

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
from dataclasses import dataclass, field
from collections import defaultdict

import yaml
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class BucketStats:
    """Statistics for a single bucket."""
    name: str
    file_count: int = 0
    total_size: int = 0
    avg_file_size: int = 0
    largest_file_size: int = 0
    largest_file_path: str = ""
    oldest_file_date: Optional[datetime] = None
    newest_file_date: Optional[datetime] = None
    files_by_extension: dict = field(default_factory=dict)


@dataclass
class StorageReport:
    """Complete storage usage report."""
    generated_at: datetime = field(default_factory=datetime.now)
    total_buckets: int = 0
    total_files: int = 0
    total_size: int = 0
    buckets: list = field(default_factory=list)
    largest_files: list = field(default_factory=list)
    growth_data: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)


class SupabaseStorageReporter:
    """Reporter for Supabase Storage usage statistics."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()

        # Get connection details
        supabase_url = os.getenv("SUPABASE_URL", self.config["supabase"]["url"])
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        if not service_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

        self.base_url = supabase_url.rstrip('/')
        self.storage_url = f"{self.base_url}/storage/v1"
        self.headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/json"
        }
        self.client = httpx.Client(timeout=60.0)
        self.logger = logging.getLogger(__name__)

        # Historical data storage (for trends)
        self.history_file = Path(
            self.config["reporting"].get("reports_directory", "reports")
        ) / "storage_history.json"

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
        logging.basicConfig(
            level=getattr(logging, log_config.get("level", "INFO")),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    def _api_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request."""
        url = f"{self.storage_url}{endpoint}"
        response = self.client.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def list_buckets(self) -> list[dict]:
        """List all storage buckets."""
        return self._api_request("GET", "/bucket")

    def list_files(self, bucket: str, path: str = "", limit: int = 1000, offset: int = 0) -> list[dict]:
        """List files in a bucket."""
        return self._api_request(
            "POST",
            f"/object/list/{bucket}",
            json={
                "prefix": path,
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"}
            }
        )

    def list_all_files(self, bucket: str) -> list[dict]:
        """List all files in a bucket with pagination."""
        all_files = []
        offset = 0
        limit = 1000

        while True:
            files = self.list_files(bucket, "", limit, offset)
            if not files:
                break
            all_files.extend(files)
            if len(files) < limit:
                break
            offset += limit

        return all_files

    def get_bucket_stats(self, bucket_name: str) -> BucketStats:
        """Get detailed statistics for a bucket."""
        stats = BucketStats(name=bucket_name)
        files = self.list_all_files(bucket_name)

        extensions: dict[str, dict] = defaultdict(lambda: {"count": 0, "size": 0})

        for file_data in files:
            if file_data.get('id') is None:  # Skip folders
                continue

            metadata = file_data.get('metadata', {})
            size = metadata.get('size', 0)
            file_name = file_data.get('name', '')

            stats.file_count += 1
            stats.total_size += size

            # Track largest file
            if size > stats.largest_file_size:
                stats.largest_file_size = size
                stats.largest_file_path = f"{bucket_name}/{file_name}"

            # Track dates
            created_at = None
            if file_data.get('created_at'):
                created_at = datetime.fromisoformat(
                    file_data['created_at'].replace('Z', '+00:00')
                ).replace(tzinfo=None)

                if stats.oldest_file_date is None or created_at < stats.oldest_file_date:
                    stats.oldest_file_date = created_at
                if stats.newest_file_date is None or created_at > stats.newest_file_date:
                    stats.newest_file_date = created_at

            # Track by extension
            ext = Path(file_name).suffix.lower() or '.no_extension'
            extensions[ext]["count"] += 1
            extensions[ext]["size"] += size

        # Calculate average
        if stats.file_count > 0:
            stats.avg_file_size = stats.total_size // stats.file_count

        stats.files_by_extension = dict(extensions)

        return stats

    def get_largest_files(self, limit: int = 20) -> list[dict]:
        """Get the largest files across all buckets."""
        all_files = []

        buckets = self.list_buckets()
        for bucket in buckets:
            bucket_name = bucket['name']
            files = self.list_all_files(bucket_name)

            for file_data in files:
                if file_data.get('id') is None:
                    continue

                metadata = file_data.get('metadata', {})
                size = metadata.get('size', 0)

                all_files.append({
                    "bucket": bucket_name,
                    "path": file_data.get('name', ''),
                    "size": size,
                    "created_at": file_data.get('created_at'),
                    "mimetype": metadata.get('mimetype', 'unknown')
                })

        # Sort by size descending
        all_files.sort(key=lambda x: x['size'], reverse=True)

        return all_files[:limit]

    def _load_history(self) -> dict:
        """Load historical storage data."""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {"daily_snapshots": []}

    def _save_history(self, history: dict):
        """Save historical storage data."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def record_snapshot(self, report: StorageReport):
        """Record current storage state for trend analysis."""
        history = self._load_history()

        snapshot = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_size": report.total_size,
            "total_files": report.total_files,
            "buckets": {
                bucket.name: {"size": bucket.total_size, "files": bucket.file_count}
                for bucket in report.buckets
            }
        }

        # Remove duplicate date entry if exists
        history["daily_snapshots"] = [
            s for s in history["daily_snapshots"]
            if s["date"] != snapshot["date"]
        ]
        history["daily_snapshots"].append(snapshot)

        # Keep only last N days
        trend_days = self.config["reporting"].get("trend_days", 30)
        history["daily_snapshots"] = history["daily_snapshots"][-trend_days:]

        self._save_history(history)

    def calculate_growth_trends(self) -> dict:
        """Calculate storage growth trends."""
        history = self._load_history()
        snapshots = history.get("daily_snapshots", [])

        if len(snapshots) < 2:
            return {
                "has_data": False,
                "message": "Insufficient historical data for trend analysis"
            }

        # Calculate daily growth rate
        first = snapshots[0]
        last = snapshots[-1]
        days_diff = (
            datetime.strptime(last["date"], "%Y-%m-%d") -
            datetime.strptime(first["date"], "%Y-%m-%d")
        ).days

        if days_diff == 0:
            days_diff = 1

        size_growth = last["total_size"] - first["total_size"]
        daily_growth = size_growth / days_diff

        # Calculate weekly average
        weekly_data = []
        for s in snapshots[-7:]:
            weekly_data.append(s["total_size"])
        weekly_avg = sum(weekly_data) / len(weekly_data) if weekly_data else 0

        return {
            "has_data": True,
            "period_days": days_diff,
            "start_size": first["total_size"],
            "end_size": last["total_size"],
            "total_growth": size_growth,
            "daily_growth_bytes": int(daily_growth),
            "weekly_average_size": int(weekly_avg),
            "growth_rate_percent": (
                (size_growth / first["total_size"] * 100)
                if first["total_size"] > 0 else 0
            ),
            "snapshots": snapshots
        }

    def check_thresholds(self, report: StorageReport) -> list[dict]:
        """Check storage against configured thresholds."""
        alerts = []
        thresholds = self.config.get("thresholds", {})

        total_gb = report.total_size / (1024 ** 3)

        # Total storage thresholds
        if total_gb >= thresholds.get("total_storage_critical_gb", 500):
            alerts.append({
                "level": "critical",
                "type": "total_storage",
                "message": f"Total storage ({total_gb:.2f} GB) exceeds critical threshold",
                "value": total_gb,
                "threshold": thresholds.get("total_storage_critical_gb", 500)
            })
        elif total_gb >= thresholds.get("total_storage_warning_gb", 100):
            alerts.append({
                "level": "warning",
                "type": "total_storage",
                "message": f"Total storage ({total_gb:.2f} GB) exceeds warning threshold",
                "value": total_gb,
                "threshold": thresholds.get("total_storage_warning_gb", 100)
            })

        # Per-bucket thresholds
        for bucket in report.buckets:
            bucket_gb = bucket.total_size / (1024 ** 3)

            if bucket_gb >= thresholds.get("bucket_size_critical_gb", 50):
                alerts.append({
                    "level": "critical",
                    "type": "bucket_storage",
                    "bucket": bucket.name,
                    "message": f"Bucket '{bucket.name}' ({bucket_gb:.2f} GB) exceeds critical threshold",
                    "value": bucket_gb,
                    "threshold": thresholds.get("bucket_size_critical_gb", 50)
                })
            elif bucket_gb >= thresholds.get("bucket_size_warning_gb", 10):
                alerts.append({
                    "level": "warning",
                    "type": "bucket_storage",
                    "bucket": bucket.name,
                    "message": f"Bucket '{bucket.name}' ({bucket_gb:.2f} GB) exceeds warning threshold",
                    "value": bucket_gb,
                    "threshold": thresholds.get("bucket_size_warning_gb", 10)
                })

        return alerts

    def generate_report(self) -> StorageReport:
        """Generate a comprehensive storage report."""
        self.logger.info("Generating storage usage report...")
        report = StorageReport()

        # Get all buckets
        buckets = self.list_buckets()
        report.total_buckets = len(buckets)
        self.logger.info(f"Found {len(buckets)} buckets")

        # Get stats for each bucket
        for bucket in buckets:
            bucket_name = bucket['name']
            self.logger.info(f"Analyzing bucket: {bucket_name}")
            stats = self.get_bucket_stats(bucket_name)
            report.buckets.append(stats)
            report.total_files += stats.file_count
            report.total_size += stats.total_size

        # Get largest files
        top_files_count = self.config["reporting"].get("top_files_count", 20)
        report.largest_files = self.get_largest_files(top_files_count)

        # Get growth trends
        report.growth_data = self.calculate_growth_trends()

        # Check thresholds
        report.alerts = self.check_thresholds(report)

        # Record snapshot for future trends
        self.record_snapshot(report)

        self.logger.info("Report generation complete")
        return report

    def format_report(self, report: StorageReport, format_type: str = "markdown") -> str:
        """Format report for output."""
        if format_type == "json":
            return self._format_json(report)
        elif format_type == "html":
            return self._format_html(report)
        else:
            return self._format_markdown(report)

    def _format_json(self, report: StorageReport) -> str:
        """Format report as JSON."""
        data = {
            "generated_at": report.generated_at.isoformat(),
            "total_buckets": report.total_buckets,
            "total_files": report.total_files,
            "total_size": report.total_size,
            "total_size_formatted": self._format_bytes(report.total_size),
            "buckets": [
                {
                    "name": b.name,
                    "file_count": b.file_count,
                    "total_size": b.total_size,
                    "total_size_formatted": self._format_bytes(b.total_size),
                    "avg_file_size": b.avg_file_size,
                    "largest_file": {
                        "path": b.largest_file_path,
                        "size": b.largest_file_size
                    },
                    "files_by_extension": b.files_by_extension
                }
                for b in report.buckets
            ],
            "largest_files": report.largest_files,
            "growth_data": report.growth_data,
            "alerts": report.alerts
        }
        return json.dumps(data, indent=2, default=str)

    def _format_markdown(self, report: StorageReport) -> str:
        """Format report as Markdown."""
        lines = [
            "# Storage Usage Report",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Buckets | {report.total_buckets} |",
            f"| Total Files | {report.total_files:,} |",
            f"| Total Storage | {self._format_bytes(report.total_size)} |",
            "",
        ]

        # Alerts section
        if report.alerts:
            lines.extend([
                "## Alerts",
                "",
            ])
            for alert in report.alerts:
                icon = "!!" if alert["level"] == "critical" else "!"
                lines.append(f"- [{icon}] **{alert['level'].upper()}**: {alert['message']}")
            lines.append("")

        # Bucket breakdown
        lines.extend([
            "## Storage by Bucket",
            "",
            "| Bucket | Files | Size | Avg Size |",
            "|--------|-------|------|----------|",
        ])

        for bucket in sorted(report.buckets, key=lambda x: x.total_size, reverse=True):
            lines.append(
                f"| {bucket.name} | {bucket.file_count:,} | "
                f"{self._format_bytes(bucket.total_size)} | "
                f"{self._format_bytes(bucket.avg_file_size)} |"
            )

        lines.append("")

        # Largest files
        lines.extend([
            "## Largest Files",
            "",
            "| Rank | File | Size | Type |",
            "|------|------|------|------|",
        ])

        for i, file in enumerate(report.largest_files[:10], 1):
            lines.append(
                f"| {i} | {file['bucket']}/{file['path'][:50]} | "
                f"{self._format_bytes(file['size'])} | {file['mimetype']} |"
            )

        lines.append("")

        # Growth trends
        if report.growth_data.get("has_data"):
            lines.extend([
                "## Growth Trends",
                "",
                f"**Period:** {report.growth_data['period_days']} days",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Starting Size | {self._format_bytes(report.growth_data['start_size'])} |",
                f"| Current Size | {self._format_bytes(report.growth_data['end_size'])} |",
                f"| Total Growth | {self._format_bytes(report.growth_data['total_growth'])} |",
                f"| Daily Growth | {self._format_bytes(report.growth_data['daily_growth_bytes'])} |",
                f"| Growth Rate | {report.growth_data['growth_rate_percent']:.2f}% |",
                "",
            ])

        # File type breakdown (aggregate)
        lines.extend([
            "## File Types Summary",
            "",
        ])

        all_extensions: dict = defaultdict(lambda: {"count": 0, "size": 0})
        for bucket in report.buckets:
            for ext, data in bucket.files_by_extension.items():
                all_extensions[ext]["count"] += data["count"]
                all_extensions[ext]["size"] += data["size"]

        sorted_ext = sorted(all_extensions.items(), key=lambda x: x[1]["size"], reverse=True)[:15]

        lines.extend([
            "| Extension | Count | Total Size |",
            "|-----------|-------|------------|",
        ])
        for ext, data in sorted_ext:
            lines.append(f"| {ext} | {data['count']:,} | {self._format_bytes(data['size'])} |")

        lines.extend([
            "",
            "---",
            "*Generated by LeverEdge Storage Reporter*",
        ])

        return "\n".join(lines)

    def _format_html(self, report: StorageReport) -> str:
        """Format report as HTML."""
        # Simple HTML template
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Storage Usage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .alert-critical {{ background-color: #ffcccc; }}
        .alert-warning {{ background-color: #ffffcc; }}
        h1, h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Storage Usage Report</h1>
    <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Summary</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Buckets</td><td>{report.total_buckets}</td></tr>
        <tr><td>Total Files</td><td>{report.total_files:,}</td></tr>
        <tr><td>Total Storage</td><td>{self._format_bytes(report.total_size)}</td></tr>
    </table>
"""
        if report.alerts:
            html += "<h2>Alerts</h2><ul>"
            for alert in report.alerts:
                css_class = f"alert-{alert['level']}"
                html += f"<li class='{css_class}'><strong>{alert['level'].upper()}:</strong> {alert['message']}</li>"
            html += "</ul>"

        html += """
    <h2>Storage by Bucket</h2>
    <table>
        <tr><th>Bucket</th><th>Files</th><th>Size</th><th>Avg Size</th></tr>
"""
        for bucket in sorted(report.buckets, key=lambda x: x.total_size, reverse=True):
            html += f"""
        <tr>
            <td>{bucket.name}</td>
            <td>{bucket.file_count:,}</td>
            <td>{self._format_bytes(bucket.total_size)}</td>
            <td>{self._format_bytes(bucket.avg_file_size)}</td>
        </tr>
"""
        html += """
    </table>

    <h2>Largest Files</h2>
    <table>
        <tr><th>Rank</th><th>File</th><th>Size</th><th>Type</th></tr>
"""
        for i, file in enumerate(report.largest_files[:10], 1):
            html += f"""
        <tr>
            <td>{i}</td>
            <td>{file['bucket']}/{file['path'][:50]}</td>
            <td>{self._format_bytes(file['size'])}</td>
            <td>{file['mimetype']}</td>
        </tr>
"""
        html += """
    </table>
    <hr>
    <p><em>Generated by LeverEdge Storage Reporter</em></p>
</body>
</html>
"""
        return html

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
        self.client.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Storage Usage Reporter for Supabase Storage"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "html"],
        default=None,
        help="Output format (default: from config)"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print report to stdout"
    )

    args = parser.parse_args()

    try:
        reporter = SupabaseStorageReporter(args.config)
        report = reporter.generate_report()

        # Determine format
        output_format = args.format or reporter.config["reporting"].get("output_format", "markdown")

        # Format report
        formatted = reporter.format_report(report, output_format)

        # Output
        if args.stdout:
            print(formatted)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(formatted)
            logging.info(f"Report saved to: {args.output}")
        elif not args.stdout:
            # Default output path
            reports_dir = reporter.config["reporting"].get(
                "reports_directory",
                "/opt/leveredge/maintenance/storage-cleanup/reports"
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "json" if output_format == "json" else "html" if output_format == "html" else "md"
            output_path = Path(reports_dir) / f"storage_report_{timestamp}.{ext}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(formatted)
            print(f"Report saved to: {output_path}")

        reporter.close()

        # Exit with warning code if there are critical alerts
        if any(a["level"] == "critical" for a in report.alerts):
            sys.exit(2)
        elif report.alerts:
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        logging.error(f"Report generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
