-- ==========================================
-- SCHEMA PARA MYSQL (XAMPP)
-- Microservicio de Logística
-- ==========================================

-- Crear base de datos
CREATE DATABASE IF NOT EXISTS logistics_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE logistics_db;

-- ==========================================
-- TABLA: units (Unidades/Vehículos)
-- ==========================================
CREATE TABLE IF NOT EXISTS units (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    floatify_unit_id VARCHAR(255) NOT NULL UNIQUE,
    wialon_unit_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    plate VARCHAR(50),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_floatify_unit (floatify_unit_id),
    INDEX idx_wialon_unit (wialon_unit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: drivers (Conductores)
-- ==========================================
CREATE TABLE IF NOT EXISTS drivers (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    wialon_driver_code VARCHAR(100) UNIQUE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_wialon_code (wialon_driver_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: geofences (Geocercas/Clientes)
-- ==========================================
CREATE TABLE IF NOT EXISTS geofences (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    floatify_geofence_id VARCHAR(255) NOT NULL UNIQUE,
    wialon_geofence_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    radius INT DEFAULT 100,
    geofence_type VARCHAR(50) DEFAULT 'delivery',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_floatify_geofence (floatify_geofence_id),
    INDEX idx_wialon_geofence (wialon_geofence_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: trips (Viajes)
-- ==========================================
CREATE TABLE IF NOT EXISTS trips (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    floatify_trip_id VARCHAR(255) NOT NULL UNIQUE,
    unit_id VARCHAR(36) NOT NULL,
    driver_id VARCHAR(36),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    qr_code VARCHAR(255) UNIQUE,
    qr_scanned_at TIMESTAMP NULL,
    trip_started_at TIMESTAMP NULL,
    trip_ended_at TIMESTAMP NULL,
    whatsapp_group_id VARCHAR(255),
    whatsapp_group_name VARCHAR(255),
    cargo_description TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    INDEX idx_floatify_trip (floatify_trip_id),
    INDEX idx_unit (unit_id),
    INDEX idx_driver (driver_id),
    INDEX idx_status (status),
    INDEX idx_qr_code (qr_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: trip_geofences (Relación Viaje-Geocercas)
-- ==========================================
CREATE TABLE IF NOT EXISTS trip_geofences (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    trip_id VARCHAR(36) NOT NULL,
    geofence_id VARCHAR(36) NOT NULL,
    sequence_order INT NOT NULL,
    visit_type VARCHAR(50) NOT NULL DEFAULT 'delivery',
    entered_at TIMESTAMP NULL,
    exited_at TIMESTAMP NULL,
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    FOREIGN KEY (geofence_id) REFERENCES geofences(id) ON DELETE CASCADE,
    UNIQUE KEY unique_trip_geofence (trip_id, geofence_id),
    INDEX idx_trip (trip_id),
    INDEX idx_geofence (geofence_id),
    INDEX idx_sequence (trip_id, sequence_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: events (Eventos de Wialon)
-- ==========================================
CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    event_type VARCHAR(100) NOT NULL,
    unit_id VARCHAR(36),
    trip_id VARCHAR(36),
    geofence_id VARCHAR(36),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    event_time TIMESTAMP NOT NULL,
    wialon_notification_id VARCHAR(255),
    raw_payload JSON,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL,
    FOREIGN KEY (geofence_id) REFERENCES geofences(id) ON DELETE SET NULL,
    UNIQUE KEY unique_wialon_notification (wialon_notification_id),
    INDEX idx_event_type (event_type),
    INDEX idx_unit (unit_id),
    INDEX idx_trip (trip_id),
    INDEX idx_event_time (event_time),
    INDEX idx_processed (processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: conversations (Conversaciones WhatsApp)
-- ==========================================
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    trip_id VARCHAR(36) NOT NULL,
    driver_id VARCHAR(36),
    whatsapp_group_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    INDEX idx_trip (trip_id),
    INDEX idx_driver (driver_id),
    INDEX idx_whatsapp_group (whatsapp_group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: messages (Mensajes WhatsApp)
-- ==========================================
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    conversation_id VARCHAR(36) NOT NULL,
    sender_phone VARCHAR(20) NOT NULL,
    sender_name VARCHAR(255),
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    whatsapp_message_id VARCHAR(255),
    is_from_driver BOOLEAN DEFAULT FALSE,
    ai_processed BOOLEAN DEFAULT FALSE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation (conversation_id),
    INDEX idx_sender (sender_phone),
    INDEX idx_created_at (created_at),
    INDEX idx_ai_processed (ai_processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: ai_interactions (Interacciones con IA)
-- ==========================================
CREATE TABLE IF NOT EXISTS ai_interactions (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    message_id VARCHAR(36),
    trip_id VARCHAR(36),
    driver_message TEXT NOT NULL,
    ai_classification VARCHAR(100),
    ai_confidence DECIMAL(5, 4),
    ai_response TEXT,
    model_used VARCHAR(100),
    prompt_used TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL,
    INDEX idx_message (message_id),
    INDEX idx_trip (trip_id),
    INDEX idx_classification (ai_classification),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: configurations (Configuraciones Dinámicas)
-- ==========================================
CREATE TABLE IF NOT EXISTS configurations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value JSON NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABLA: system_logs (Logs del Sistema)
-- ==========================================
CREATE TABLE IF NOT EXISTS system_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    level VARCHAR(20) NOT NULL,
    service VARCHAR(100),
    message TEXT NOT NULL,
    trace_id VARCHAR(100),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level (level),
    INDEX idx_service (service),
    INDEX idx_trace_id (trace_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- INSERTAR CONFIGURACIONES INICIALES
-- ==========================================
INSERT INTO configurations (config_key, config_value, description) VALUES
('ai_prompts', 
 '{
   "classify_driver_message": "Eres un asistente de IA...",
   "generate_response": "Genera una respuesta contextual..."
 }', 
 'Prompts para Gemini AI'),
 
('notification_templates',
 '{
   "trip_started": "Viaje iniciado correctamente",
   "geofence_entry": "Llegada a {geofence_name}",
   "trip_completed": "Viaje completado"
 }',
 'Templates de notificaciones'),
 
('business_rules',
 '{
   "max_trip_duration_hours": 24,
   "auto_complete_on_last_geofence": true,
   "require_qr_scan": true
 }',
 'Reglas de negocio del sistema')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);

-- ==========================================
-- VISTAS ÚTILES
-- ==========================================

-- Vista: Viajes activos con detalles
CREATE OR REPLACE VIEW active_trips_view AS
SELECT 
    t.id,
    t.floatify_trip_id,
    t.status,
    u.name AS unit_name,
    u.plate,
    d.name AS driver_name,
    d.phone AS driver_phone,
    t.whatsapp_group_name,
    t.created_at,
    t.trip_started_at
FROM trips t
LEFT JOIN units u ON t.unit_id = u.id
LEFT JOIN drivers d ON t.driver_id = d.id
WHERE t.status IN ('pending', 'in_progress', 'qr_scanned');

-- Vista: Resumen de eventos por viaje
CREATE OR REPLACE VIEW trip_events_summary AS
SELECT 
    t.id AS trip_id,
    t.floatify_trip_id,
    COUNT(DISTINCT e.id) AS total_events,
    COUNT(DISTINCT CASE WHEN e.event_type = 'geofence_entry' THEN e.id END) AS entries,
    COUNT(DISTINCT CASE WHEN e.event_type = 'geofence_exit' THEN e.id END) AS exits,
    MIN(e.event_time) AS first_event,
    MAX(e.event_time) AS last_event
FROM trips t
LEFT JOIN events e ON t.id = e.trip_id
GROUP BY t.id, t.floatify_trip_id;

-- ==========================================
-- FIN DEL SCHEMA
-- ==========================================

SELECT '✅ Base de datos MySQL creada correctamente!' AS status;
SELECT COUNT(*) AS total_tables FROM information_schema.tables WHERE table_schema = 'logistics_db';

