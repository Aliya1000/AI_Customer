-- ============================================================
-- AI Customer Support Coaching Assistant - SQL Schema
-- Compatible with SQLite & PostgreSQL
-- ============================================================

-- 1. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL UNIQUE,
    product_description TEXT NOT NULL,
    product_category VARCHAR(120) NOT NULL
);

-- 2. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    interaction_mode VARCHAR(32) NOT NULL CHECK (interaction_mode IN ('simulator', 'manual', 'replay')),
    product_name VARCHAR(255) NOT NULL,
    product_context TEXT,
    customer_scenario TEXT NOT NULL,
    persona VARCHAR(64) DEFAULT 'Patient',
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Messages Table
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    sender VARCHAR(32) NOT NULL CHECK (sender IN ('customer', 'employee', 'system')),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- 4. Knowledge Documents Table
CREATE TABLE IF NOT EXISTS knowledge_documents (
    document_id VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    upload_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'indexed', 'failed'))
);

-- 5. Coaching Reports Table
CREATE TABLE IF NOT EXISTS coaching_reports (
    report_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    conversation_summary TEXT NOT NULL,
    evaluation_score INTEGER NOT NULL CHECK (evaluation_score >= 0 AND evaluation_score <= 100),
    recommendations TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_filename ON knowledge_documents(filename);