-- ==========================================
-- FIX REALTIME REPLICA IDENTITY
-- Migration: 20260120_fix_realtime_replica_identity
-- Target: DEV Supabase (postgres_dev)
-- ==========================================
--
-- ISSUE: Realtime subscriptions with filters (e.g., conversation_id=eq.xxx)
-- require REPLICA IDENTITY FULL to include all columns in the WAL.
-- Without this, the subscription filter cannot match on non-primary-key columns.
--
-- AFFECTED TABLES:
-- - aria_unified_conversations (realtime for cross-device sync)
-- - aria_unified_messages (realtime for cross-device message sync)
--
-- This fix enables filtered postgres_changes subscriptions to work correctly.
-- ==========================================

-- Set replica identity to FULL for realtime-enabled tables
-- This allows postgres_changes filters on any column, not just primary key

ALTER TABLE aria_unified_messages REPLICA IDENTITY FULL;
ALTER TABLE aria_unified_conversations REPLICA IDENTITY FULL;

-- Also apply to the original tables if they're used for realtime
ALTER TABLE aria_messages REPLICA IDENTITY FULL;
ALTER TABLE aria_conversations REPLICA IDENTITY FULL;

-- Verify the settings
DO $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT c.relname, c.relreplident
        FROM pg_class c
        WHERE c.relname IN (
            'aria_unified_messages',
            'aria_unified_conversations',
            'aria_messages',
            'aria_conversations'
        )
    LOOP
        IF t.relreplident != 'f' THEN
            RAISE WARNING 'Table % has replica identity % (expected f for FULL)', t.relname, t.relreplident;
        ELSE
            RAISE NOTICE 'Table % replica identity correctly set to FULL', t.relname;
        END IF;
    END LOOP;
END
$$;
