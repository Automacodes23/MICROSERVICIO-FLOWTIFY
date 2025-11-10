-- ============================================================================
-- MIGRACIÓN INTEGRAL: Agregar todas las columnas faltantes
-- ============================================================================

USE logistics_db;

-- ============================================================================
-- TABLA: trips
-- ============================================================================

-- Agregar code (único identificador del viaje)
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS code VARCHAR(50) NULL AFTER id,
ADD UNIQUE INDEX idx_trips_code (code);

-- Agregar customer_id
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS customer_id VARCHAR(36) NULL AFTER floatify_trip_id;

-- Agregar origin y destination (JSON con detalles de origen/destino)
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS origin JSON NULL AFTER substatus,
ADD COLUMN IF NOT EXISTS destination JSON NULL AFTER origin;

-- Agregar started_at y completed_at
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS started_at TIMESTAMP NULL AFTER destination,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP NULL AFTER started_at;

-- ============================================================================
-- TABLA: units
-- ============================================================================

-- Agregar plates (placas del vehículo)
ALTER TABLE units 
ADD COLUMN IF NOT EXISTS plates VARCHAR(20) NULL AFTER name;

-- Agregar wialon_id
ALTER TABLE units 
ADD COLUMN IF NOT EXISTS wialon_id VARCHAR(50) NULL AFTER plates,
ADD UNIQUE INDEX idx_units_wialon_id (wialon_id);

-- ============================================================================
-- TABLA: drivers
-- ============================================================================

-- Agregar floatify_driver_id
ALTER TABLE drivers 
ADD COLUMN IF NOT EXISTS floatify_driver_id VARCHAR(50) NULL AFTER phone,
ADD UNIQUE INDEX idx_drivers_floatify_driver_id (floatify_driver_id);

-- ============================================================================
-- Verificación Final
-- ============================================================================

SELECT 'VERIFICACION FINAL' as paso;

SELECT 
    'trips' as tabla,
    COUNT(COLUMN_NAME) as columnas_totales
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'logistics_db' AND TABLE_NAME = 'trips';

SELECT 
    'units' as tabla,
    COUNT(COLUMN_NAME) as columnas_totales
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'logistics_db' AND TABLE_NAME = 'units';

SELECT 
    'drivers' as tabla,
    COUNT(COLUMN_NAME) as columnas_totales
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'logistics_db' AND TABLE_NAME = 'drivers';

-- ============================================================================
-- FIN DE LA MIGRACIÓN
-- ============================================================================

