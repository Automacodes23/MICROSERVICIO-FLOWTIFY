-- ==========================================
-- MIGRACIÓN: Agregar columna substatus a trips
-- Fecha: 2025-11-03
-- Descripción: Agrega la columna substatus para manejar
--              los subestados del viaje (ej: cargando, 
--              descargando, en_ruta, etc.)
-- ==========================================

USE logistics_db;

-- Agregar columna substatus después de status
ALTER TABLE trips 
ADD COLUMN substatus VARCHAR(50) DEFAULT NULL AFTER status,
ADD INDEX idx_substatus (substatus);

-- Comentarios para documentación
ALTER TABLE trips 
MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'pending' 
COMMENT 'Estado principal del viaje: pending, en_ruta_carga, en_zona_carga, en_ruta_destino, en_zona_descarga, finalizado, cancelado';

ALTER TABLE trips 
MODIFY COLUMN substatus VARCHAR(50) DEFAULT NULL 
COMMENT 'Subestado detallado: esperando_inicio_carga, cargando, carga_completada, en_transito, esperando_inicio_descarga, descargando, descarga_completada';

-- Verificar que la columna se agregó correctamente
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM 
    INFORMATION_SCHEMA.COLUMNS
WHERE 
    TABLE_SCHEMA = 'logistics_db' 
    AND TABLE_NAME = 'trips'
    AND COLUMN_NAME IN ('status', 'substatus')
ORDER BY 
    ORDINAL_POSITION;

