-- ============================================================================
-- MIGRACIÓN: Agregar columnas faltantes a la tabla messages
-- ============================================================================
-- Este script agrega las columnas que el código espera pero no existen

USE logistics_db;

-- 1. Agregar trip_id
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS trip_id VARCHAR(36) NULL AFTER conversation_id,
ADD INDEX idx_messages_trip_id (trip_id);

-- 2. Agregar sender_type (valores: 'driver', 'admin', 'system', 'bot')
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS sender_type VARCHAR(20) NULL AFTER sender_name;

-- 3. Agregar direction (valores: 'inbound', 'outbound')
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS direction VARCHAR(20) NOT NULL DEFAULT 'inbound' AFTER sender_type;

-- 4. Agregar transcription (para mensajes de voz)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS transcription TEXT NULL AFTER content;

-- 5. Agregar ai_result (JSON con la respuesta de IA)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS ai_result JSON NULL AFTER transcription;

-- 6. Poblar sender_type basado en is_from_driver existente
UPDATE messages 
SET sender_type = CASE 
    WHEN is_from_driver = 1 THEN 'driver'
    ELSE 'admin'
END
WHERE sender_type IS NULL;

-- 7. Poblar direction basado en is_from_driver
UPDATE messages
SET direction = CASE
    WHEN is_from_driver = 1 THEN 'inbound'
    ELSE 'outbound'
END;

-- 8. Verificar resultado
SELECT 
    'messages' as tabla,
    COUNT(*) as total_registros,
    SUM(CASE WHEN trip_id IS NOT NULL THEN 1 ELSE 0 END) as con_trip_id,
    SUM(CASE WHEN sender_type IS NOT NULL THEN 1 ELSE 0 END) as con_sender_type,
    SUM(CASE WHEN direction IS NOT NULL THEN 1 ELSE 0 END) as con_direction
FROM messages;

-- ============================================================================
-- FIN DE LA MIGRACIÓN
-- ============================================================================

