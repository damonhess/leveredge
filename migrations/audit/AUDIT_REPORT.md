# Database Audit Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Summary

### Tables in DEV but not PROD: 124 tables
Key tables include:
- **AEGIS V2**: aegis_credentials_v2, aegis_credential_versions, aegis_audit_log, aegis_rotation_history, aegis_health_checks, aegis_providers, aegis_templates
- **CONCLAVE/Council**: council_meetings, council_transcript, council_decisions, council_actions, council_agent_profiles
- **HADES**: hades_operations, recovery_logs
- **Infrastructure**: port_registry, port_ranges, services, ssl_certificates, security_audits, security_events
- **LLM Tracking**: llm_daily_stats, llm_monthly_stats, llm_node_costs, llm_model_pricing, llm_executions, llm_daily_summary
- **Quality/Testing**: quality_gates, quality_metrics, quality_standards, test_runs
- **Various Domain Tables**: Many empty placeholder tables from previous experiments

### Tables only in PROD: 17 tables
Most are empty placeholder tables or have been moved. Tables with data:
- agent_usage_logs (40 rows) - Consider migrating or deprecating
- llm_budget_alerts (4 rows) - May need preservation
- llm_usage_daily (0 rows) - Empty
- n8n_vectors (0 rows) - Empty

### Views in DEV: 5
- aria_chunks_overview
- aria_reminder_summary
- build_log_recent
- llm_cost_summary
- llm_daily_costs

### Views in PROD: 14
Many views that should be standardized or deprecated.

## Action Plan

1. Create migrations for AEGIS V2 tables (priority)
2. Create migrations for CONCLAVE tables (priority)
3. Create migrations for monitoring/backup infrastructure
4. Sync views from DEV to PROD
5. Mark PROD-only tables for review/deprecation

