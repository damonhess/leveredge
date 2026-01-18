-- Rollback AEGIS V2
DROP TABLE IF EXISTS aegis_health_checks CASCADE;
DROP TABLE IF EXISTS aegis_rotation_history CASCADE;
DROP TABLE IF EXISTS aegis_audit_log CASCADE;
DROP TABLE IF EXISTS aegis_credential_versions CASCADE;
DROP TABLE IF EXISTS aegis_credentials_v2 CASCADE;
DROP TABLE IF EXISTS aegis_credentials CASCADE;
DROP TABLE IF EXISTS aegis_providers CASCADE;
