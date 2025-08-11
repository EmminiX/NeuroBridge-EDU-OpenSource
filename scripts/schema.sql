-- NeuroBridgeEDU Database Schema
-- SQLite database for lecture summaries and student management

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Core summaries table for lecture content
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    raw_transcript TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata JSON DEFAULT '{}',
    -- Additional fields for enhanced functionality
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    word_count INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    topic_category TEXT,
    ai_confidence_score REAL DEFAULT 0.0,
    -- Trigger to update word count automatically
    CONSTRAINT valid_confidence CHECK (ai_confidence_score >= 0.0 AND ai_confidence_score <= 1.0)
);

-- Students table for API endpoint management
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    api_endpoint TEXT NOT NULL,
    api_key TEXT,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Additional fields for better management
    email TEXT,
    last_sync DATETIME,
    sync_enabled BOOLEAN DEFAULT 1,
    rate_limit_per_hour INTEGER DEFAULT 60,
    webhook_secret TEXT,
    -- Constraints
    CONSTRAINT unique_student_endpoint UNIQUE (name, api_endpoint)
);

-- Send logs for tracking delivery status
CREATE TABLE IF NOT EXISTS send_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed', 'retry')),
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    response_code INTEGER,
    response_body TEXT,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    -- Foreign key relationships
    FOREIGN KEY (summary_id) REFERENCES summaries(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Application settings table for configuration
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- API usage tracking for monitoring
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    user_agent TEXT,
    ip_address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_summaries_created ON summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_status ON summaries(status);
CREATE INDEX IF NOT EXISTS idx_summaries_topic ON summaries(topic_category);

CREATE INDEX IF NOT EXISTS idx_students_active ON students(active);
CREATE INDEX IF NOT EXISTS idx_students_name ON students(name);

CREATE INDEX IF NOT EXISTS idx_send_logs_summary ON send_logs(summary_id, status);
CREATE INDEX IF NOT EXISTS idx_send_logs_student ON send_logs(student_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_send_logs_status ON send_logs(status, sent_at);

CREATE INDEX IF NOT EXISTS idx_app_settings_key ON app_settings(setting_key);

CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at DESC);

-- Triggers for automatic timestamp updates
CREATE TRIGGER IF NOT EXISTS update_summaries_timestamp 
    AFTER UPDATE ON summaries
BEGIN
    UPDATE summaries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_students_timestamp 
    AFTER UPDATE ON students
BEGIN
    UPDATE students SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_app_settings_timestamp 
    AFTER UPDATE ON app_settings
BEGIN
    UPDATE app_settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to automatically calculate word count for summaries
CREATE TRIGGER IF NOT EXISTS calculate_word_count 
    AFTER INSERT ON summaries
BEGIN
    UPDATE summaries 
    SET word_count = (
        LENGTH(NEW.content) - LENGTH(REPLACE(NEW.content, ' ', '')) + 1
    )
    WHERE id = NEW.id;
END;

-- Views for common queries
CREATE VIEW IF NOT EXISTS active_students AS
SELECT 
    id, name, api_endpoint, email, 
    last_sync, sync_enabled, rate_limit_per_hour,
    created_at, updated_at
FROM students 
WHERE active = 1;

CREATE VIEW IF NOT EXISTS recent_summaries AS
SELECT 
    s.id, s.title, s.content, s.status, s.topic_category,
    s.word_count, s.duration_seconds, s.ai_confidence_score,
    s.created_at, s.updated_at,
    COUNT(sl.id) as send_count,
    COUNT(CASE WHEN sl.status = 'sent' THEN 1 END) as successful_sends
FROM summaries s
LEFT JOIN send_logs sl ON s.id = sl.summary_id
WHERE s.created_at >= datetime('now', '-30 days')
GROUP BY s.id, s.title, s.content, s.status, s.topic_category,
         s.word_count, s.duration_seconds, s.ai_confidence_score,
         s.created_at, s.updated_at
ORDER BY s.created_at DESC;

CREATE VIEW IF NOT EXISTS delivery_status_summary AS
SELECT 
    sl.summary_id,
    s.title as summary_title,
    COUNT(*) as total_deliveries,
    COUNT(CASE WHEN sl.status = 'sent' THEN 1 END) as successful_deliveries,
    COUNT(CASE WHEN sl.status = 'failed' THEN 1 END) as failed_deliveries,
    COUNT(CASE WHEN sl.status = 'pending' THEN 1 END) as pending_deliveries,
    AVG(CASE WHEN sl.status = 'sent' THEN sl.response_code END) as avg_response_code,
    MAX(sl.sent_at) as last_delivery_attempt
FROM send_logs sl
JOIN summaries s ON sl.summary_id = s.id
GROUP BY sl.summary_id, s.title;