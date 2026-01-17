# Storage Cleanup Automation

Automated storage cleanup and reporting system for Supabase Storage buckets.

## Overview

This system provides:

- **Orphaned file detection**: Identifies files not referenced in any database table
- **Age-based cleanup**: Removes files older than a configurable retention period
- **Storage usage reporting**: Comprehensive reports on storage usage and trends
- **Scheduled automation**: Weekly cleanup via n8n workflow
- **Safe deletion**: Dry-run mode by default with confirmation

## Components

### cleanup.py

Main cleanup script that:

1. Connects to Supabase Storage API
2. Scans configured database tables for file references
3. Identifies orphaned files (not referenced anywhere)
4. Identifies old files (beyond retention period)
5. Deletes files (with dry-run mode for safety)
6. Generates cleanup reports

### reporter.py

Storage usage reporter that generates:

1. Total storage usage statistics
2. Per-bucket breakdown
3. Largest files listing
4. Growth trend analysis
5. Threshold alerts

### cleanup-workflow.json

n8n workflow for scheduled automation:

1. Runs every Sunday at 3:00 AM
2. Generates storage report
3. Executes cleanup (dry-run first, then live)
4. Sends notification via HERMES

## Installation

```bash
# Navigate to directory
cd /opt/leveredge/maintenance/storage-cleanup

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create logs and reports directories
mkdir -p logs reports
```

## Configuration

Edit `config.yaml` to customize:

```yaml
cleanup:
  retention_days: 30        # Files older than this are candidates
  dry_run: true             # Set to false to actually delete
  buckets_to_clean:
    - uploads
    - temp
    - exports
```

### Environment Variables

Required:

```bash
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

Optional:

```bash
export SUPABASE_URL="http://localhost:54323"  # Override config
```

## Usage

### Manual Cleanup

```bash
# Dry run (default) - see what would be deleted
python cleanup.py

# Dry run with explicit flag
python cleanup.py --dry-run

# Live deletion (actually delete files)
python cleanup.py --no-dry-run

# Custom config file
python cleanup.py --config /path/to/config.yaml

# Output stats as JSON
python cleanup.py --json
```

### Storage Report

```bash
# Generate report (default: markdown)
python reporter.py

# JSON output
python reporter.py --format json

# HTML output
python reporter.py --format html

# Print to stdout
python reporter.py --stdout

# Custom output path
python reporter.py --output /path/to/report.md
```

### n8n Workflow

1. Import `cleanup-workflow.json` into n8n
2. Configure the schedule trigger (default: Sunday 3 AM)
3. Update HERMES webhook URL if needed
4. Activate the workflow

## Orphan Detection

The system identifies orphaned files by:

1. Scanning configured database tables for file path columns
2. Building a reference map of all paths
3. Comparing storage files against the reference map
4. Files not in the map are considered orphaned

Configure tables to scan in `config.yaml`:

```yaml
orphan_detection:
  enabled: true
  reference_tables:
    documents:
      - file_path
      - attachment_url
    profiles:
      - avatar_url
```

## Safety Features

1. **Dry Run Mode**: Enabled by default - no files deleted until explicitly disabled
2. **Exclude Patterns**: Protect specific files from deletion (e.g., `*.keep`)
3. **Bucket Exclusions**: Skip critical buckets (e.g., `avatars`, `system`)
4. **Threshold Alerts**: Warnings before storage limits are reached
5. **Error Handling**: Continues on individual file errors, reports all issues

## Reports

Reports are saved to `/opt/leveredge/maintenance/storage-cleanup/reports/`:

- `cleanup_report_YYYYMMDD_HHMMSS.md` - Cleanup operation reports
- `storage_report_YYYYMMDD_HHMMSS.md` - Usage reports
- `storage_history.json` - Historical data for trend analysis

## Troubleshooting

### Connection Issues

```bash
# Test Supabase connection
curl -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
     http://localhost:54323/storage/v1/bucket
```

### Permission Errors

Ensure the service role key has storage admin permissions.

### No Files Detected

1. Verify bucket names in config match actual Supabase buckets
2. Check reference table configuration
3. Enable debug logging: `logging: level: DEBUG`

## Workflow Architecture

```
Weekly Schedule (Sunday 3 AM)
         |
         v
Generate Storage Report
         |
         v
Parse & Analyze Report
         |
         v
Run Cleanup (Dry Run)
         |
         v
Analyze Results
         |
    +----+----+
    |         |
    v         v
Should    Skip
Proceed?  Report
    |         |
    v         |
Run Cleanup   |
(Live)        |
    |         |
    +----+----+
         |
         v
Build HERMES Notification
         |
         v
Send Report via HERMES
```

## Monitoring

The workflow sends notifications via HERMES with:

- Storage summary
- Cleanup results
- Alerts (warnings/critical)
- Error details if any

Priority levels:

- `low`: Normal operation
- `medium`: Warning thresholds exceeded
- `high`: Critical thresholds or errors

## License

Internal use only - LeverEdge Infrastructure
