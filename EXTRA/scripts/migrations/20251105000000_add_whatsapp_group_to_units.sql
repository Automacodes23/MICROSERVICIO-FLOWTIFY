-- =====================================================
-- Migración: Agregar grupos de WhatsApp a unidades
-- Fecha: 2025-11-05
-- Descripción: Permite que cada unidad tenga un grupo
--              de WhatsApp permanente que se reutiliza
--              entre múltiples viajes
-- =====================================================

-- 1. Agregar columnas para grupo de WhatsApp en units
ALTER TABLE units 
ADD COLUMN whatsapp_group_id VARCHAR(255) DEFAULT NULL 
  COMMENT 'ID del grupo de WhatsApp reutilizable para todos los viajes de esta unidad',
ADD COLUMN whatsapp_group_name VARCHAR(255) DEFAULT NULL
  COMMENT 'Nombre del grupo de WhatsApp de la unidad';

-- 2. Agregar índice para búsquedas por grupo
ALTER TABLE units
ADD KEY idx_units_whatsapp_group (whatsapp_group_id);

-- 3. (OPCIONAL) Migrar grupos existentes de trips a units
-- NOTA: Esto solo debe ejecutarse si deseas migrar los grupos existentes
--       Descomenta las siguientes líneas solo si es necesario

/*
UPDATE units u
INNER JOIN (
    SELECT 
        unit_id,
        whatsapp_group_id,
        whatsapp_group_name,
        MIN(created_at) as first_trip
    FROM trips
    WHERE whatsapp_group_id IS NOT NULL
    GROUP BY unit_id, whatsapp_group_id, whatsapp_group_name
) t ON u.id = t.unit_id
SET 
    u.whatsapp_group_id = t.whatsapp_group_id,
    u.whatsapp_group_name = t.whatsapp_group_name,
    u.updated_at = NOW()
WHERE u.whatsapp_group_id IS NULL;
*/

-- 4. Verificar la migración
SELECT 
    COUNT(*) as total_units,
    COUNT(whatsapp_group_id) as units_with_group,
    COUNT(*) - COUNT(whatsapp_group_id) as units_without_group
FROM units;

-- =====================================================
-- Rollback (si es necesario deshacer los cambios)
-- =====================================================
/*
ALTER TABLE units
DROP COLUMN whatsapp_group_id,
DROP COLUMN whatsapp_group_name,
DROP KEY idx_units_whatsapp_group;
*/

