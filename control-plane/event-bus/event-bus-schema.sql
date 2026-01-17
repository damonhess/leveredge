-- /opt/leveredge/control-plane/event-bus/event-bus-schema.sql
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
  ('ARGUS', '*_completed', 5),

  -- SOLON watches for legal-related events
  ('SOLON', 'legal_*', 1),
  ('SOLON', 'contract_*', 1),
  ('SOLON', 'compliance_*', 1),
  ('SOLON', 'deadline_legal_*', 2),

  -- CROESUS watches for financial/tax events
  ('CROESUS', 'tax_*', 1),
  ('CROESUS', 'financial_*', 1),
  ('CROESUS', 'deadline_tax_*', 2),
  ('CROESUS', 'income_*', 2),
  ('CROESUS', 'expense_*', 2),
  ('CROESUS', 'transaction_*', 3),

  -- ARIA-OMNISCIENCE subscribes to all events for knowledge extraction
  ('ARIA-OMNISCIENCE', '*', 10),
  ('ARIA-OMNISCIENCE', 'aria.*', 1);

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
