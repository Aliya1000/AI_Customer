-- ==============================================================================
-- 03. Soft Deletes and Audit Trail Extensions
-- ==============================================================================

-- Add deleted_at and updated_by columns to enable soft deletes & auditability
ALTER TABLE public.sessions
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) DEFAULT NULL;

ALTER TABLE public.messages
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS edit_count INTEGER DEFAULT 0;

ALTER TABLE public.knowledge_documents
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(64) DEFAULT 'system';

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(64) NOT NULL,
    record_id VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE', 'SOFT_DELETE')),
    old_data JSONB DEFAULT NULL,
    new_data JSONB DEFAULT NULL,
    performed_by VARCHAR(64) DEFAULT 'anonymous',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_record ON public.audit_logs(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON public.audit_logs(timestamp);
