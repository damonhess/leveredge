-- BUILD-OBSERVER: Real-time Build Visibility System
-- Enables Claude Web to observe what Claude Code is building
-- Migration: 003_build_observer.sql
-- Date: 2026-01-17

-- =============================================================================
-- TABLES
-- =============================================================================

-- Build sessions
CREATE TABLE IF NOT EXISTS build_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_name TEXT NOT NULL,
  spec_reference TEXT,  -- e.g., "CONCLAVE", "BUILD-OBSERVER"
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'paused')),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  summary TEXT,
  files_created INTEGER DEFAULT 0,
  files_modified INTEGER DEFAULT 0,
  errors_encountered INTEGER DEFAULT 0
);

-- Individual build actions
CREATE TABLE IF NOT EXISTS build_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES build_sessions(id),
  action_type TEXT NOT NULL CHECK (action_type IN ('file_created', 'file_modified', 'file_deleted', 'command_run', 'error', 'decision', 'milestone', 'note')),
  target_path TEXT,  -- file path or command
  description TEXT NOT NULL,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Quick lookup view for recent activity
CREATE OR REPLACE VIEW build_log_recent AS
SELECT
  bl.created_at,
  bs.session_name,
  bl.action_type,
  bl.target_path,
  bl.description
FROM build_log bl
JOIN build_sessions bs ON bl.session_id = bs.id
ORDER BY bl.created_at DESC
LIMIT 50;

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_build_log_session ON build_log(session_id);
CREATE INDEX IF NOT EXISTS idx_build_log_created ON build_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_build_sessions_status ON build_sessions(status);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Start a new build session
CREATE OR REPLACE FUNCTION build_start(p_name TEXT, p_spec TEXT DEFAULT NULL)
RETURNS UUID AS $$
DECLARE
  v_session_id UUID;
BEGIN
  INSERT INTO build_sessions (session_name, spec_reference)
  VALUES (p_name, p_spec)
  RETURNING id INTO v_session_id;

  RETURN v_session_id;
END;
$$ LANGUAGE plpgsql;

-- Log a build action
CREATE OR REPLACE FUNCTION build_log_action(
  p_session_id UUID,
  p_action_type TEXT,
  p_description TEXT,
  p_target_path TEXT DEFAULT NULL,
  p_details JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
  v_log_id UUID;
BEGIN
  INSERT INTO build_log (session_id, action_type, target_path, description, details)
  VALUES (p_session_id, p_action_type, p_target_path, p_description, p_details)
  RETURNING id INTO v_log_id;

  -- Update session counters
  IF p_action_type = 'file_created' THEN
    UPDATE build_sessions SET files_created = files_created + 1 WHERE id = p_session_id;
  ELSIF p_action_type = 'file_modified' THEN
    UPDATE build_sessions SET files_modified = files_modified + 1 WHERE id = p_session_id;
  ELSIF p_action_type = 'error' THEN
    UPDATE build_sessions SET errors_encountered = errors_encountered + 1 WHERE id = p_session_id;
  END IF;

  RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- End a build session
CREATE OR REPLACE FUNCTION build_end(p_session_id UUID, p_summary TEXT DEFAULT NULL)
RETURNS VOID AS $$
BEGIN
  UPDATE build_sessions
  SET status = 'completed', ended_at = NOW(), summary = p_summary
  WHERE id = p_session_id;
END;
$$ LANGUAGE plpgsql;

-- Mark session as failed
CREATE OR REPLACE FUNCTION build_fail(p_session_id UUID, p_reason TEXT)
RETURNS VOID AS $$
BEGIN
  UPDATE build_sessions
  SET status = 'failed', ended_at = NOW(), summary = p_reason
  WHERE id = p_session_id;
END;
$$ LANGUAGE plpgsql;

-- Get current active build session
CREATE OR REPLACE FUNCTION build_current()
RETURNS TABLE(
  session_id UUID,
  session_name TEXT,
  spec_reference TEXT,
  started_at TIMESTAMPTZ,
  files_created INTEGER,
  files_modified INTEGER,
  errors_encountered INTEGER,
  recent_actions JSONB
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    bs.id,
    bs.session_name,
    bs.spec_reference,
    bs.started_at,
    bs.files_created,
    bs.files_modified,
    bs.errors_encountered,
    COALESCE(
      (SELECT jsonb_agg(row_to_json(t))
       FROM (
         SELECT bl.action_type, bl.target_path, bl.description, bl.created_at
         FROM build_log bl
         WHERE bl.session_id = bs.id
         ORDER BY bl.created_at DESC
         LIMIT 10
       ) t),
      '[]'::jsonb
    ) as recent_actions
  FROM build_sessions bs
  WHERE bs.status = 'active'
  ORDER BY bs.started_at DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- USAGE EXAMPLES
-- =============================================================================

-- Start a build:
--   SELECT build_start('CONCLAVE', 'Multi-Agent Council System');
--   -- Returns UUID, save as session_id

-- Log an action:
--   SELECT build_log_action(
--     'session_id_here',
--     'file_created',
--     'Created CONVENER agent main file',
--     '/opt/leveredge/control-plane/agents/convener/convener.py',
--     '{"lines": 450}'::jsonb
--   );

-- End a build:
--   SELECT build_end('session_id_here', 'Build complete: CONVENER + SCRIBE deployed');

-- Check current build:
--   SELECT * FROM build_current();

-- View recent activity:
--   SELECT * FROM build_log_recent;
