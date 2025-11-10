"""
Script de Limpieza Masiva de Grupos de WhatsApp
================================================

Este script saca al bot de todos los grupos de WhatsApp de prueba
y desactiva las conversaciones en la base de datos.

Útil para:
- Limpiar grupos después de pruebas E2E
- Evitar rate limits de WhatsApp
- Mantener limpia la lista de grupos

Uso:
    python scripts/cleanup_all_test_groups.py [opciones]

Opciones:
    --dry-run       : Solo muestra qué haría sin ejecutar
    --filter-test   : Solo limpia grupos que contengan "TEST" en el nombre
    --days N        : Solo limpia grupos creados en los últimos N días
    --confirm       : No pide confirmación (peligroso!)
"""

import requests
import sys
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Configurar codificación UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Intentar importar pymysql
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️  pymysql no está instalado. Instala con: pip install pymysql")
    sys.exit(1)

# Colores ANSI
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_URL = "http://localhost:8000/api/v1"

# Configuración de MySQL desde .env
def get_mysql_config() -> Dict[str, Any]:
    """Obtener configuración de MySQL desde .env"""
    mysql_config = {
        "host": "localhost",
        "port": 3307,
        "user": "root",
        "password": "",
        "database": "logistics_db"
    }
    
    env_file = ".env"
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("MYSQL_HOST="):
                        mysql_config["host"] = line.split("=", 1)[1].strip()
                    elif line.startswith("MYSQL_PORT="):
                        mysql_config["port"] = int(line.split("=", 1)[1].strip())
                    elif line.startswith("MYSQL_USER="):
                        mysql_config["user"] = line.split("=", 1)[1].strip()
                    elif line.startswith("MYSQL_PASSWORD="):
                        mysql_config["password"] = line.split("=", 1)[1].strip()
                    elif line.startswith("MYSQL_DATABASE="):
                        mysql_config["database"] = line.split("=", 1)[1].strip()
        except Exception as e:
            print(f"{Colors.WARNING}⚠️  Error leyendo .env: {e}{Colors.ENDC}")
    
    return mysql_config


# =============================================================================
# FUNCIONES DE BASE DE DATOS
# =============================================================================

