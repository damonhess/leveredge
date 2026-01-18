-- Rollback backup and monitoring
DROP FUNCTION IF EXISTS cleanup_old_monitoring_data;
DROP TABLE IF EXISTS build_log CASCADE;
DROP TABLE IF EXISTS llm_daily_summary CASCADE;
DROP TABLE IF EXISTS llm_model_pricing CASCADE;
DROP TABLE IF EXISTS db_metrics CASCADE;
DROP TABLE IF EXISTS system_events CASCADE;
DROP TABLE IF EXISTS system_health CASCADE;
DROP TABLE IF EXISTS backup_history CASCADE;
