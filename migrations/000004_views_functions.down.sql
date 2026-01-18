-- Rollback views and functions
DROP VIEW IF EXISTS aegis_expiring_credentials;
DROP VIEW IF EXISTS llm_daily_costs;
DROP VIEW IF EXISTS llm_cost_summary;
DROP VIEW IF EXISTS portfolio_summary;
DROP TABLE IF EXISTS agent_health;
DROP TABLE IF EXISTS hades_operations;
DROP FUNCTION IF EXISTS update_updated_at CASCADE;
