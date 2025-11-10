"""
Script rápido para reiniciar la base de datos usando subprocess
Ejecuta el archivo SQL directamente sin necesidad de async/await
"""
import sys
import os
import subprocess
from pathlib import Path

def get_mysql_credentials():
    """Lee las credenciales de MySQL desde el archivo .env"""
    env_path = Path(__file__).parent.parent / ".env"
    
    credentials = {
        'host': '127.0.0.1',
        'port': '3306',
        'user': 'root',
        'password': '',
        'database': 'logistics_db'
    }
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        if key == 'MYSQL_HOST':
                            credentials['host'] = value
                        elif key == 'MYSQL_PORT':
                            credentials['port'] = value
                        elif key == 'MYSQL_USER':
                            credentials['user'] = value
                        elif key == 'MYSQL_PASSWORD':
                            credentials['password'] = value
                        elif key == 'MYSQL_DATABASE':
                            credentials['database'] = value
    
    return credentials


def confirm_action():
    """Solicita confirmación al usuario."""
    print("\n" + "="*60)
    print("⚠️  REINICIO TOTAL DE BASE DE DATOS MySQL")
    print("="*60)
    print("\nEsta acción ELIMINARÁ PERMANENTEMENTE todos los datos de:")
    print("  • Units (unidades)")
    print("  • Drivers (conductores)")
    print("  • Trips (viajes)")
    print("  • Messages (mensajes)")
    print("  • Conversations (conversaciones)")
    print("  • Events (eventos)")
    print("  • AI Interactions (interacciones IA)")
    print("  • Geofences (geocercas)")
    print("  • System Logs (logs)")
    print("  • Configurations (configuraciones)")
    print("\nEsta operación NO se puede deshacer.")
    print("="*60)
    
    confirmation = input("\n¿Confirmas la eliminación? Escribe 'SI ELIMINAR': ").strip()
    return confirmation == "SI ELIMINAR"


def execute_reset():
    """Ejecuta el script SQL de limpieza."""
    creds = get_mysql_credentials()
    sql_file = Path(__file__).parent / "reset_database_simple.sql"
    
    if not sql_file.exists():
        print(f"❌ Error: No se encuentra el archivo {sql_file}")
        return False
    
    print(f"\n🔌 Conectando a MySQL...")
    print(f"   Host: {creds['host']}:{creds['port']}")
    print(f"   Database: {creds['database']}")
    print(f"   User: {creds['user']}")
    
    # Construir comando MySQL
    cmd = [
        "mysql",
        f"--host={creds['host']}",
        f"--port={creds['port']}",
        f"--user={creds['user']}",
        f"--database={creds['database']}"
    ]
    
    if creds['password']:
        cmd.append(f"--password={creds['password']}")
    
    try:
        # Ejecutar el script SQL
        print("\n🗑️  Ejecutando limpieza...")
        with open(sql_file, 'r', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode == 0:
            print("✅ Limpieza ejecutada exitosamente")
            if result.stdout:
                print("\n📊 Resultado:")
                print(result.stdout)
            return True
        else:
            print(f"❌ Error al ejecutar limpieza:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ Error: MySQL no está instalado o no está en el PATH")
        print("   Opciones:")
        print("   1. Instala MySQL client")
        print("   2. Usa phpMyAdmin para ejecutar el SQL manualmente")
        print("   3. Usa el script reset_database.py (Python asíncrono)")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Error: Timeout al ejecutar el script (>30s)")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def main():
    """Función principal."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║  🔥 SCRIPT RÁPIDO DE REINICIO DE BASE DE DATOS 🔥        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    if not confirm_action():
        print("\n❌ Operación CANCELADA\n")
        return
    
    print("\n✅ Confirmación recibida\n")
    
    success = execute_reset()
    
    if success:
        print("\n✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("   La base de datos ha sido reiniciada.\n")
    else:
        print("\n⚠️  PROCESO COMPLETADO CON ERRORES")
        print("   Revisa los mensajes anteriores.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación interrumpida por el usuario.\n")
        sys.exit(1)

