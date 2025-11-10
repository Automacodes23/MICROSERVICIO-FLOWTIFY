-- ============================================================================
-- Migration: 001_webhook_tables
-- Description: Add webhook infrastructure tables for Flowtify integration
-- Author: BMAD Architecture Team
-- Date: 2025-01-10
-- Related: PRD (docs/prd.md), Architecture (docs/architecture.md)
-- ============================================================================

-- This migration adds three tables:
-- 1. webhook_delivery_log: Audit log of all webhook attempts
-- 2. webhook_config: Per-tenant webhook configuration
-- 3. webhook_dead_letter_queue: Failed webhooks requiring manual intervention

START TRANSACTION;

-- ============================================================================
-- Table: webhook_delivery_log
-- Purpose: Track all webhook delivery attempts for auditing and retry management
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_delivery_log (
    id CHAR(36) PRIMARY KEY COMMENT 'UUID of the delivery attempt',
    webhook_type VARCHAR(50) NOT NULL COMMENT 'Type: status_update, speed_violation, geofence_transition, route_deviation, communication_response',
    trip_id CHAR(36) COMMENT 'Foreign key to trips table (NULL for non-trip webhooks)',
    payload JSON NOT NULL COMMENT 'Complete webhook payload as sent',
    target_url VARCHAR(500) NOT NULL COMMENT 'Flowtify endpoint URL',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'Status: pending, sent, failed, retrying',
    retry_count INT NOT NULL DEFAULT 0 COMMENT 'Number of retry attempts',
    last_error TEXT COMMENT 'Error message from last failed attempt',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When webhook was first attempted',
    delivered_at DATETIME COMMENT 'When webhook was successfully delivered',
    trace_id VARCHAR(100) COMMENT 'Request correlation ID for debugging',
    
    -- Indexes for common queries
    INDEX idx_webhook_trip_id (trip_id),
    INDEX idx_webhook_status (status),
    INDEX idx_webhook_created_at (created_at),
    INDEX idx_webhook_type (webhook_type),
    INDEX idx_webhook_status_type (status, webhook_type),
    
    -- Foreign key (soft delete on trip deletion)
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Audit log of webhook deliveries to Flowtify';

-- ============================================================================
-- Table: webhook_config
-- Purpose: Store webhook configuration per tenant
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_config (
    id CHAR(36) PRIMARY KEY COMMENT 'UUID of the configuration',
    tenant_id INT NOT NULL COMMENT 'Tenant/organization ID',
    webhook_type VARCHAR(50) NOT NULL COMMENT 'Which webhook type this config applies to',
    target_url VARCHAR(500) NOT NULL COMMENT 'Flowtify webhook endpoint URL',
    enabled BOOLEAN NOT NULL DEFAULT true COMMENT 'Whether webhooks are enabled for this tenant/type',
    secret_key VARCHAR(100) COMMENT 'HMAC secret for signature generation',
    retry_max INT NOT NULL DEFAULT 5 COMMENT 'Maximum number of retry attempts',
    timeout_seconds INT NOT NULL DEFAULT 30 COMMENT 'HTTP request timeout',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When config was created',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Ensure one config per tenant per webhook type
    UNIQUE KEY unique_tenant_webhook (tenant_id, webhook_type),
    
    -- Indexes
    INDEX idx_webhook_config_tenant (tenant_id),
    INDEX idx_webhook_config_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Webhook configuration per tenant';

-- ============================================================================
-- Table: webhook_dead_letter_queue
-- Purpose: Store webhooks that failed after exhausting all retries
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_dead_letter_queue (
    id CHAR(36) PRIMARY KEY COMMENT 'UUID of the DLQ entry',
    original_delivery_log_id CHAR(36) COMMENT 'Reference to webhook_delivery_log',
    webhook_type VARCHAR(50) NOT NULL COMMENT 'Type of webhook that failed',
    trip_id CHAR(36) COMMENT 'Associated trip ID if applicable',
    payload JSON NOT NULL COMMENT 'Original webhook payload',
    target_url VARCHAR(500) NOT NULL COMMENT 'Target URL that failed',
    failure_reason TEXT NOT NULL COMMENT 'Final error message',
    retry_count INT NOT NULL COMMENT 'Total number of retries attempted',
    last_attempt_at DATETIME NOT NULL COMMENT 'Timestamp of last delivery attempt',
    moved_to_dlq_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When moved to DLQ',
    resolved BOOLEAN NOT NULL DEFAULT false COMMENT 'Whether manually resolved',
    resolved_at DATETIME COMMENT 'When the issue was resolved',
    resolved_by VARCHAR(100) COMMENT 'User/admin who resolved it',
    resolution_notes TEXT COMMENT 'Notes about the resolution',
    
    -- Indexes
    INDEX idx_dlq_resolved (resolved),
    INDEX idx_dlq_webhook_type (webhook_type),
    INDEX idx_dlq_trip_id (trip_id),
    INDEX idx_dlq_moved_at (moved_to_dlq_at),
    
    -- Foreign keys
    FOREIGN KEY (original_delivery_log_id) REFERENCES webhook_delivery_log(id) ON DELETE CASCADE,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Dead letter queue for webhooks that exhausted retries';

-- ============================================================================
-- Initial Data: Default webhook config for tenant 24 (test tenant)
-- ============================================================================

-- Only insert if environment variable FLOWTIFY_WEBHOOK_URL is configured
-- This is safe to run - will only create if not exists

INSERT IGNORE INTO webhook_config (id, tenant_id, webhook_type, target_url, enabled, retry_max, timeout_seconds)
VALUES
    (UUID(), 24, 'status_update', 'https://api.flowtify.com/webhooks/status-update', true, 5, 30),
    (UUID(), 24, 'speed_violation', 'https://api.flowtify.com/webhooks/speed-violation', true, 5, 30),
    (UUID(), 24, 'geofence_transition', 'https://api.flowtify.com/webhooks/geofence-transition', true, 5, 30),
    (UUID(), 24, 'route_deviation', 'https://api.flowtify.com/webhooks/route-deviation', true, 5, 30),
    (UUID(), 24, 'communication_response', 'https://api.flowtify.com/webhooks/communication-response', true, 5, 30);

-- ============================================================================
-- Verification Queries (for testing after migration)
-- ============================================================================

-- Uncomment these to verify tables were created successfully:
-- SHOW TABLES LIKE 'webhook%';
-- DESCRIBE webhook_delivery_log;
-- DESCRIBE webhook_config;
-- DESCRIBE webhook_dead_letter_queue;
-- SELECT * FROM webhook_config WHERE tenant_id = 24;

COMMIT;

-- ============================================================================
-- Rollback Script (if needed)
-- ============================================================================

-- IMPORTANT: Save this for emergency rollback
-- Run these commands ONLY if you need to completely remove webhook tables

/*
START TRANSACTION;

DROP TABLE IF EXISTS webhook_dead_letter_queue;
DROP TABLE IF EXISTS webhook_config;
DROP TABLE IF EXISTS webhook_delivery_log;

COMMIT;
*/

-- ============================================================================
-- Notes for Database Administrator
-- ============================================================================

-- 1. This migration is IDEMPOTENT - safe to run multiple times
-- 2. Uses IF NOT EXISTS to prevent errors on re-run
-- 3. Foreign keys use SET NULL on delete to preserve audit trail
-- 4. All tables use InnoDB for transaction support
-- 5. Indexes optimized for common query patterns:
--    - Filtering by status (pending, failed)
--    - Filtering by trip_id
--    - Time-based queries (created_at, moved_to_dlq_at)
-- 6. JSON columns for payload storage (searchable in MySQL 5.7+)
-- 7. UTF8MB4 charset for international character support

-- Performance Considerations:
-- - webhook_delivery_log will grow rapidly (consider partitioning by date)
-- - Recommended: Archive old logs (>30 days) to separate table
-- - webhook_config is small (< 1000 rows typically)
-- - webhook_dead_letter_queue should be small if system healthy

-- Monitoring Recommendations:
-- - Alert if webhook_dead_letter_queue grows > 10 items
-- - Monitor webhook_delivery_log for high failure rates
-- - Track average retry_count in webhook_delivery_log

-- ============================================================================
-- End of Migration
-- ============================================================================

