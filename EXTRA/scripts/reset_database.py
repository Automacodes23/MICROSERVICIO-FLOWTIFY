"""
Script para reiniciar completamente la base de datos MySQL
⚠️ ADVERTENCIA: Este script ELIMINARÁ TODOS los datos de todas las tablas
"""
import sys
import os
import asyncio
from typing import List

# Agregar el directorio raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

try:
    from app.core.database import db
    from app.config import settings
    from app.core.logging import get_logger
except ImportError as e:
    print(f"[ERROR] Error al importar modulos: {e}")
    print("Asegurate de estar en el directorio correcto y tener las dependencias instaladas.")
    sys.exit(1)

logger = get_logger(__name__)

# ====================================================================
# LISTA DE TABLAS EN ORDEN CORRECTO (respetando foreign keys)
# ====================================================================
# El orden es crítico: primero las tablas sin dependencias (hijas),
# luego las que dependen de ellas (padres)
TABLES_TO_TRUNCATE: List[str] = [
    # Nivel 1: Tablas que dependen de todo (eliminar primero)
    "ai_interactions",      # Depende de messages y trips
    "messages",             # Depende de conversations y trips
    "conversations",        # Depende de trips
    "events",               # Depende de trips y units
    "trip_geofences",       # Depende de trips y geofences
    
    # Nivel 2: Tablas intermedias
    "trips",                # Depende de units, drivers
    "geofences",            # Independiente
    
    # Nivel 3: Tablas base
    "drivers",              # Independiente
    "units",                # Independiente
    
    # Nivel 4: Tablas de configuración
    "system_logs",          # Independiente
    "configurations",       # Independiente
]


async def reset_mysql_database() -> bool:
    """
    Ejecuta la limpieza completa de la base de datos MySQL.
    
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    print("\n" + "="*60)
    print("  REINICIO TOTAL DE BASE DE DATOS MySQL")
    print("="*60)
    print(f"[*] Host: {settings.mysql_host}")
    print(f"[*] Base de datos: {settings.mysql_database}")
    print(f"[*] Tablas a limpiar: {len(TABLES_TO_TRUNCATE)}")
    print("="*60)
    
    try:
        # Conectar a la base de datos
        print("\n[+] Conectando a MySQL...")
        await db.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            database=settings.mysql_database,
            user=settings.mysql_user,
            password=settings.mysql_password,
            min_size=1,
            max_size=2
        )
        print("[OK] Conexion establecida\n")
        
        # Deshabilitar verificación de foreign keys
        print("[+] Deshabilitando verificacion de foreign keys...")
        await db.execute("SET FOREIGN_KEY_CHECKS = 0")
        print("[OK] Foreign key checks deshabilitados\n")
        
        # Truncar cada tabla
        print("[+] Iniciando limpieza de tablas:\n")
        success_count = 0
        error_count = 0
        
        for table in TABLES_TO_TRUNCATE:
            try:
                print(f"   Limpiando tabla: {table:30}", end=" ... ")
                await db.execute(f"TRUNCATE TABLE `{table}`")
                print("[OK]")
                success_count += 1
            except Exception as e:
                print(f"[ERROR]: {str(e)[:50]}")
                error_count += 1
                logger.error(f"Error al truncar tabla {table}: {e}")
        
        # Rehabilitar verificación de foreign keys
        print("\n[+] Rehabilitando verificacion de foreign keys...")
        await db.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("[OK] Foreign key checks rehabilitados\n")
        
        # Resumen
        print("="*60)
        print(f"[OK] Tablas limpiadas exitosamente: {success_count}")
        if error_count > 0:
            print(f"[ERROR] Tablas con errores: {error_count}")
        print("="*60)
        
        return error_count == 0
        
    except Exception as e:
        print(f"\n[ERROR CRITICO]: {e}")
        logger.error(f"Error en reset_mysql_database: {e}")
        return False
    finally:
        # Cerrar conexión
        try:
            await db.disconnect()
            print("\n[+] Conexion cerrada")
        except Exception as e:
            print(f"[WARNING] Error al cerrar conexion: {e}")


async def verify_cleanup() -> None:
    """Verifica que todas las tablas estén vacías después de la limpieza."""
    print("\n" + "="*60)
    print("  VERIFICANDO LIMPIEZA")
    print("="*60 + "\n")
    
    try:
        await db.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            database=settings.mysql_database,
            user=settings.mysql_user,
            password=settings.mysql_password,
            min_size=1,
            max_size=2
        )
        
        all_empty = True
        for table in TABLES_TO_TRUNCATE:
            count = await db.fetchval(f"SELECT COUNT(*) FROM `{table}`")
            status = "[OK] VACIA" if count == 0 else f"[WARNING] TIENE {count} REGISTROS"
            print(f"   {table:30} {status}")
            if count > 0:
                all_empty = False
        
        print("\n" + "="*60)
        if all_empty:
            print("[OK] VERIFICACION EXITOSA: Todas las tablas estan vacias")
        else:
            print("[WARNING] ADVERTENCIA: Algunas tablas aun tienen datos")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"[ERROR] Error en verificacion: {e}")
    finally:
        await db.disconnect()


def confirm_action() -> bool:
    """
    Solicita confirmación al usuario antes de proceder.
    
    Returns:
        bool: True si el usuario confirma, False en caso contrario
    """
    print("\n" + "!"*60)
    print("  ADVERTENCIA CRITICA")
    print("!"*60 + "\n")
    print("Esta accion ELIMINARA PERMANENTEMENTE todos los datos de:")
    print("")
    for i, table in enumerate(TABLES_TO_TRUNCATE, 1):
        print(f"  {i:2}. {table}")
    print("")
    print("Esta operacion NO se puede deshacer.")
    print("Solo debes usar esto en entornos de DESARROLLO o PRUEBAS.")
    print("")
    print("="*60)
    
    confirmation = input("\nEstas SEGURO? Escribe 'ELIMINAR TODO' para confirmar: ").strip()
    
    return confirmation == "ELIMINAR TODO"


async def main():
    """Función principal del script."""
    print("\n")
    print("="*60)
    print("        SCRIPT DE REINICIO TOTAL DE BASE DE DATOS")
    print("="*60)
    
    # Solicitar confirmación
    if not confirm_action():
        print("\n[CANCELADO] Operacion CANCELADA por el usuario.")
        print("   No se realizaron cambios en la base de datos.\n")
        return
    
    print("\n[OK] Confirmacion recibida. Iniciando proceso de limpieza...\n")
    
    # Ejecutar limpieza
    success = await reset_mysql_database()
    
    if success:
        # Verificar limpieza
        verify = input("\nDeseas verificar que las tablas esten vacias? (s/n): ").strip().lower()
        if verify == 's':
            await verify_cleanup()
        
        print("\n[OK] PROCESO COMPLETADO EXITOSAMENTE")
        print("   La base de datos ha sido reiniciada.\n")
    else:
        print("\n[WARNING] PROCESO COMPLETADO CON ERRORES")
        print("   Revisa los logs para mas detalles.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[CANCELADO] Operacion interrumpida por el usuario.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}\n")
        sys.exit(1)

