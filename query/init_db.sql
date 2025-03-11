-- Users table with access levels and usage tracking
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    access_level TEXT CHECK (access_level IN ('free', 'premium', 'admin')) NOT NULL DEFAULT 'free',
    remaining_free_queries INTEGER NOT NULL DEFAULT 30,
    total_queries INTEGER NOT NULL DEFAULT 0,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table to track all interactions
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    query_cost REAL NOT NULL,
    search_used BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Provider statistics
CREATE TABLE IF NOT EXISTS provider_stats (
    provider TEXT PRIMARY KEY,
    total_messages INTEGER NOT NULL DEFAULT 0,
    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost REAL NOT NULL DEFAULT 0
);

-- Initialize the providers
INSERT OR IGNORE INTO provider_stats (provider, total_messages, total_input_tokens, total_output_tokens, total_tokens, total_cost)
VALUES 
    ('claude', 0, 0, 0, 0, 0.0),
    ('deepseek', 0, 0, 0, 0, 0.0),
    ('chatgpt', 0, 0, 0, 0, 0.0);