def get_active_conversations(
    filter_test_only: bool = False, 
    days_limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Obtener todas las conversaciones activas de la base de datos
    
    Args:
        filter_test_only: Si True, solo devuelve conversaciones con "TEST" en el trip_id
        days_limit: Si se especifica, solo devuelve conversaciones creadas en los últimos N días
    
    Returns:
        Lista de conversaciones con trip_id, whatsapp_group_id, etc.
    """
    mysql_config = get_mysql_config()
    
    try:
        connection = pymysql.connect(
            host=mysql_config["host"],
            port=mysql_config["port"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            database=mysql_config["database"],
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection:
            with connection.cursor() as cursor:
                # Construir query base
                query = """
                    SELECT 
                        c.id as conversation_id,
                        c.trip_id,
                        c.whatsapp_group_id,
                        c.status,
                        c.created_at,
                        t.floatify_trip_id as trip_code
                    FROM conversations c
                    LEFT JOIN trips t ON c.trip_id = t.id
                    WHERE c.status = 'active' 
                    AND c.whatsapp_group_id IS NOT NULL
                """
                
                # Agregar filtro de fecha si se especifica
                if days_limit:
                    query += f" AND c.created_at >= DATE_SUB(NOW(), INTERVAL {days_limit} DAY)"
                
                # Agregar filtro de TEST si se especifica
                if filter_test_only:
                    query += " AND (t.floatify_trip_id LIKE '%TEST%' OR t.floatify_trip_id LIKE '%test%')"
                
                query += " ORDER BY c.created_at DESC"
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                return results
                
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error al consultar base de datos: {e}{Colors.ENDC}")
        sys.exit(1)


# =============================================================================
# FUNCIONES DE API
# =============================================================================

def cleanup_single_group(trip_id: str) -> tuple[bool, str]:
    """
    Llama al endpoint de cleanup para un trip_id específico
    
    Returns:
        (success: bool, message: str)
    """
    try:
        url = f"{BASE_URL}/trips/{trip_id}/cleanup_group"
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get("message", "Grupo limpiado exitosamente")
        else:
            error_detail = response.json() if response.text else {}
            error_msg = error_detail.get("error", {}).get("message", response.text)
            return False, f"Error {response.status_code}: {error_msg}"
            
    except requests.exceptions.Timeout:
        return False, "Timeout - el servidor no respondió a tiempo"
    except requests.exceptions.ConnectionError:
        return False, "Error de conexión - ¿está el servidor corriendo?"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"


def check_server_health() -> bool:
    """Verifica que el servidor esté corriendo"""
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/api/v1/health", timeout=5)
        return response.status_code == 200
    except:
        return False


# =============================================================================
# FUNCIONES DE UI
# =============================================================================

def print_header():
    """Imprime el encabezado del script"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("LIMPIEZA MASIVA DE GRUPOS DE WHATSAPP".center(80))
    print("=" * 80)
    print(f"{Colors.ENDC}\n")


def print_summary(conversations: List[Dict[str, Any]]):
    """Imprime un resumen de las conversaciones a limpiar"""
    print(f"{Colors.BOLD}CONVERSACIONES ENCONTRADAS:{Colors.ENDC}\n")
    print(f"{'#':<5} {'Trip Code':<25} {'Grupo WhatsApp':<30} {'Creado':<20}")
    print("-" * 80)
    
    for idx, conv in enumerate(conversations, 1):
        trip_code = conv.get('trip_code') or 'N/A'
        group_id = conv.get('whatsapp_group_id', 'N/A')
        created = conv.get('created_at', 'N/A')
        
        # Truncar si es muy largo
        if len(trip_code) > 24:
            trip_code = trip_code[:21] + "..."
        if len(group_id) > 29:
            group_id = group_id[:26] + "..."
        
        # Colorear filas de TEST
        color = Colors.OKCYAN if 'TEST' in trip_code.upper() else Colors.ENDC
        print(f"{color}{idx:<5} {trip_code:<25} {group_id:<30} {created}{Colors.ENDC}")
    
    print("-" * 80)
    print(f"\n{Colors.BOLD}Total: {len(conversations)} conversaciones{Colors.ENDC}\n")


def confirm_action(dry_run: bool, auto_confirm: bool) -> bool:
    """Pide confirmación al usuario"""
    if dry_run:
        print(f"{Colors.OKBLUE}[DRY RUN] No se realizarán cambios reales{Colors.ENDC}\n")
        return True
    
    if auto_confirm:
        print(f"{Colors.WARNING}[AUTO-CONFIRM] Procediendo sin confirmación...{Colors.ENDC}\n")
        return True
    
    print(f"{Colors.WARNING}{Colors.BOLD}⚠️  ADVERTENCIA:{Colors.ENDC}")
    print(f"  - El bot será expulsado de TODOS estos grupos")
    print(f"  - Las conversaciones se marcarán como inactivas")
    print(f"  - Esta acción NO es reversible fácilmente\n")
    
    response = input(f"{Colors.BOLD}¿Continuar? (escribe 'SI' para confirmar): {Colors.ENDC}").strip()
    
    return response == 'SI'


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """Función principal del script"""
    
    # Parsear argumentos simples
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    filter_test = '--filter-test' in args
    auto_confirm = '--confirm' in args
    
    # Obtener days_limit si existe
    days_limit = None
    for i, arg in enumerate(args):
        if arg == '--days' and i + 1 < len(args):
            try:
                days_limit = int(args[i + 1])
            except ValueError:
                print(f"{Colors.FAIL}❌ --days debe ser un número{Colors.ENDC}")
                sys.exit(1)
    
    # Mostrar ayuda si se solicita
    if '--help' in args or '-h' in args:
        print(__doc__)
        sys.exit(0)
    
    print_header()
    
    # 1. Verificar servidor
    print(f"{Colors.BOLD}[1/5] Verificando servidor...{Colors.ENDC}")
    if not check_server_health():
        print(f"{Colors.FAIL}❌ El servidor no está disponible en {BASE_URL}{Colors.ENDC}")
        print(f"   Asegúrate de que el servidor esté corriendo: uvicorn app.main:app")
        sys.exit(1)
    print(f"{Colors.OKGREEN}✓ Servidor activo{Colors.ENDC}\n")
    
    # 2. Obtener conversaciones
    print(f"{Colors.BOLD}[2/5] Obteniendo conversaciones de la base de datos...{Colors.ENDC}")
    if filter_test:
        print(f"{Colors.OKCYAN}   Filtro: Solo grupos con 'TEST' en el nombre{Colors.ENDC}")
    if days_limit:
        print(f"{Colors.OKCYAN}   Filtro: Solo últimos {days_limit} días{Colors.ENDC}")
    
    conversations = get_active_conversations(
        filter_test_only=filter_test,
        days_limit=days_limit
    )
    
    if not conversations:
        print(f"{Colors.WARNING}⚠️  No se encontraron conversaciones activas para limpiar{Colors.ENDC}")
        sys.exit(0)
    
    print(f"{Colors.OKGREEN}✓ {len(conversations)} conversaciones encontradas{Colors.ENDC}\n")
    
    # 3. Mostrar resumen
    print(f"{Colors.BOLD}[3/5] Resumen de conversaciones:{Colors.ENDC}\n")
    print_summary(conversations)
    
    # 4. Confirmar acción
    print(f"{Colors.BOLD}[4/5] Confirmación:{Colors.ENDC}\n")
    if not confirm_action(dry_run, auto_confirm):
        print(f"{Colors.WARNING}Operación cancelada por el usuario{Colors.ENDC}")
        sys.exit(0)
    
    # 5. Procesar limpieza
    print(f"\n{Colors.BOLD}[5/5] Procesando limpieza...{Colors.ENDC}\n")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for idx, conv in enumerate(conversations, 1):
        trip_id = conv['trip_id']
        trip_code = conv.get('trip_code', 'N/A')
        group_id = conv['whatsapp_group_id']
        
        print(f"[{idx}/{len(conversations)}] Procesando {trip_code}...", end=" ")
        
        if dry_run:
            print(f"{Colors.OKBLUE}[DRY RUN] Omitido{Colors.ENDC}")
            success_count += 1
        else:
            success, message = cleanup_single_group(trip_id)
            
            if success:
                print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")
                success_count += 1
            else:
                print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")
                error_count += 1
                errors.append({
                    "trip_code": trip_code,
                    "trip_id": trip_id,
                    "error": message
                })
    
    # Resumen final
    print(f"\n{Colors.BOLD}{'=' * 80}")
    print("RESUMEN FINAL".center(80))
    print(f"{'=' * 80}{Colors.ENDC}\n")
    
    if dry_run:
        print(f"{Colors.OKBLUE}[DRY RUN] No se realizaron cambios reales{Colors.ENDC}\n")
    
    print(f"  {Colors.OKGREEN}✓ Exitosos: {success_count}{Colors.ENDC}")
    print(f"  {Colors.FAIL}✗ Errores:   {error_count}{Colors.ENDC}")
    print(f"  {Colors.BOLD}Total:      {len(conversations)}{Colors.ENDC}\n")
    
    # Mostrar errores si los hay
    if errors:
        print(f"{Colors.WARNING}{Colors.BOLD}ERRORES DETALLADOS:{Colors.ENDC}\n")
        for err in errors:
            print(f"  • {err['trip_code']} (ID: {err['trip_id']})")
            print(f"    {Colors.FAIL}{err['error']}{Colors.ENDC}\n")
    
    # Recomendaciones
    if not dry_run and success_count > 0:
        print(f"{Colors.OKGREEN}{'=' * 80}")
        print(f"¡Limpieza completada exitosamente!")
        print(f"{'=' * 80}{Colors.ENDC}\n")
        print(f"{Colors.OKCYAN}💡 Recomendaciones:{Colors.ENDC}")
        print(f"  - Verifica que el bot haya salido de los grupos en WhatsApp")
        print(f"  - Revisa la base de datos: las conversaciones deben estar con status='inactive'")
        print(f"  - Ahora puedes crear nuevos grupos sin preocuparte por el rate limit\n")
    
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Operación cancelada por el usuario (Ctrl+C){Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.FAIL}{'=' * 80}")
        print(f"ERROR INESPERADO")
        print(f"{'=' * 80}{Colors.ENDC}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

