-- ====================================================================
-- Script SQL para reiniciar completamente la base de datos MySQL
-- ⚠️ ADVERTENCIA: Este script ELIMINARÁ TODOS los datos
-- ====================================================================
-- USO: Ejecutar directamente en phpMyAdmin o MySQL Workbench
-- O desde terminal: mysql -u root -p logistics_db < scripts/reset_database_simple.sql
-- ====================================================================

-- Deshabilitar verificación de foreign keys
SET FOREIGN_KEY_CHECKS = 0;

-- Limpiar todas las tablas (orden respetando dependencias)
TRUNCATE TABLE `ai_interactions`;
TRUNCATE TABLE `messages`;
TRUNCATE TABLE `conversations`;
TRUNCATE TABLE `events`;
TRUNCATE TABLE `trip_geofences`;
TRUNCATE TABLE `trips`;
TRUNCATE TABLE `geofences`;
TRUNCATE TABLE `drivers`;
TRUNCATE TABLE `units`;
TRUNCATE TABLE `system_logs`;
TRUNCATE TABLE `configurations`;

-- Rehabilitar verificación de foreign keys
SET FOREIGN_KEY_CHECKS = 1;

-- Verificación: Contar registros en cada tabla
SELECT 
    'ai_interactions' as tabla, 
    COUNT(*) as registros 
FROM `ai_interactions`
UNION ALL
SELECT 'messages', COUNT(*) FROM `messages`
UNION ALL
SELECT 'conversations', COUNT(*) FROM `conversations`
UNION ALL
SELECT 'events', COUNT(*) FROM `events`
UNION ALL
SELECT 'trip_geofences', COUNT(*) FROM `trip_geofences`
UNION ALL
SELECT 'trips', COUNT(*) FROM `trips`
UNION ALL
SELECT 'geofences', COUNT(*) FROM `geofences`
UNION ALL
SELECT 'drivers', COUNT(*) FROM `drivers`
UNION ALL
SELECT 'units', COUNT(*) FROM `units`
UNION ALL
SELECT 'system_logs', COUNT(*) FROM `system_logs`
UNION ALL
SELECT 'configurations', COUNT(*) FROM `configurations`;

-- Si todos muestran 0, la limpieza fue exitosa

