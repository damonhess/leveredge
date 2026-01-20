-- Add tables to realtime publication (PROD uses aria_* not aria_unified_*)
-- This ensures PROD realtime subscriptions work for ARIA chat
ALTER PUBLICATION supabase_realtime ADD TABLE IF NOT EXISTS aria_conversations;
ALTER PUBLICATION supabase_realtime ADD TABLE IF NOT EXISTS aria_messages;
