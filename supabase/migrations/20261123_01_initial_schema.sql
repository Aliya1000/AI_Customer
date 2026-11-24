-- ==============================================================================
-- 01. Initial Core Schema for Supabase PostgreSQL
-- ==============================================================================

-- 1. Products Catalog Table
CREATE TABLE IF NOT EXISTS public.products (
    product_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL UNIQUE,
    product_description TEXT NOT NULL,
    product_category VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Sessions Table
CREATE TABLE IF NOT EXISTS public.sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    interaction_mode VARCHAR(32) NOT NULL CHECK (interaction_mode IN ('simulator', 'manual', 'replay')),
    product_name VARCHAR(255) NOT NULL,
    product_context TEXT,
    customer_scenario TEXT NOT NULL,
    persona VARCHAR(64) DEFAULT 'Patient',
    emotional_progression TEXT,
    replay_transcript TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Messages Table
CREATE TABLE IF NOT EXISTS public.messages (
    message_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
    sender VARCHAR(32) NOT NULL CHECK (sender IN ('customer', 'employee', 'system')),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Knowledge Documents Table
CREATE TABLE IF NOT EXISTS public.knowledge_documents (
    document_id VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    storage_path TEXT,
    upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'indexed', 'failed'))
);

-- 5. Coaching Reports Table
CREATE TABLE IF NOT EXISTS public.coaching_reports (
    report_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE REFERENCES public.sessions(session_id) ON DELETE CASCADE,
    conversation_summary TEXT NOT NULL,
    customer_sentiment VARCHAR(255),
    evaluation_score INTEGER NOT NULL CHECK (evaluation_score >= 0 AND evaluation_score <= 100),
    employee_evaluation TEXT,
    strengths JSONB DEFAULT '[]',
    areas_for_improvement JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    recommended_replies JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON public.sessions(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_filename ON public.knowledge_documents(filename);

-- Seed Initial Products
INSERT INTO public.products (product_id, product_name, product_description, product_category)
VALUES
    ('PRD-01', 'AeroSound Pro ANC Headphones', 'Wireless Bluetooth 5.3 over-ear headphones with Hybrid Active Noise Cancellation and 1-year hardware warranty.', 'Audio Hardware'),
    ('PRD-02', 'PulseWatch S4 Smartwatch', 'AMOLED fitness smartwatch with 5ATM water resistance and 10-day battery life.', 'Wearables'),
    ('PRD-03', 'CloudDesk CRM Pro Subscription', 'Enterprise multi-seat SaaS subscription with SSO, API access, and 99.9% SLA.', 'SaaS Software')
ON CONFLICT (product_id) DO NOTHING;
