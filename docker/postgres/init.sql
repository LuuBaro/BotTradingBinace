-- Initialize PostgreSQL for Bot Trading Platform
-- This script creates initial database structure and extensions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
ALTER DATABASE bottrading SET search_path TO trading, audit, public;

-- Enable logging for audit trail
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255),
    operation VARCHAR(10),
    old_data JSONB,
    new_data JSONB,
    user_name VARCHAR(255) DEFAULT CURRENT_USER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remote_addr INET
);

-- Create indexes on audit table
CREATE INDEX idx_audit_timestamp ON audit.audit_log(timestamp DESC);
CREATE INDEX idx_audit_table ON audit.audit_log(table_name);

-- Create backup metadata table
CREATE TABLE IF NOT EXISTS trading.backup_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    backup_name VARCHAR(255) NOT NULL UNIQUE,
    backup_size BIGINT,
    backup_path TEXT,
    backup_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    backup_type VARCHAR(50), -- 'full', 'incremental', 'automated'
    status VARCHAR(50), -- 'pending', 'in_progress', 'completed', 'failed'
    error_message TEXT,
    version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_backup_time ON trading.backup_metadata(backup_time DESC);
CREATE INDEX idx_backup_status ON trading.backup_metadata(status);

-- Create health check log
CREATE TABLE IF NOT EXISTS trading.health_check_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(255),
    status VARCHAR(50), -- healthy, degraded, unhealthy
    response_time_ms INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

CREATE INDEX idx_health_check_time ON trading.health_check_log(timestamp DESC);
CREATE INDEX idx_health_check_service ON trading.health_check_log(service_name);

-- Create migration history
CREATE TABLE IF NOT EXISTS trading.migration_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50), -- 'success', 'failed', 'rolled_back'
    error_message TEXT
);

CREATE INDEX idx_migration_executed ON trading.migration_history(executed_at DESC);

-- Grant permissions
GRANT ALL ON SCHEMA trading TO bottrading;
GRANT ALL ON SCHEMA audit TO bottrading;
GRANT ALL ON ALL TABLES IN SCHEMA trading TO bottrading;
GRANT ALL ON ALL TABLES IN SCHEMA audit TO bottrading;
GRANT USAGE, CREATE ON SCHEMA trading TO bottrading;
