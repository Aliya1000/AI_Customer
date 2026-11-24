# SQL Database Schema Specification

All database access must happen exclusively inside the Python backend. The frontend interacts with these entities through REST endpoints.

## Entity Relationship Summary
- `sessions` (1) ──── (N) `messages`
- `sessions` (1) ──── (1) `coaching_reports`
- `products` (catalog reference)
- `knowledge_documents` (standalone RAG document registry)

## SQL DDL (PostgreSQL / MySQL / SQLite Compatible)

```sql
-- 1. Products Table
CREATE TABLE products (
    product_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL UNIQUE,
    product_description TEXT NOT NULL,
    product_category VARCHAR(120) NOT NULL
);

-- 2. Sessions Table
CREATE TABLE sessions (
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
CREATE TABLE messages (
    message_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    sender VARCHAR(32) NOT NULL CHECK (sender IN ('customer', 'employee', 'system')),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- 4. Knowledge Documents Table
CREATE TABLE knowledge_documents (
    document_id VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    upload_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'indexed', 'failed'))
);

-- 5. Coaching Reports Table
CREATE TABLE coaching_reports (
    report_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    conversation_summary TEXT NOT NULL,
    evaluation_score INTEGER NOT NULL CHECK (evaluation_score >= 0 AND evaluation_score <= 100),
    recommendations JSON NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Recommended Indexes
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_knowledge_filename ON knowledge_documents(filename);
```

## Notes for Backend Developers
- `recommendations` in `coaching_reports` can store JSON containing `customer_sentiment`, `strengths`, `areas_for_improvement`, and `recommended_replies`.
- You may add extra columns (e.g., `employee_id`, `updated_at`, `vector_chunk_count`) without breaking the frontend as long as existing field names remain intact.