"""
Script simple para limpiar la base de datos sin confirmación interactiva
USO: python scripts/reset_database_force.py
"""
import sys
import os
import asyncio

# Agregar el directorio raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from app.core.database import db
from app.config import settings

TABLES = [
    "ai_interactions",
    "messages",
    "conversations",
    "events",
    "trip_geofences",
    "trips",
    "geofences",
    "drivers",
    "units",
    "system_logs",
    "configurations",
]

async def reset_database():
    """Ejecuta la limpieza de la base de datos."""
    print("\n" + "="*60)
    print("  LIMPIEZA DE BASE DE DATOS")
    print("="*60)
    print(f"\n[*] Host: {settings.mysql_host}:{settings.mysql_port}")
    print(f"[*] Database: {settings.mysql_database}")
    print(f"[*] Tablas: {len(TABLES)}\n")
    
    try:
        # Conectar
        print("[+] Conectando...")
        await db.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            database=settings.mysql_database,
            user=settings.mysql_user,
            password=settings.mysql_password,
            min_size=1,
            max_size=2
        )
        print("[OK] Conectado\n")
        
        # Deshabilitar foreign keys
        print("[+] Deshabilitando foreign key checks...")
        await db.execute("SET FOREIGN_KEY_CHECKS = 0")
        print("[OK]\n")
        
        # Limpiar tablas
        print("[+] Limpiando tablas:")
        success = 0
        errors = 0
        
        for table in TABLES:
            try:
                print(f"    - {table:25}", end=" ... ")
                await db.execute(f"TRUNCATE TABLE `{table}`")
                print("[OK]")
                success += 1
            except Exception as e:
                print(f"[ERROR]: {str(e)[:40]}")
                errors += 1
        
        # Rehabilitar foreign keys
        print("\n[+] Rehabilitando foreign key checks...")
        await db.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("[OK]\n")
        
        # Resumen
        print("="*60)
        print(f"[RESUMEN]")
        print(f"  Exitosas: {success}")
        print(f"  Errores:  {errors}")
        print("="*60 + "\n")
        
        if errors == 0:
            print("[OK] LIMPIEZA COMPLETADA EXITOSAMENTE\n")
            return True
        else:
            print("[WARNING] LIMPIEZA COMPLETADA CON ALGUNOS ERRORES\n")
            return False
            
    except Exception as e:
        print(f"\n[ERROR CRITICO]: {e}\n")
        return False
    finally:
        try:
            await db.disconnect()
        except:
            pass

async def verify():
    """Verifica que las tablas estén vacías."""
    print("\n" + "="*60)
    print("  VERIFICACION")
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
        for table in TABLES:
            try:
                count = await db.fetchval(f"SELECT COUNT(*) FROM `{table}`")
                status = "[OK] VACIA" if count == 0 else f"[!] {count} registros"
                print(f"    {table:25} {status}")
                if count > 0:
                    all_empty = False
            except Exception as e:
                print(f"    {table:25} [ERROR]: {str(e)[:30]}")
        
        print("\n" + "="*60)
        if all_empty:
            print("[OK] Todas las tablas estan vacias")
        else:
            print("[WARNING] Algunas tablas tienen datos")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"[ERROR]: {e}\n")
    finally:
        try:
            await db.disconnect()
        except:
            pass

async def main():
    """Función principal."""
    print("\n" + "="*60)
    print("  SCRIPT DE LIMPIEZA FORZADA DE BASE DE DATOS")
    print("  (Sin confirmacion interactiva)")
    print("="*60)
    
    # Ejecutar limpieza
    success = await reset_database()
    
    # Verificar
    if success:
        await verify()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CANCELADO]\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR]: {e}\n")
        sys.exit(1)

