#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar migración: Agregar grupos de WhatsApp a unidades

Este script:
1. Lee las credenciales de la base de datos del .env
2. Hace backup de la tabla units antes de modificarla
3. Aplica la migración
4. Verifica que se aplicó correctamente
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

def get_db_connection():
    """Obtener conexión a MySQL usando aiomysql"""
    try:
        import aiomysql
        import asyncio
        
        # Obtener credenciales del .env
        db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'db': os.getenv('MYSQL_DATABASE', 'logistics_db'),
            'charset': 'utf8mb4',
        }
        
        return db_config
    except ImportError:
        print("[ERROR] aiomysql no esta instalado")
        print("Instalando aiomysql...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiomysql"])
        return get_db_connection()


async def check_columns_exist(cursor):
    """Verificar si las columnas ya existen"""
    await cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'units' 
          AND COLUMN_NAME IN ('whatsapp_group_id', 'whatsapp_group_name')
    """)
    existing_columns = await cursor.fetchall()
    return [col[0] for col in existing_columns]


async def backup_units_table(cursor):
    """Hacer backup de la estructura de la tabla units"""
    backup_file = project_root / 'backup' / f'units_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    backup_file.parent.mkdir(exist_ok=True)
    
    # Obtener estructura de la tabla
    await cursor.execute("SHOW CREATE TABLE units")
    result = await cursor.fetchone()
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Backup de tabla units\n")
        f.write(f"-- Fecha: {datetime.now().isoformat()}\n\n")
        f.write(f"{result[1]};\n")
    
    print(f"[OK] Backup guardado en: {backup_file}")
    return backup_file


async def apply_migration(cursor, conn):
    """Aplicar la migración"""
    print("\n[MIGRACION] Aplicando cambios...")
    
    # 1. Agregar columnas
    print("  [1/3] Agregando columna whatsapp_group_id...")
    await cursor.execute("""
        ALTER TABLE units 
        ADD COLUMN whatsapp_group_id VARCHAR(255) DEFAULT NULL 
        COMMENT 'ID del grupo de WhatsApp reutilizable para todos los viajes de esta unidad'
    """)
    await conn.commit()
    print("        [OK] whatsapp_group_id agregada")
    
    print("  [2/3] Agregando columna whatsapp_group_name...")
    await cursor.execute("""
        ALTER TABLE units
        ADD COLUMN whatsapp_group_name VARCHAR(255) DEFAULT NULL
        COMMENT 'Nombre del grupo de WhatsApp de la unidad'
    """)
    await conn.commit()
    print("        [OK] whatsapp_group_name agregada")
    
    # 2. Agregar índice
    print("  [3/3] Creando indice idx_units_whatsapp_group...")
    await cursor.execute("""
        ALTER TABLE units
        ADD KEY idx_units_whatsapp_group (whatsapp_group_id)
    """)
    await conn.commit()
    print("        [OK] Indice creado")


async def verify_migration(cursor):
    """Verificar que la migración se aplicó correctamente"""
    print("\n[VERIFICACION] Verificando migracion...")
    
    # Verificar columnas
    await cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'units' 
          AND COLUMN_NAME IN ('whatsapp_group_id', 'whatsapp_group_name')
        ORDER BY COLUMN_NAME
    """)
    columns = await cursor.fetchall()
    
    print("\n  Columnas agregadas:")
    for col in columns:
        print(f"    [OK] {col[0]} - {col[1]} - Nullable: {col[2]}")
        print(f"         Comentario: {col[3]}")
    
    # Verificar índice
    await cursor.execute("""
        SHOW KEYS FROM units 
        WHERE Key_name = 'idx_units_whatsapp_group'
    """)
    indexes = await cursor.fetchall()
    
    if indexes:
        print(f"\n  Indice creado:")
        print(f"    [OK] idx_units_whatsapp_group")
    
    # Estadísticas
    await cursor.execute("""
        SELECT 
            COUNT(*) as total_units,
            COUNT(whatsapp_group_id) as units_with_group,
            COUNT(*) - COUNT(whatsapp_group_id) as units_without_group
        FROM units
    """)
    stats = await cursor.fetchone()
    
    print(f"\n  Estadisticas de la tabla units:")
    print(f"    Total de unidades: {stats[0]}")
    print(f"    Unidades con grupo: {stats[1]}")
    print(f"    Unidades sin grupo: {stats[2]}")


async def main():
    """Función principal"""
    print("=" * 60)
    print("APLICANDO MIGRACION: Grupos de WhatsApp por Unidad")
    print("=" * 60)
    
    try:
        import aiomysql
        
        # Obtener configuración
        db_config = get_db_connection()
        
        print(f"\n[DB] Conectando a base de datos...")
        print(f"     Host: {db_config['host']}:{db_config['port']}")
        print(f"     Database: {db_config['db']}")
        print(f"     User: {db_config['user']}")
        
        # Conectar
        conn = await aiomysql.connect(**db_config)
        cursor = await conn.cursor()
        
        print("     [OK] Conectado exitosamente")
        
        # Verificar si las columnas ya existen
        existing_columns = await check_columns_exist(cursor)
        
        if existing_columns:
            print(f"\n[ADVERTENCIA] Las siguientes columnas ya existen:")
            for col in existing_columns:
                print(f"   - {col}")
            
            response = input("\nDeseas continuar de todos modos? (s/n): ")
            if response.lower() != 's':
                print("\n[CANCELADO] Migracion cancelada por el usuario")
                cursor.close()
                conn.close()
                return
        
        # Hacer backup
        backup_file = await backup_units_table(cursor)
        
        # Aplicar migración
        await apply_migration(cursor, conn)
        
        # Verificar
        await verify_migration(cursor)
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[EXITO] MIGRACION APLICADA EXITOSAMENTE")
        print("=" * 60)
        print(f"\n[BACKUP] Guardado en: {backup_file}")
        print("\n[PROXIMOS PASOS]")
        print("   1. Reiniciar el servicio de la aplicacion")
        print("   2. Verificar logs en busca de errores")
        print("   3. Crear un viaje de prueba")
        print("\n[DOCUMENTACION]")
        print("   - Guia de despliegue: docs/DEPLOY_GRUPOS_UNIDAD.md")
        print("   - FAQ: docs/FAQ_GRUPOS_UNIDAD.md")
        print("   - Analisis completo: docs/ANALISIS_GRUPOS_POR_UNIDAD.md")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"\n[SOLUCION DE PROBLEMAS]")
        print(f"   1. Verifica las credenciales en el archivo .env")
        print(f"   2. Verifica que la base de datos este accesible")
        print(f"   3. Verifica que tienes permisos para ALTER TABLE")
        print(f"\n[DOCUMENTACION] docs/DEPLOY_GRUPOS_UNIDAD.md")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
