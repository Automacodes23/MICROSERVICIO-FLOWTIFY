-- ==========================================
-- SCRIPT DIRECTO: Agregar substatus a trips
-- EJECUTAR DESDE MYSQL WORKBENCH O CLI
-- ==========================================

-- 1. Matar cualquier transacción pendiente
SHOW PROCESSLIST;
-- (Anota los IDs de procesos en logistics_db)
-- KILL <process_id>;

-- 2. Verificar si existe la columna
SELECT COUNT(*) as column_exists
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'logistics_db' 
AND TABLE_NAME = 'trips' 
AND COLUMN_NAME = 'substatus';

-- 3. Si no existe (column_exists = 0), ejecutar:
USE logistics_db;

ALTER TABLE trips 
ADD COLUMN substatus VARCHAR(50) DEFAULT NULL AFTER status,
ADD INDEX idx_substatus (substatus);

-- 4. Verificar que se agregó:
DESCRIBE trips;

-- 5. Ver las columnas status y substatus:
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'logistics_db' 
AND TABLE_NAME = 'trips'
AND COLUMN_NAME IN ('status', 'substatus');

