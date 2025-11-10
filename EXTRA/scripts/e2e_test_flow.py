"""
Script de Test E2E - Flujo Completo de Viaje
=============================================

Este script simula el ciclo de vida completo de un viaje:
1. Creación del viaje (simula Floatify)
2. Inicio del viaje (simula escaneo QR)
3. Eventos de GPS (simula Wialon)
4. Interacciones manuales del conductor vía WhatsApp (usuario real)

El script se pausa en puntos clave esperando que el usuario
interactúe manualmente desde WhatsApp como si fuera el conductor.

Requisitos:
- Servidor corriendo en http://localhost:8000
- WhatsApp Web activo
- Evolution API configurada
- Librería requests instalada
"""

import requests
import sys
from datetime import datetime
import time
import json
import re
import os
import random


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_URL = "http://localhost:8000/api/v1"
TRIP_CODE = f"TEST_FLOW_{datetime.now().strftime('%Y%m%d%H%M%S')}"

# Configuración de WhatsApp
USER_PHONE = "+5214771817823"  # Número del usuario real
DRIVER_PHONE = "+5214775589835"  # Número del conductor de prueba

# Ngrok webhook para Evolution API
NGROK_WEBHOOK_URL = "https://postasthmatic-dicycly-veda.ngrok-free.dev"

# Archivo de log
LOG_FILE = "e2e_test_log.txt"
log_file_handle = None

# Configuración de base de datos (para búsqueda automática de trip_id)
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# Colores ANSI para terminal
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
# FUNCIONES HELPER - LOGGING
# =============================================================================

def init_log():
    """Inicializa el archivo de log (lo limpia si existe)"""
    global log_file_handle
    log_file_handle = open(LOG_FILE, 'w', encoding='utf-8')
    
    # Escribir encabezado
    header = f"""
{'='*80}
TEST E2E - FLUJO COMPLETO DE VIAJE
{'='*80}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Código de Viaje: {TRIP_CODE}
Usuario: {USER_PHONE}
Conductor: {DRIVER_PHONE}
Base URL: {BASE_URL}
{'='*80}

"""
    log_file_handle.write(header)
    log_file_handle.flush()


def log_to_file(message, level="INFO"):
    """Escribe mensaje en el archivo de log"""
    if log_file_handle:
        timestamp = datetime.now().strftime('%H:%M:%S')
        # Remover códigos ANSI del mensaje
        clean_message = re.sub(r'\033\[[0-9;]+m', '', str(message))
        log_file_handle.write(f"[{timestamp}] [{level}] {clean_message}\n")
        log_file_handle.flush()


def close_log():
    """Cierra el archivo de log"""
    if log_file_handle:
        log_file_handle.write(f"\n{'='*80}\n")
        log_file_handle.write(f"Log finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file_handle.write(f"{'='*80}\n")
        log_file_handle.close()


# =============================================================================
# FUNCIONES HELPER - WEBHOOK MONITORING (NUEVO)
# =============================================================================

def check_geofence_webhooks_detailed():
    """Verificación detallada SOLO de webhooks de geofence"""
    try:
        print(f"\n{Colors.BOLD}🔍 BÚSQUEDA ESPECÍFICA DE WEBHOOKS DE GEOFENCE:{Colors.ENDC}")
        
        # Buscar SOLO geofence_transition
        response = requests.get(
            f"{BASE_URL}/webhooks/delivery-log",
            params={"webhook_type": "geofence_transition", "limit": 20},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            
            if count > 0:
                print(f"{Colors.OKGREEN}✓ Encontrados {count} webhooks de geofence_transition{Colors.ENDC}")
                for log in data.get('logs', []):
                    payload = json.loads(log['payload']) if isinstance(log['payload'], str) else log['payload']
                    geo_data = payload.get('geofence', {})
                    print(f"  - {geo_data.get('name')} ({payload.get('transition_type')}) - {log['status']}")
                    log_to_file(f"Geofence webhook: {geo_data.get('name')} - {log['status']}", "GEOFENCE_WEBHOOK")
            else:
                print(f"{Colors.FAIL}✗ NO se encontraron webhooks de geofence_transition{Colors.ENDC}")
                print(f"{Colors.WARNING}  Esto indica que EventService.webhook_service probablemente es None{Colors.ENDC}")
                log_to_file("NO HAY webhooks de geofence_transition en la BD", "CRITICAL")
        
    except Exception as e:
        print(f"{Colors.WARNING}⚠ Error al buscar geofence webhooks: {e}{Colors.ENDC}")


def check_webhooks_sent(trip_id=None, fase_name="", expect_geofence=False):
    """
    Verifica los webhooks que se enviaron a Flowtify
    
    Args:
        trip_id: ID del viaje (opcional, para filtrar)
        fase_name: Nombre de la fase actual para contexto
        expect_geofence: Si True, alerta si NO hay webhooks de geofence
    """
    print(f"\n{Colors.OKCYAN}{'─'*80}")
    print(f"📡 VERIFICANDO WEBHOOKS ENVIADOS A FLOWTIFY {f'(Fase: {fase_name})' if fase_name else ''}")
    print(f"{'─'*80}{Colors.ENDC}")
    
    log_to_file(f"\n{'─'*80}", "WEBHOOK_CHECK")
    log_to_file(f"VERIFICANDO WEBHOOKS - {fase_name}", "WEBHOOK_CHECK")
    
    # Variables para tracking
    webhook_types_found = set()
    
    try:
        # 1. Obtener estadísticas generales
        stats_response = requests.get(f"{BASE_URL}/webhooks/stats", timeout=5)
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            
            print(f"\n📊 {Colors.BOLD}Estadísticas Generales:{Colors.ENDC}")
            print(f"   Total enviados: {Colors.OKGREEN}{stats['total_sent']}{Colors.ENDC}")
            print(f"   Total fallidos: {Colors.FAIL if stats['total_failed'] > 0 else Colors.OKGREEN}{stats['total_failed']}{Colors.ENDC}")
            print(f"   Success rate: {Colors.OKGREEN}{stats['success_rate']}%{Colors.ENDC}")
            print(f"   Pending retries: {stats['pending_retries']}")
            print(f"   DLQ size: {Colors.FAIL if stats['dlq_size'] > 0 else Colors.OKGREEN}{stats['dlq_size']}{Colors.ENDC}")
            
            log_to_file(f"Stats - Sent: {stats['total_sent']}, Failed: {stats['total_failed']}, Success: {stats['success_rate']}%", "WEBHOOK_STATS")
        
        # 2. Obtener logs de delivery (últimos 10 o filtrados por trip)
        params = {"limit": 10}
        if trip_id:
            params["trip_id"] = trip_id
        
        logs_response = requests.get(f"{BASE_URL}/webhooks/delivery-log", params=params, timeout=5)
        
        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            logs = logs_data.get("logs", [])
            
            if logs:
                print(f"\n📋 {Colors.BOLD}Webhooks Enviados{' para este viaje' if trip_id else ' (últimos 10)'}{Colors.ENDC}:")
                
                for log in logs:
                    webhook_type = log['webhook_type']
                    status = log['status']
                    retry_count = log['retry_count']
                    created_at = log['created_at']
                    
                    # Track tipos de webhooks encontrados
                    webhook_types_found.add(webhook_type)
                    
                    # Icono según status
                    if status == 'sent':
                        icon = f"{Colors.OKGREEN}✓{Colors.ENDC}"
                        status_text = f"{Colors.OKGREEN}{status}{Colors.ENDC}"
                    elif status == 'failed':
                        icon = f"{Colors.FAIL}✗{Colors.ENDC}"
                        status_text = f"{Colors.FAIL}{status}{Colors.ENDC}"
                    else:
                        icon = f"{Colors.WARNING}◯{Colors.ENDC}"
                        status_text = f"{Colors.WARNING}{status}{Colors.ENDC}"
                    
                    print(f"   {icon} {Colors.BOLD}{webhook_type}{Colors.ENDC}")
                    print(f"      Status: {status_text}")
                    print(f"      Created: {created_at}")
                    print(f"      Retries: {retry_count}")
                    
                    # Si falló, mostrar error
                    if status == 'failed' and log.get('last_error'):
                        print(f"      {Colors.FAIL}Error: {log['last_error'][:100]}{Colors.ENDC}")
                    
                    # Mostrar payload resumido
                    try:
                        payload = json.loads(log['payload']) if isinstance(log['payload'], str) else log['payload']
                        print(f"      Event: {payload.get('event', 'N/A')}")
                        
                        # Mostrar target URL
                        target_url = log.get('target_url', 'N/A')
                        print(f"      Target: {target_url}")
                    except:
                        pass
                    
                    print()
                    
                    log_to_file(f"Webhook: {webhook_type} - Status: {status} - Retries: {retry_count}", "WEBHOOK_LOG")
            else:
                print(f"\n{Colors.WARNING}⚠ No se encontraron webhooks{' para este viaje' if trip_id else ''}{Colors.ENDC}")
                log_to_file("No se encontraron webhooks", "WEBHOOK_CHECK")
        else:
            print(f"\n{Colors.WARNING}⚠ No se pudieron obtener logs de webhooks (Status: {logs_response.status_code}){Colors.ENDC}")
            log_to_file(f"Error al obtener logs de webhooks: {logs_response.status_code}", "WARNING")
        
        # 3. Verificar DLQ
        dlq_response = requests.get(f"{BASE_URL}/webhooks/dead-letter-queue", timeout=5)
        
        if dlq_response.status_code == 200:
            dlq_data = dlq_response.json()
            dlq_items = dlq_data.get("items", [])
            
            if dlq_items:
                print(f"\n{Colors.FAIL}⚠ ATENCIÓN: {len(dlq_items)} webhooks en Dead Letter Queue{Colors.ENDC}")
                for item in dlq_items[:5]:  # Mostrar máximo 5
                    print(f"   - {item['webhook_type']}: {item['failure_reason'][:80]}")
                log_to_file(f"DLQ tiene {len(dlq_items)} items", "WARNING")
        
        # ALERTA si se esperaba geofence pero no se encontró
        if expect_geofence and 'geofence_transition' not in webhook_types_found:
            print(f"\n{Colors.FAIL}{'='*80}")
            print(f"⚠️  ALERTA CRÍTICA: WEBHOOK DE GEOFENCE NO GENERADO")
            print(f"{'='*80}{Colors.ENDC}")
            print(f"{Colors.WARNING}Se esperaba un webhook de tipo 'geofence_transition' pero NO se encontró.{Colors.ENDC}")
            print(f"{Colors.WARNING}Tipos encontrados: {', '.join(webhook_types_found) if webhook_types_found else 'Ninguno'}{Colors.ENDC}")
            print(f"\n{Colors.BOLD}Causas posibles:{Colors.ENDC}")
            print(f"  1. EventService.webhook_service es None (no se inyectó correctamente)")
            print(f"  2. El código en EventService._send_webhooks_for_event() no se ejecuta")
            print(f"  3. Error silencioso al enviar el webhook de geofence")
            print(f"\n{Colors.BOLD}Solución:{Colors.ENDC}")
            print(f"  - Revisa los logs del servidor en busca de:")
            print(f"    * 'event_service_initialized' → ¿has_webhook_service es True?")
            print(f"    * 'whatsapp_notification_check' → se ejecuta al procesar geofence")
            print(f"    * 'event_webhook_check' → intenta enviar webhook")
            print(f"{Colors.FAIL}{'='*80}{Colors.ENDC}\n")
            
            log_to_file("ALERTA: Webhook de geofence NO generado cuando se esperaba", "CRITICAL")
            log_to_file(f"Tipos encontrados: {webhook_types_found}", "INFO")
        
        print(f"\n{Colors.OKCYAN}{'─'*80}{Colors.ENDC}\n")
        
    except requests.exceptions.Timeout:
        print(f"\n{Colors.WARNING}⚠ Timeout al verificar webhooks (endpoint puede no estar disponible){Colors.ENDC}\n")
        log_to_file("Timeout al verificar webhooks", "WARNING")
    except requests.exceptions.ConnectionError:
        print(f"\n{Colors.WARNING}⚠ No se pudo conectar al endpoint de webhooks{Colors.ENDC}\n")
        log_to_file("Error de conexión al verificar webhooks", "WARNING")
    except Exception as e:
        print(f"\n{Colors.WARNING}⚠ Error al verificar webhooks: {e}{Colors.ENDC}\n")
        log_to_file(f"Error al verificar webhooks: {e}", "ERROR")


# =============================================================================
# FUNCIONES HELPER - UI
# =============================================================================

def print_step(title, char="="):
    """Imprime un título de fase con formato destacado"""
    line = char * 80
    print(f"\n{Colors.OKBLUE}{line}")
    print(f"{title.center(80)}")
    print(f"{line}{Colors.ENDC}\n")
    
    # Escribir también en el log
    log_to_file(f"\n{line}")
    log_to_file(f"{title.center(80)}")
    log_to_file(f"{line}\n")


def wait_for_user(prompt_message):
    """Pausa la ejecución y espera input del usuario"""
    print(f"\n{Colors.WARNING}{Colors.BOLD}>>> {prompt_message}{Colors.ENDC}")
    log_to_file(f">>> {prompt_message}", "USER_ACTION")
    log_to_file("Esperando acción del usuario...", "PAUSE")
    input(f"{Colors.OKCYAN}Presiona Enter para continuar...{Colors.ENDC} ")
    log_to_file("Usuario confirmó. Continuando...", "RESUME")


def check_server():
    """Verifica que el servidor esté corriendo"""
    print(f"{Colors.BOLD}[CHECK] Verificando servidor...{Colors.ENDC}")
    log_to_file("[CHECK] Verificando servidor...", "CHECK")
    
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/api/v1/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"{Colors.OKGREEN}[OK] Servidor activo{Colors.ENDC}")
            print(f"  - Status: {data.get('status', 'unknown')}")
            print(f"  - Service: {data.get('service', 'unknown')}")
            print(f"  - Timestamp: {data.get('timestamp', 'unknown')}")
            
            log_to_file("[OK] Servidor activo", "SUCCESS")
            log_to_file(f"  - Status: {data.get('status', 'unknown')}")
            log_to_file(f"  - Service: {data.get('service', 'unknown')}")
            log_to_file(f"  - Timestamp: {data.get('timestamp', 'unknown')}")
            return True
        else:
            msg = f"✗ Servidor respondió con status {response.status_code}"
            print(f"{Colors.FAIL}{msg}{Colors.ENDC}")
            log_to_file(msg, "ERROR")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"{Colors.FAIL}✗ No se pudo conectar al servidor{Colors.ENDC}")
        print(f"  Error: {e}")
        print(f"\n{Colors.WARNING}Asegúrate de que el servidor esté corriendo en {BASE_URL}{Colors.ENDC}")
        log_to_file(f"✗ No se pudo conectar al servidor: {e}", "ERROR")
        sys.exit(1)


def get_mysql_config():
    """Obtener configuración de MySQL desde variables de entorno o .env"""
    # Intentar cargar desde .env si existe
    env_file = ".env"
    mysql_config = {
        "host": "localhost",
        "port": 3307,
        "user": "root",
        "password": "",
        "database": "logistics_db"
    }
    
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
            log_to_file(f"Error leyendo .env: {e}", "WARNING")
    
    return mysql_config


def search_trip_id_in_db(trip_code):
    """Buscar trip_id en la base de datos MySQL"""
    if not MYSQL_AVAILABLE:
        log_to_file("pymysql no disponible, no se puede buscar trip_id automáticamente", "WARNING")
        return None
    
    try:
        mysql_config = get_mysql_config()
        
        print(f"\n{Colors.OKCYAN}[AUTO] Buscando trip_id en la base de datos...{Colors.ENDC}")
        log_to_file(f"Intentando conectar a MySQL: {mysql_config['host']}:{mysql_config['port']}", "INFO")
        
        # Conectar a MySQL
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
                # Buscar el trip por código
                sql = "SELECT id FROM trips WHERE floatify_trip_id = %s ORDER BY created_at DESC LIMIT 1"
                cursor.execute(sql, (trip_code,))
                result = cursor.fetchone()
                
                if result:
                    trip_id = result['id']
                    print(f"{Colors.OKGREEN}[OK] Trip ID encontrado: {trip_id}{Colors.ENDC}")
                    log_to_file(f"Trip ID encontrado automáticamente: {trip_id}", "SUCCESS")
                    return trip_id
                else:
                    print(f"{Colors.WARNING}⚠ No se encontró el viaje en la BD{Colors.ENDC}")
                    log_to_file(f"No se encontró viaje con código: {trip_code}", "WARNING")
                    return None
    
    except Exception as e:
        print(f"{Colors.WARNING}⚠ Error al buscar en BD: {e}{Colors.ENDC}")
        log_to_file(f"Error al buscar trip_id en BD: {e}", "ERROR")
        return None


def check_webhook_config():
    """Verifica que el usuario haya configurado el webhook de Evolution API"""
    print(f"\n{Colors.BOLD}[CHECK] Configuración de Webhook Evolution API{Colors.ENDC}")
    print(f"\n{Colors.WARNING}IMPORTANTE:{Colors.ENDC} Para que el bot responda a tus mensajes,")
    print(f"Evolution API debe estar configurado con el siguiente webhook:")
    print(f"\n  {Colors.OKCYAN}{NGROK_WEBHOOK_URL}/api/v1/whatsapp/messages{Colors.ENDC}")
    print(f"\n¿Ya configuraste este webhook en Evolution API?")
    print(f"(Puedes usar el script: python scripts/configure_webhook.py)")
    
    log_to_file("[CHECK] Configuración de Webhook Evolution API", "CHECK")
    log_to_file(f"Webhook esperado: {NGROK_WEBHOOK_URL}/api/v1/whatsapp/messages")
    
    response = input(f"\n{Colors.BOLD}¿Webhook configurado correctamente? (s/n): {Colors.ENDC}").lower().strip()
    
    log_to_file(f"Usuario respondió: {response}", "USER_INPUT")
    
    if response != 's':
        print(f"\n{Colors.WARNING}Por favor, configura el webhook antes de continuar.{Colors.ENDC}")
        print(f"Ejecuta: {Colors.OKCYAN}python scripts/configure_webhook.py{Colors.ENDC}")
        log_to_file("Webhook no configurado. Test abortado.", "ERROR")
        sys.exit(0)
    else:
        log_to_file("Webhook confirmado como configurado", "SUCCESS")


def log_manual_interaction(trip_id, user_message_prompt, expected_status, expected_substatus):
    """
    Solicita al usuario enviar un mensaje, captura la respuesta del bot y 
    verifica el estado de la BD inmediatamente.
    
    Args:
        trip_id: ID del viaje
        user_message_prompt: Mensaje que el usuario debe enviar
        expected_status: Estado esperado después del mensaje
        expected_substatus: Subestado esperado después del mensaje
    """
    print(f"\n{Colors.WARNING}{Colors.BOLD}>>> ACCIÓN REQUERIDA:{Colors.ENDC}")
    print(f"{Colors.OKCYAN}    1. Envía este mensaje al grupo de WhatsApp:{Colors.ENDC}")
    print(f"       {Colors.BOLD}\"{user_message_prompt}\"{Colors.ENDC}")
    print(f"{Colors.OKCYAN}    2. Espera la respuesta del bot.{Colors.ENDC}")
    print(f"{Colors.OKCYAN}    3. Copia y pega la respuesta del bot aquí:{Colors.ENDC}")
    
    log_to_file(f">>> [USER_ACTION] Enviar mensaje: '{user_message_prompt}'", "USER_ACTION")
    
    # Capturar la respuesta del bot
    bot_response = input(f"\n{Colors.WARNING}Pega la respuesta del bot (o presiona Enter si no hubo respuesta): {Colors.ENDC}")
    
    # Loguear la interacción
    print(f"\n    {Colors.OKBLUE}{'='*70}{Colors.ENDC}")
    print(f"    {Colors.OKGREEN}[INTERACCIÓN] Mensaje Usuario: {user_message_prompt}{Colors.ENDC}")
    if bot_response.strip():
        print(f"    {Colors.OKGREEN}[INTERACCIÓN] Respuesta Bot:   {bot_response.strip()}{Colors.ENDC}")
    else:
        print(f"    {Colors.WARNING}[INTERACCIÓN] Sin respuesta del bot{Colors.ENDC}")
    print(f"    {Colors.OKBLUE}{'='*70}{Colors.ENDC}")
    
    log_to_file(f"[INTERACTION] Usuario envió: '{user_message_prompt}'", "INFO")
    if bot_response.strip():
        log_to_file(f"[INTERACTION] Bot respondió: '{bot_response.strip()}'", "INFO")
    else:
        log_to_file(f"[INTERACTION] Sin respuesta del bot", "WARNING")
    
    # Verificar la BD inmediatamente después de esta interacción
    check_db_status(trip_id, expected_status, expected_substatus, delay=1.0)


def check_messaging_db_status(trip_id, group_id, delay=1.0):
    """
    Consulta y muestra el estado de las tablas relacionadas con mensajería
    
    Args:
        trip_id: ID del viaje
        group_id: ID del grupo de WhatsApp
        delay: Segundos a esperar antes de consultar (default 1.0)
    """
    if not MYSQL_AVAILABLE:
        print(f"{Colors.WARNING}  [MESSAGING CHECK] pymysql no disponible.{Colors.ENDC}")
        return
    
    if delay > 0:
        time.sleep(delay)
    
    print(f"\n{Colors.OKCYAN}{'='*80}")
    print(f"  [MESSAGING CHECK] VERIFICANDO ESTADO DE MENSAJERÍA EN BD")
    print(f"{'='*80}{Colors.ENDC}")
    log_to_file(f"\n{'='*80}")
    log_to_file(f"MESSAGING CHECK - Trip: {trip_id}, Group: {group_id}")
    log_to_file(f"{'='*80}")
    
    try:
        mysql_config = get_mysql_config()
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
                # 1. Verificar UNIT
                print(f"\n{Colors.BOLD}  1. TABLA UNITS:{Colors.ENDC}")
                cursor.execute("""
                    SELECT u.id, u.name, u.whatsapp_group_id, u.whatsapp_group_name
                    FROM trips t
                    JOIN units u ON t.unit_id = u.id
                    WHERE t.id = %s
                """, (trip_id,))
                unit = cursor.fetchone()
                
                if unit:
                    has_group = bool(unit['whatsapp_group_id'])
                    status_icon = "✓" if has_group else "✗"
                    color = Colors.OKGREEN if has_group else Colors.FAIL
                    
                    print(f"    {color}{status_icon} Unit ID: {unit['id']}{Colors.ENDC}")
                    print(f"    {color}{status_icon} Unit Name: {unit['name']}{Colors.ENDC}")
                    print(f"    {color}{status_icon} WhatsApp Group ID: {unit['whatsapp_group_id'] or 'NULL'}{Colors.ENDC}")
                    print(f"    {color}{status_icon} WhatsApp Group Name: {unit['whatsapp_group_name'] or 'NULL'}{Colors.ENDC}")
                    
                    log_to_file(f"[UNIT] ID: {unit['id']}, Name: {unit['name']}")
                    log_to_file(f"[UNIT] WhatsApp Group ID: {unit['whatsapp_group_id'] or 'NULL'}")
                    log_to_file(f"[UNIT] WhatsApp Group Name: {unit['whatsapp_group_name'] or 'NULL'}")
                    
                    if not has_group:
                        print(f"    {Colors.WARNING}⚠ PROBLEMA: La unidad NO tiene whatsapp_group_id registrado{Colors.ENDC}")
                        log_to_file("[WARNING] Unidad sin whatsapp_group_id", "WARNING")
                else:
                    print(f"    {Colors.FAIL}✗ No se encontró la unidad{Colors.ENDC}")
                    log_to_file("[ERROR] Unidad no encontrada", "ERROR")
                
                # 2. Verificar CONVERSATIONS
                print(f"\n{Colors.BOLD}  2. TABLA CONVERSATIONS:{Colors.ENDC}")
                cursor.execute("""
                    SELECT id, trip_id, whatsapp_group_id, driver_id, status, created_at
                    FROM conversations
                    WHERE trip_id = %s
                """, (trip_id,))
                conversation = cursor.fetchone()
                
                if conversation:
                    print(f"    {Colors.OKGREEN}✓ Conversation ID: {conversation['id']}{Colors.ENDC}")
                    print(f"    {Colors.OKGREEN}✓ Group ID: {conversation['whatsapp_group_id']}{Colors.ENDC}")
                    print(f"    {Colors.OKGREEN}✓ Status: {conversation['status']}{Colors.ENDC}")
                    print(f"    {Colors.OKGREEN}✓ Created: {conversation['created_at']}{Colors.ENDC}")
                    
                    log_to_file(f"[CONVERSATION] ID: {conversation['id']}, Status: {conversation['status']}")
                    log_to_file(f"[CONVERSATION] Group ID: {conversation['whatsapp_group_id']}")
                else:
                    print(f"    {Colors.WARNING}⚠ NO HAY CONVERSATION REGISTRADA{Colors.ENDC}")
                    log_to_file("[WARNING] No hay conversation para este trip", "WARNING")
                
                # 3. Verificar MESSAGES
                print(f"\n{Colors.BOLD}  3. TABLA MESSAGES:{Colors.ENDC}")
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_messages,
                        SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as inbound_messages,
                        SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as outbound_messages,
                        MAX(created_at) as last_message_time
                    FROM messages
                    WHERE trip_id = %s
                """, (trip_id,))
                messages_stats = cursor.fetchone()
                
                if messages_stats and messages_stats['total_messages'] > 0:
                    print(f"    {Colors.OKGREEN}✓ Total Mensajes: {messages_stats['total_messages']}{Colors.ENDC}")
                    print(f"    {Colors.OKGREEN}  - Inbound (operador): {messages_stats['inbound_messages']}{Colors.ENDC}")
                    print(f"    {Colors.OKGREEN}  - Outbound (bot): {messages_stats['outbound_messages']}{Colors.ENDC}")
                    print(f"    {Colors.OKGREEN}✓ Último mensaje: {messages_stats['last_message_time']}{Colors.ENDC}")
                    
                    log_to_file(f"[MESSAGES] Total: {messages_stats['total_messages']}")
                    log_to_file(f"[MESSAGES] Inbound: {messages_stats['inbound_messages']}, Outbound: {messages_stats['outbound_messages']}")
                    
                    # Mostrar últimos 3 mensajes
                    cursor.execute("""
                        SELECT sender_type, direction, content, created_at
                        FROM messages
                        WHERE trip_id = %s
                        ORDER BY created_at DESC
                        LIMIT 3
                    """, (trip_id,))
                    recent_messages = cursor.fetchall()
                    
                    if recent_messages:
                        print(f"\n    {Colors.OKCYAN}Últimos mensajes:{Colors.ENDC}")
                        for msg in recent_messages:
                            direction_icon = "→" if msg['direction'] == 'outbound' else "←"
                            content_preview = (msg['content'][:50] + '...') if len(msg['content']) > 50 else msg['content']
                            print(f"      {direction_icon} [{msg['sender_type']}] {content_preview}")
                            log_to_file(f"[MESSAGE] {direction_icon} [{msg['sender_type']}] {msg['content'][:100]}")
                else:
                    print(f"    {Colors.FAIL}✗ NO HAY MENSAJES REGISTRADOS{Colors.ENDC}")
                    log_to_file("[ERROR] No hay mensajes en la tabla messages", "ERROR")
                
                # 4. Verificar AI_INTERACTIONS
                print(f"\n{Colors.BOLD}  4. TABLA AI_INTERACTIONS:{Colors.ENDC}")
                cursor.execute("""
                    SELECT COUNT(*) as total_interactions
                    FROM ai_interactions
                    WHERE trip_id = %s
                """, (trip_id,))
                ai_stats = cursor.fetchone()
                
                if ai_stats and ai_stats['total_interactions'] > 0:
                    print(f"    {Colors.OKGREEN}✓ Total Interacciones IA: {ai_stats['total_interactions']}{Colors.ENDC}")
                    log_to_file(f"[AI_INTERACTIONS] Total: {ai_stats['total_interactions']}")
                else:
                    print(f"    {Colors.WARNING}⚠ NO HAY INTERACCIONES DE IA{Colors.ENDC}")
                    log_to_file("[WARNING] No hay interacciones de IA registradas", "WARNING")
                
                # RESUMEN
                print(f"\n{Colors.OKCYAN}{'='*80}")
                print(f"  FIN MESSAGING CHECK")
                print(f"{'='*80}{Colors.ENDC}\n")
                log_to_file(f"{'='*80}\n")
                    
    except Exception as e:
        print(f"    {Colors.FAIL}✗ [ERROR] Error al consultar la BD: {e}{Colors.ENDC}")
        log_to_file(f"[ERROR] Error en messaging check: {e}", "ERROR")


def check_db_status(trip_id, expected_status, expected_substatus, delay=1.0):
    """
    Consulta la BD y muestra el estado actual del viaje
    
    Args:
        trip_id: ID del viaje a consultar
        expected_status: Estado esperado
        expected_substatus: Subestado esperado (puede ser None)
        delay: Segundos a esperar antes de consultar (default 1.0)
    """
    if not MYSQL_AVAILABLE:
        print(f"{Colors.WARNING}  [DB CHECK] pymysql no disponible. Omitiendo verificación de BD.{Colors.ENDC}")
        log_to_file("Omitiendo verificación de BD (pymysql no disponible)", "WARNING")
        return
    
    # Pequeño delay para asegurar que la transacción se completó
    if delay > 0:
        time.sleep(delay)
    
    print(f"\n{Colors.OKCYAN}  [DB CHECK] Verificando estado en Base de Datos...{Colors.ENDC}")
    log_to_file(f"Verificando BD para trip_id: {trip_id}")
    
    try:
        mysql_config = get_mysql_config()
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
                sql = "SELECT status, substatus FROM trips WHERE id = %s"
                cursor.execute(sql, (trip_id,))
                result = cursor.fetchone()
                
                if result:
                    actual_status = result['status']
                    actual_substatus = result['substatus']
                    
                    # Mostrar comparación
                    print(f"    {Colors.BOLD}Estado Esperado:   {expected_status} -> {expected_substatus or 'NULL'}{Colors.ENDC}")
                    log_to_file(f"Estado Esperado: {expected_status} -> {expected_substatus or 'NULL'}")
                    
                    # Comprobar Status
                    status_ok = actual_status == expected_status
                    if status_ok:
                        print(f"    {Colors.OKGREEN}✓ [OK] Status Actual:    {actual_status}{Colors.ENDC}")
                        log_to_file(f"[OK] Status Actual: {actual_status}")
                    else:
                        print(f"    {Colors.FAIL}✗ [FALLA] Status Actual:  {actual_status}{Colors.ENDC}")
                        log_to_file(f"[FALLA] Status Actual: {actual_status} (Esperado: {expected_status})", "ERROR")
                    
                    # Comprobar Substatus (manejo especial de NULL)
                    substatus_ok = actual_substatus == expected_substatus
                    if substatus_ok:
                        print(f"    {Colors.OKGREEN}✓ [OK] Substatus Actual: {actual_substatus or 'NULL'}{Colors.ENDC}")
                        log_to_file(f"[OK] Substatus Actual: {actual_substatus or 'NULL'}")
                    else:
                        print(f"    {Colors.FAIL}✗ [FALLA] Substatus Actual: {actual_substatus or 'NULL'}{Colors.ENDC}")
                        log_to_file(f"[FALLA] Substatus Actual: {actual_substatus or 'NULL'} (Esperado: {expected_substatus or 'NULL'})", "ERROR")
                    
                    # Resumen
                    if status_ok and substatus_ok:
                        print(f"\n    {Colors.OKGREEN}{'='*60}")
                        print(f"    ✓ VERIFICACIÓN BD: CORRECTA")
                        print(f"    {'='*60}{Colors.ENDC}")
                    else:
                        print(f"\n    {Colors.FAIL}{'='*60}")
                        print(f"    ✗ VERIFICACIÓN BD: DISCREPANCIA DETECTADA")
                        print(f"    {'='*60}{Colors.ENDC}")
                    
                else:
                    print(f"    {Colors.FAIL}✗ [FALLA] No se encontró el trip_id {trip_id} en la BD.{Colors.ENDC}")
                    log_to_file(f"[FALLA] No se encontró el trip_id {trip_id} en la BD.", "ERROR")
                    
    except Exception as e:
        print(f"    {Colors.FAIL}✗ [FALLA] Error al consultar la BD: {e}{Colors.ENDC}")
        log_to_file(f"[FALLA] Error al consultar la BD: {e}", "ERROR")


def make_request(method, endpoint, **kwargs):
    """
    Wrapper para requests con manejo de errores
    
    Returns:
        tuple: (success: bool, response_data: dict, status_code: int)
    """
    url = f"{BASE_URL}{endpoint}"
    
    try:
        print(f"\n{Colors.BOLD}[{method.upper()}] {endpoint}{Colors.ENDC}")
        log_to_file(f"\n[{method.upper()}] {endpoint}", "REQUEST")
        
        # Registrar datos de la petición
        if 'json' in kwargs:
            log_to_file(f"Payload (JSON):", "REQUEST")
            log_to_file(json.dumps(kwargs['json'], indent=2, ensure_ascii=False), "DATA")
        elif 'data' in kwargs:
            log_to_file(f"Payload (FORM):", "REQUEST")
            log_to_file(str(kwargs['data']), "DATA")
        
        response = requests.request(method, url, timeout=30, **kwargs)
        
        print(f"  Status: {response.status_code}")
        log_to_file(f"Status Code: {response.status_code}", "RESPONSE")
        
        # Intentar parsear JSON
        try:
            response_data = response.json()
            log_to_file(f"Response (JSON):", "RESPONSE")
            log_to_file(json.dumps(response_data, indent=2, ensure_ascii=False), "DATA")
        except:
            response_data = {"raw": response.text}
            log_to_file(f"Response (TEXT): {response.text[:500]}", "RESPONSE")
        
        success = 200 <= response.status_code < 300
        
        if success:
            print(f"{Colors.OKGREEN}  [OK] Request exitoso{Colors.ENDC}")
            log_to_file("[OK] Request exitoso", "SUCCESS")
        else:
            print(f"{Colors.WARNING}  ⚠ Request con status {response.status_code}{Colors.ENDC}")
            log_to_file(f"⚠ Request con status {response.status_code}", "WARNING")
        
        return success, response_data, response.status_code
        
    except requests.exceptions.RequestException as e:
        print(f"{Colors.FAIL}  ✗ Error en request: {e}{Colors.ENDC}")
        log_to_file(f"✗ Error en request: {e}", "ERROR")
        return False, {"error": str(e)}, 0


def print_payload(payload, title="Payload"):
    """Imprime un payload de forma legible"""
    print(f"\n{Colors.OKCYAN}[{title}]{Colors.ENDC}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def handle_error(phase, success, response_data, status_code):
    """Maneja errores de requests y pregunta si continuar"""
    if not success:
        print(f"\n{Colors.FAIL}{'='*80}")
        print(f"ERROR EN {phase}")
        print(f"{'='*80}{Colors.ENDC}")
        print(f"Status Code: {status_code}")
        print(f"Respuesta:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        log_to_file(f"\n{'='*80}", "ERROR")
        log_to_file(f"ERROR EN {phase}", "ERROR")
        log_to_file(f"{'='*80}", "ERROR")
        log_to_file(f"Status Code: {status_code}", "ERROR")
        log_to_file(f"Respuesta: {json.dumps(response_data, indent=2, ensure_ascii=False)}", "ERROR")
        
        print(f"\n{Colors.WARNING}Opciones:{Colors.ENDC}")
        print("  1. Continuar de todas formas")
        print("  2. Abortar test")
        
        choice = input(f"{Colors.BOLD}Selecciona (1/2): {Colors.ENDC}").strip()
        log_to_file(f"Usuario seleccionó opción: {choice}", "USER_INPUT")
        
        if choice == "2":
            print(f"\n{Colors.FAIL}Test abortado por el usuario.{Colors.ENDC}")
            log_to_file("Test abortado por el usuario", "ABORT")
            sys.exit(1)
        else:
            print(f"\n{Colors.WARNING}Continuando...{Colors.ENDC}")
            log_to_file("Usuario decidió continuar pese al error", "WARNING")


# =============================================================================
# FASE 1: CREACIÓN DE VIAJE (Simula Floatify)
# =============================================================================

def fase_1_crear_viaje():
    """Crear viaje desde Floatify"""
    print_step("FASE 1: CREACIÓN DE VIAJE (Simula Floatify)")
    
    # Construir payload completo según docs.txt
    payload = {
        "event": "whatsapp.group.create",
        "action": "create_group",
        "tenant_id": 24,
        "trip": {
            "id": 45,
            "code": TRIP_CODE,
            "status": "asignado",
            "planned_start": "2025-10-06T20:00:00-06:00",
            "planned_end": "2025-10-06T22:00:00-06:00",
            "origin": "León",
            "destination": "Jalisco"
        },
        "driver": {
            "id": 33,
            "name": "PRUEBA_FLOWTIFY",
            "phone": DRIVER_PHONE
        },
        "unit": {
            "id": 18,
            "floatify_unit_id": "18",  # ID de la unidad en Floatify
            "name": "Torton 309 41BB3T",
            "plate": "41BB3T",
            "wialon_id": "27538728",
            "imei": "863719067169228"
        },
        "customer": {
            "id": 6,
            "name": "Pañales Aurora"
        },
        "geofences": [
            {
                "role": "origin",
                "geofence_id": "685",
                "geofence_name": "PATIO TTU",
                "geofence_type": "circle",
                "order": 0
            },
            {
                "role": "loading",
                "geofence_id": "9001",
                "geofence_name": "CEDIS COPPEL LEON",
                "geofence_type": "polygon",
                "order": 1
            },
            {
                "role": "unloading",
                "geofence_id": "9002",
                "geofence_name": "BODEGA COPPEL JALISCO",
                "geofence_type": "polygon",
                "order": 2
            }
        ],
        "whatsapp_participants": [
            USER_PHONE,      # Usuario real - recibirá mensajes del bot
            DRIVER_PHONE     # Conductor de prueba
        ],
        "metadata": {
            "tipo": "Cliente",
            "modalidad": "Renta",
            "priority": "medium"
        }
    }
    
    print_payload(payload, "Creación de Viaje")
    
    # Enviar request
    success, response_data, status_code = make_request(
        "POST",
        "/trips/create",
        json=payload
    )
    
    # Verificar respuesta
    handle_error("FASE 1", success, response_data, status_code)
    
    # Extraer datos de respuesta (incluso si hubo error, puede que se haya creado)
    trip_id = response_data.get("trip_id")
    trip_code = response_data.get("trip_code", TRIP_CODE)  # Usar código generado si no viene en respuesta
    whatsapp_group_id = response_data.get("whatsapp_group_id")
    
    # Si no hay trip_id y el usuario decidió continuar, intentar búsqueda automática
    if not trip_id and not success:
        print(f"\n{Colors.WARNING}No se pudo obtener el trip_id de la respuesta.{Colors.ENDC}")
        print(f"Código del viaje: {Colors.BOLD}{trip_code}{Colors.ENDC}")
        
        # PASO 1: Intentar búsqueda automática en BD
        if MYSQL_AVAILABLE:
            print(f"\n{Colors.OKCYAN}Intentando búsqueda automática...{Colors.ENDC}")
            log_to_file("Iniciando búsqueda automática de trip_id en BD", "INFO")
            trip_id = search_trip_id_in_db(trip_code)
            
            if trip_id:
                print(f"\n{Colors.OKGREEN}[OK] Trip ID recuperado automáticamente: {trip_id}{Colors.ENDC}")
                log_to_file(f"Trip ID recuperado automáticamente: {trip_id}", "SUCCESS")
                # Continuar con el flujo
            else:
                print(f"\n{Colors.WARNING}No se pudo recuperar automáticamente.{Colors.ENDC}")
        else:
            print(f"\n{Colors.WARNING}pymysql no disponible para búsqueda automática.{Colors.ENDC}")
            print(f"Instala con: pip install pymysql")
        
        # PASO 2: Si aún no hay trip_id, opciones manuales
        if not trip_id:
            print(f"\n{Colors.BOLD}Opciones:{Colors.ENDC}")
            print("  1. Buscar trip_id manualmente (te daré el query SQL)")
            print("  2. Ingresar trip_id manualmente")
            print("  3. Abortar test")
            
            choice = input(f"\n{Colors.BOLD}Selecciona (1/2/3): {Colors.ENDC}").strip()
            log_to_file(f"Usuario seleccionó opción para trip_id: {choice}", "USER_INPUT")
            
            if choice == "1":
                print(f"\n{Colors.OKCYAN}Ejecuta este query en MySQL:{Colors.ENDC}")
                print(f"  SELECT id FROM trips WHERE floatify_trip_id = '{trip_code}' ORDER BY created_at DESC LIMIT 1;")
                trip_id_input = input(f"\n{Colors.BOLD}Ingresa el trip_id obtenido: {Colors.ENDC}").strip()
                if trip_id_input:
                    # Mantener como string (puede ser UUID o int)
                    trip_id = trip_id_input
                    log_to_file(f"Trip ID ingresado manualmente: {trip_id}", "USER_INPUT")
                else:
                    print(f"{Colors.FAIL}No se ingresó trip_id. Abortando.{Colors.ENDC}")
                    log_to_file("No se ingresó trip_id. Abortando.", "ABORT")
                    return None, None
            elif choice == "2":
                trip_id_input = input(f"\n{Colors.BOLD}Ingresa el trip_id: {Colors.ENDC}").strip()
                if trip_id_input:
                    # Mantener como string (puede ser UUID o int)
                    trip_id = trip_id_input
                    log_to_file(f"Trip ID ingresado manualmente: {trip_id}", "USER_INPUT")
                else:
                    print(f"{Colors.FAIL}No se ingresó trip_id. Abortando.{Colors.ENDC}")
                    log_to_file("No se ingresó trip_id. Abortando.", "ABORT")
                    return None, None
            else:
                print(f"{Colors.FAIL}Abortando test.{Colors.ENDC}")
                log_to_file("Usuario decidió abortar por falta de trip_id", "ABORT")
                return None, None
    
    print(f"\n{Colors.OKGREEN}{'='*80}")
    print(f"VIAJE CREADO EXITOSAMENTE")
    print(f"{'='*80}{Colors.ENDC}")
    print(f"  Trip ID: {Colors.BOLD}{trip_id}{Colors.ENDC}")
    print(f"  Trip Code: {Colors.BOLD}{trip_code}{Colors.ENDC}")
    print(f"  WhatsApp Group: {Colors.BOLD}{whatsapp_group_id}{Colors.ENDC}")
    print(f"  Participantes: {Colors.BOLD}{USER_PHONE}, {DRIVER_PHONE}{Colors.ENDC}")
    
    # Info sobre tipo de trip_id
    trip_id_type = "UUID" if isinstance(trip_id, str) and len(str(trip_id)) > 20 else "int"
    print(f"\n{Colors.OKCYAN}ℹ  Trip ID type: {trip_id_type}{Colors.ENDC}")
    
    # Verificar si el mensaje de bienvenida se envió
    welcome_message_sent = response_data.get("welcome_message_sent", False)
    if not welcome_message_sent:
        print(f"\n{Colors.WARNING}⚠️  ADVERTENCIA: El mensaje de bienvenida NO se envió{Colors.ENDC}")
        print(f"   Esto puede indicar un problema con Evolution API o WhatsApp")
        print(f"   El viaje se creó correctamente, pero el mensaje falló")
        log_to_file("⚠️ ADVERTENCIA: Mensaje de bienvenida NO enviado", "WARNING")
    else:
        print(f"\n{Colors.OKGREEN}[OK] Mensaje de bienvenida enviado correctamente{Colors.ENDC}")
        log_to_file("[OK] Mensaje de bienvenida enviado", "SUCCESS")
    
    wait_for_user(
        f"Viaje creado. Revisa tu WhatsApp ({USER_PHONE}):\n"
        f"  - Deberías ser agregado al grupo '{whatsapp_group_id}'\n"
        f"  - {'⚠️ PUEDE QUE NO VEAS' if not welcome_message_sent else 'Deberías ver'} un mensaje de bienvenida del bot\n"
        f"  - El mensaje debería mencionar el viaje '{trip_code}'\n"
        f"  - El grupo incluye a ambos participantes"
    )
    
    return trip_id, whatsapp_group_id


# =============================================================================
# FASE 2: INICIO DE VIAJE (Simula escaneo QR)
# =============================================================================

def fase_2_iniciar_viaje(trip_id):
    """Iniciar viaje (simula escaneo QR)"""
    print_step("FASE 2: INICIO DE VIAJE (Simula Escaneo QR)")
    
    print(f"Iniciando viaje con ID: {Colors.BOLD}{trip_id}{Colors.ENDC}")
    
    # Construir endpoint con parámetros de query
    endpoint = f"/trips/{trip_id}/status?status=en_ruta_carga&substatus=rumbo_a_zona_carga"
    
    success, response_data, status_code = make_request(
        "PUT",
        endpoint
    )
    
    handle_error("FASE 2", success, response_data, status_code)
    
    print(f"\n{Colors.OKGREEN}{'='*80}")
    print(f"VIAJE INICIADO")
    print(f"{'='*80}{Colors.ENDC}")
    print(f"  Estado: {Colors.BOLD}en_ruta_carga{Colors.ENDC}")
    print(f"  Subestado: {Colors.BOLD}rumbo_a_zona_carga{Colors.ENDC}")
    
    time.sleep(2)  # Pequeña pausa para simular tiempo real
    
    # NUEVO: Verificar webhooks enviados
    check_webhooks_sent(trip_id=trip_id, fase_name="FASE 2 - Inicio de Viaje")


# =============================================================================
# FASE 3: EVENTO WIALON - LLEGADA A CARGA
# =============================================================================

def fase_3_llegada_carga():
    """Simular llegada a zona de carga (evento Wialon)"""
    print_step("FASE 3: EVENTO WIALON - LLEGADA A ZONA DE CARGA")
    
    # Pequeña pausa para asegurar que el viaje esté completamente creado en BD
    print(f"{Colors.OKCYAN}[INFO] Esperando 2 segundos para asegurar consistencia de BD...{Colors.ENDC}")
    time.sleep(2)
    
    # DEBUG: Verificar que el viaje se encuentre correctamente
    print(f"{Colors.OKCYAN}[DEBUG] Verificando búsqueda de viaje activo...{Colors.ENDC}")
    debug_success, debug_data, debug_status = make_request(
        "GET",
        "/wialon/debug/trip/27538728"
    )
    
    if debug_success:
        print(f"  Unit found: {debug_data.get('unit_found')}")
        print(f"  Trip found: {debug_data.get('trip_found')}")
        if not debug_data.get('trip_found'):
            print(f"{Colors.WARNING}  ⚠ ADVERTENCIA: No se encontró viaje activo para wialon_unit_id=27538728{Colors.ENDC}")
            print(f"  Esto causará error 500 en el evento de Wialon")
    
    # Payload form-urlencoded (según docs.txt)
    notification_id = f"NOTIF_{int(time.time())}_{random.randint(1000, 9999)}"
    
    data = {
        "unit_name": "Torton 309 41BB3T",
        "unit_id": "27538728",
        "imei": "863719067169228",
        "latitude": 21.0505,
        "longitude": -101.7995,
        "altitude": 1796,
        "speed": 6.2,
        "course": 270,
        "address": "ZONA DE CARGA - PLANTA ACME, León, Gto., México",
        "pos_time": "2024-10-07 01:28:20",
        "driver_name": "PRUEBA FLOWTIFY",
        "driver_code": "29",
        "geofence_name": "PLANTA ACME - ZONA CARGA",
        "geofence_id": "9001",
        "notification_type": "geofence_entry",
        "notification_id": notification_id,
        "event_time": 1728280100
    }
    
    print_payload(data, "Evento Wialon (Entrada a Geocerca)")
    
    # IMPORTANTE: Usar data= para form-urlencoded, NO json=
    success, response_data, status_code = make_request(
        "POST",
        "/wialon/events",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    handle_error("FASE 3", success, response_data, status_code)
    
    print(f"\n{Colors.OKGREEN}[OK] Llegada a zona de carga simulada{Colors.ENDC}")
    
    # NUEVO: Verificar webhooks de geofence transition
    time.sleep(2)  # Esperar a que webhook se procese
    check_webhooks_sent(fase_name="FASE 3 - Llegada a Carga (Geofence Entry)", expect_geofence=True)
    
    # BÚSQUEDA ESPECÍFICA de geofence webhooks
    check_geofence_webhooks_detailed()
    
    wait_for_user(
        f"Evento de llegada a carga enviado.\n"
        f"  - Revisa WhatsApp\n"
        f"  - Deberías recibir un mensaje del bot preguntando si iniciaste la carga\n"
        f"  - Algo como: 'Llegaste a PLANTA ACME - ZONA CARGA. Ya iniciaste la carga?'"
    )


# =============================================================================
# FASE 4: INTERACCIÓN DEL USUARIO (CARGA)
# =============================================================================

def fase_4_interaccion_carga(trip_id, group_id):
    """Usuario envía mensajes simulando proceso de carga"""
    print_step("FASE 4: INTERACCIÓN DEL CONDUCTOR (Proceso de Carga)")
    
    print(f"{Colors.BOLD}ACCIÓN REQUERIDA DEL USUARIO{Colors.ENDC}\n")
    print(f"Ahora debes interactuar como el CONDUCTOR desde WhatsApp ({Colors.BOLD}{USER_PHONE}{Colors.ENDC}):")
    print()
    print(f"{Colors.OKCYAN}Envía los siguientes mensajes AL GRUPO DEL VIAJE:{Colors.ENDC}")
    print()
    print("  1️⃣  'esperando en el anden'")
    print("      → Espera respuesta del bot")
    print()
    print("  2️⃣  'ya empece a cargar'")
    print("      → Espera respuesta del bot")
    print()
    print("  3️⃣  'ya termine la carga'")
    print("      → Espera respuesta del bot")
    print()
    print(f"{Colors.WARNING}El bot de IA (Gemini) debería responder a cada mensaje.{Colors.ENDC}")
    print(f"{Colors.WARNING}Los mensajes deben enviarse desde tu número: {USER_PHONE}{Colors.ENDC}")
    
    wait_for_user(
        f"Confirma que has enviado los 3 mensajes y recibido las respuestas del bot."
    )
    
    # Verificar estado de mensajería después de la interacción
    check_messaging_db_status(trip_id, group_id, delay=2.0)
    
    # NUEVO: Verificar webhooks de communication_response
    check_webhooks_sent(trip_id=trip_id, fase_name="FASE 4 - Comunicación WhatsApp")


# =============================================================================
# FASE 5: EVENTO WIALON - SALIDA DE CARGA
# =============================================================================

def fase_5_salida_carga():
    """Simular salida de zona de carga (evento Wialon)"""
    print_step("FASE 5: EVENTO WIALON - SALIDA DE ZONA DE CARGA")
    
    # Payload form-urlencoded (salida de geocerca)
    notification_id = f"NOTIF_{int(time.time())}_{random.randint(1000, 9999)}"
    
    data = {
        "unit_name": "Torton 309 41BB3T",
        "unit_id": "27538728",
        "imei": "863719067169228",
        "latitude": 21.051,
        "longitude": -101.799,
        "altitude": 1796,
        "speed": 8.4,
        "course": 90,
        "address": "ZONA DE CARGA - PLANTA ACME, León, Gto., México",
        "pos_time": "2024-10-07 01:33:20",
        "driver_name": "PRUEBA FLOWTIFY",
        "driver_code": "29",
        "geofence_name": "PLANTA ACME - ZONA CARGA",
        "geofence_id": "9001",
        "notification_type": "geofence_exit",
        "notification_id": notification_id,
        "event_time": 1728280400
    }
    
    print_payload(data, "Evento Wialon (Salida de Geocerca)")
    
    success, response_data, status_code = make_request(
        "POST",
        "/wialon/events",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    handle_error("FASE 5", success, response_data, status_code)
    
    print(f"\n{Colors.OKGREEN}[OK] Salida de zona de carga simulada{Colors.ENDC}")
    print(f"  Estado esperado: {Colors.BOLD}en_ruta_destino{Colors.ENDC}")
    
    time.sleep(2)
    
    # NUEVO: Verificar webhooks de geofence exit
    check_webhooks_sent(fase_name="FASE 5 - Salida de Carga (Geofence Exit)", expect_geofence=True)
    
    # BÚSQUEDA ESPECÍFICA de geofence webhooks
    check_geofence_webhooks_detailed()


# =============================================================================
# FASE 6: EVENTO WIALON - LLEGADA A DESCARGA
# =============================================================================

def fase_6_llegada_descarga():
    """Simular llegada a zona de descarga (evento Wialon)"""
    print_step("FASE 6: EVENTO WIALON - LLEGADA A ZONA DE DESCARGA")
    
    # Payload form-urlencoded (entrada a geocerca de descarga)
    notification_id = f"NOTIF_{int(time.time())}_{random.randint(1000, 9999)}"
    
    data = {
        "unit_name": "Torton 309 41BB3T",
        "unit_id": "27538728",
        "imei": "863719067169228",
        "latitude": 20.6736,
        "longitude": -103.3444,
        "altitude": 1566,
        "speed": 5.5,
        "course": 180,
        "address": "BODEGA COPPEL JALISCO, Jalisco, México",
        "pos_time": "2024-10-07 03:15:30",
        "driver_name": "PRUEBA FLOWTIFY",
        "driver_code": "29",
        "geofence_name": "BODEGA COPPEL JALISCO",
        "geofence_id": "9002",
        "notification_type": "geofence_entry",
        "notification_id": notification_id,
        "event_time": 1728286530
    }
    
    print_payload(data, "Evento Wialon (Entrada a Geocerca de Descarga)")
    
    success, response_data, status_code = make_request(
        "POST",
        "/wialon/events",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    handle_error("FASE 6", success, response_data, status_code)
    
    print(f"\n{Colors.OKGREEN}[OK] Llegada a zona de descarga simulada{Colors.ENDC}")
    
    # NUEVO: Verificar webhooks de geofence entry
    time.sleep(2)
    check_webhooks_sent(fase_name="FASE 6 - Llegada a Descarga (Geofence Entry)", expect_geofence=True)
    
    # BÚSQUEDA ESPECÍFICA de geofence webhooks
    check_geofence_webhooks_detailed()
    
    wait_for_user(
        f"Evento de llegada a descarga enviado.\n"
        f"  - Revisa WhatsApp\n"
        f"  - Deberías recibir mensaje del bot pidiendo confirmación\n"
        f"  - Algo como: 'Llegaste a BODEGA COPPEL JALISCO. Confirma cuando inicies descarga.'"
    )


# =============================================================================
# FASE 7: INTERACCIÓN DEL USUARIO (CIERRE)
# =============================================================================

def fase_7_interaccion_cierre():
    """Usuario envía mensajes finalizando el viaje"""
    print_step("FASE 7: INTERACCIÓN DEL CONDUCTOR (Cierre de Viaje)")
    
    print(f"{Colors.BOLD}ACCIÓN REQUERIDA DEL USUARIO - FINALIZACIÓN{Colors.ENDC}\n")
    print(f"Ahora debes FINALIZAR el viaje desde WhatsApp ({Colors.BOLD}{USER_PHONE}{Colors.ENDC}):")
    print()
    print(f"{Colors.OKCYAN}Envía los siguientes mensajes AL GRUPO:{Colors.ENDC}")
    print()
    print("  1️⃣  'empezando a descargar'")
    print("      → Espera respuesta del bot")
    print()
    print("  2️⃣  'ya termine de descargar me voy'")
    print("      → El bot debería confirmar la finalización del viaje")
    print()
    print(f"{Colors.WARNING}El bot debería marcar el viaje como FINALIZADO.{Colors.ENDC}")
    print(f"{Colors.WARNING}Los mensajes deben enviarse desde tu número: {USER_PHONE}{Colors.ENDC}")
    
    wait_for_user(
        f"Confirma que:\n"
        f"  - Has enviado los 2 mensajes de finalización\n"
        f"  - Has recibido confirmación del bot de que el viaje terminó\n"
        f"  - El mensaje del bot debería decir algo como 'Viaje finalizado'"
    )
    
    # NUEVO: Verificar webhooks de communication_response
    check_webhooks_sent(fase_name="FASE 7 - Finalización WhatsApp")


# =============================================================================
# FASE 8: FINALIZACIÓN Y RESUMEN
# =============================================================================

def fase_8_finalizacion(trip_id, trip_code):
    """Mostrar resumen final del test"""
    print_step("FASE 8: PRUEBA E2E COMPLETADA", char="*")
    
    print(f"{Colors.OKGREEN}{Colors.BOLD}¡FLUJO E2E COMPLETADO EXITOSAMENTE!{Colors.ENDC}\n")
    log_to_file("¡FLUJO E2E COMPLETADO EXITOSAMENTE!", "SUCCESS")
    
    print(f"{Colors.BOLD}RESUMEN DEL VIAJE:{Colors.ENDC}")
    print(f"{'='*80}")
    print(f"  Código de Viaje: {Colors.OKCYAN}{trip_code}{Colors.ENDC}")
    print(f"  Trip ID: {Colors.OKCYAN}{trip_id}{Colors.ENDC}")
    print(f"  Estado Final: {Colors.OKGREEN}finalizado{Colors.ENDC}")
    print(f"{'='*80}\n")
    
    log_to_file("\nRESUMEN DEL VIAJE:", "SUMMARY")
    log_to_file(f"  Código de Viaje: {trip_code}", "SUMMARY")
    log_to_file(f"  Trip ID: {trip_id}", "SUMMARY")
    log_to_file(f"  Estado Final: finalizado", "SUMMARY")
    
    print(f"{Colors.BOLD}VERIFICACIONES SUGERIDAS:{Colors.ENDC}")
    print()
    print(f"  1. Consultar estado en base de datos:")
    print(f"     {Colors.OKCYAN}SELECT * FROM trips WHERE code = '{trip_code}';{Colors.ENDC}")
    print()
    print(f"  2. Revisar logs del sistema:")
    print(f"     {Colors.OKCYAN}python scripts/diagnose_bot.py{Colors.ENDC}")
    print()
    print(f"  3. Verificar mensajes en WhatsApp:")
    print(f"     - Revisa el historial completo del grupo")
    print(f"     - Verifica que todas las respuestas del bot fueron apropiadas")
    print()
    print(f"  4. Revisar eventos procesados:")
    print(f"     {Colors.OKCYAN}SELECT * FROM events WHERE trip_id = {trip_id} ORDER BY created_at;{Colors.ENDC}")
    print()
    
    # NUEVO: Resumen completo de webhooks del viaje
    print(f"\n{Colors.OKBLUE}{'='*80}")
    print(f"RESUMEN COMPLETO DE WEBHOOKS - TODO EL VIAJE")
    print(f"{'='*80}{Colors.ENDC}\n")
    check_webhooks_sent(trip_id=trip_id, fase_name="RESUMEN FINAL")
    
    # ¡NUEVA SECCIÓN DE LIMPIEZA!
    print(f"\n{Colors.OKBLUE}{'='*80}")
    print(f"LIMPIEZA AUTOMÁTICA DEL GRUPO")
    print(f"{'='*80}{Colors.ENDC}\n")
    
    print(f"{Colors.WARNING}¿Deseas que el bot abandone el grupo de WhatsApp de prueba?{Colors.ENDC}")
    print(f"Esto ayuda a evitar rate limits de WhatsApp en futuras pruebas.\n")
    
    response = input(f"{Colors.BOLD}Limpiar grupo ahora? (s/n): {Colors.ENDC}").lower().strip()
    log_to_file(f"Usuario respondió sobre limpieza: {response}", "USER_INPUT")
    
    if response == 's':
        print(f"\n{Colors.OKCYAN}[CLEANUP] Iniciando limpieza de grupo...{Colors.ENDC}")
        log_to_file("Iniciando limpieza de grupo", "CLEANUP")

        success, response_data, status_code = make_request(
            "POST",
            f"/trips/{trip_id}/cleanup_group"
        )

        if success:
            print(f"\n{Colors.OKGREEN}✓ Limpieza de grupo exitosa{Colors.ENDC}")
            print(f"   {response_data.get('message')}")
            log_to_file(f"Limpieza de grupo exitosa: {response_data.get('message')}", "SUCCESS")
        else:
            print(f"\n{Colors.WARNING}⚠ Falló la limpieza del grupo (Status: {status_code}){Colors.ENDC}")
            print(f"   Error: {json.dumps(response_data, indent=2)}")
            log_to_file(f"Falló la limpieza del grupo: {json.dumps(response_data)}", "WARNING")
            print(f"\n{Colors.OKCYAN}💡 Puedes limpiarlo después con:{Colors.ENDC}")
            print(f"   python scripts/cleanup_all_test_groups.py --filter-test")
    else:
        print(f"\n{Colors.OKCYAN}[INFO] Limpieza omitida{Colors.ENDC}")
        print(f"   Puedes limpiar después con: {Colors.BOLD}python scripts/cleanup_all_test_groups.py --filter-test{Colors.ENDC}")
        log_to_file("Usuario omitió la limpieza", "INFO")
    
    print(f"\n{Colors.OKGREEN}{'='*80}")
    print(f"Test E2E completado - Todos los pasos ejecutados")
    print(f"{'='*80}{Colors.ENDC}\n")


# =============================================================================
# MAIN - PUNTO DE ENTRADA
# =============================================================================

def main():
    """Ejecutar el flujo completo de test E2E"""
    
    # Inicializar log
    init_log()
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("TEST E2E - FLUJO COMPLETO DE VIAJE".center(80))
    print("=" * 80)
    print(f"{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}REQUISITOS PREVIOS:{Colors.ENDC}")
    print("  1. [OK] Servidor corriendo en http://localhost:8000")
    print("  2. [OK] WhatsApp Web activo en tu navegador")
    print("  3. [OK] Evolution API configurada correctamente")
    print("  4. [OK] Base de datos MySQL activa")
    print()
    print(f"{Colors.BOLD}PARTICIPANTES DEL TEST:{Colors.ENDC}")
    print(f"  - Usuario (tú): {Colors.OKCYAN}{USER_PHONE}{Colors.ENDC}")
    print(f"  - Conductor: {Colors.OKCYAN}{DRIVER_PHONE}{Colors.ENDC}")
    print()
    print(f"{Colors.WARNING}IMPORTANTE:{Colors.ENDC}")
    print("  - Este test requiere interacción manual desde WhatsApp")
    print("  - Debes tener tu teléfono cerca para enviar mensajes")
    print("  - El script se pausará en puntos clave esperando tu acción")
    print(f"  - Recibirás notificaciones en el número: {Colors.BOLD}{USER_PHONE}{Colors.ENDC}")
    print()
    print(f"{Colors.OKGREEN}[LOG] Archivo de log: {LOG_FILE}{Colors.ENDC}")
    print()
    
    log_to_file("INICIO DEL TEST E2E", "START")
    log_to_file("Requisitos previos listados al usuario")
    
    input(f"{Colors.BOLD}Presiona Enter cuando estés listo para comenzar...{Colors.ENDC} ")
    log_to_file("Usuario confirmó inicio del test", "USER_INPUT")
    
    # Verificar servidor
    check_server()
    
    # NUEVO: Verificar sistema de webhooks Flowtify
    print(f"\n{Colors.BOLD}[CHECK] Verificando sistema de webhooks Flowtify...{Colors.ENDC}")
    try:
        webhook_health = requests.get(f"{BASE_URL}/webhooks/health", timeout=5).json()
        print(f"   Status: {Colors.OKGREEN}{webhook_health.get('status')}{Colors.ENDC}")
        print(f"   URL configurada: {'✓' if webhook_health.get('has_target_url') else '✗'}")
        print(f"   Secret configurado: {'✓' if webhook_health.get('has_secret') else '✗'}")
        print(f"   Circuit Breaker: {webhook_health.get('circuit_breaker_state')}")
        
        if webhook_health.get('status') != 'healthy':
            print(f"\n{Colors.WARNING}⚠ NOTA: Webhooks a Flowtify NO están completamente configurados{Colors.ENDC}")
            print(f"   Los webhooks NO se enviarán a Flowtify, pero el script funcionará.")
            print(f"   Para habilitar: configura FLOWTIFY_WEBHOOK_URL en .env")
        else:
            print(f"\n{Colors.OKGREEN}✓ Webhooks a Flowtify están activos y funcionando{Colors.ENDC}")
            print(f"   Los eventos se enviarán automáticamente a Flowtify")
    except:
        print(f"{Colors.WARNING}⚠ No se pudo verificar webhooks (endpoint puede no estar disponible){Colors.ENDC}")
    
    # Verificar configuración de webhook Evolution API
    check_webhook_config()
    
    print(f"\n{Colors.OKCYAN}Código único de viaje para este test: {Colors.BOLD}{TRIP_CODE}{Colors.ENDC}\n")
    log_to_file(f"Código único de viaje: {TRIP_CODE}", "INFO")
    
    try:
        # FASE 1: Crear viaje
        trip_id, whatsapp_group_id = fase_1_crear_viaje()
        
        if trip_id is None:
            print(f"{Colors.FAIL}No se pudo crear el viaje. Abortando test.{Colors.ENDC}")
            sys.exit(1)
        
        # Verificar estado inicial en BD
        check_db_status(trip_id, "pending", None, delay=1.5)
        
        # CRÍTICO: Verificar que la unidad tenga el grupo de WhatsApp registrado
        print(f"\n{Colors.OKBLUE}{'='*80}")
        print(f"  [CHECK CRÍTICO] ¿Se guardó el grupo en la tabla units?")
        print(f"{'='*80}{Colors.ENDC}")
        check_messaging_db_status(trip_id, whatsapp_group_id, delay=2.0)
        
        # FASE 2: Iniciar viaje
        fase_2_iniciar_viaje(trip_id)
        
        # Verificar estado después de iniciar viaje
        check_db_status(trip_id, "en_ruta_carga", "rumbo_a_zona_carga")
        
        # FASE 3: Llegada a carga (Wialon)
        fase_3_llegada_carga()
        
        # Verificar estado después de llegada a carga
        check_db_status(trip_id, "en_zona_carga", "esperando_inicio_carga")
        
        # ===========================================================
        # FASE 4: Interacción usuario - Carga (GRANULAR)
        # ===========================================================
        print_step("FASE 4: INTERACCIÓN DEL CONDUCTOR (Proceso de Carga)")
        
        print(f"{Colors.BOLD}INSTRUCCIONES:{Colors.ENDC}")
        print(f"  Enviarás 3 mensajes simulando el proceso de carga.")
        print(f"  Después de cada mensaje, pegarás la respuesta del bot.")
        print(f"  El script verificará la BD después de cada interacción.\n")
        
        # Interacción 4.1: Esperando turno
        log_manual_interaction(
            trip_id,
            user_message_prompt="esperando en el anden",
            expected_status="en_zona_carga",
            expected_substatus="esperando_turno"  # Ajustar según tu implementación
        )
        
        # Interacción 4.2: Inicia carga
        log_manual_interaction(
            trip_id,
            user_message_prompt="ya empece a cargar",
            expected_status="en_zona_carga",
            expected_substatus="cargando"  # Ajustar según tu implementación
        )
        
        # Interacción 4.3: Termina carga
        log_manual_interaction(
            trip_id,
            user_message_prompt="ya termine la carga",
            expected_status="en_zona_carga",
            expected_substatus="carga_completada"
        )
        
        # Verificar estado completo de mensajería después de todas las interacciones de carga
        print(f"\n{Colors.OKCYAN}>>> Verificando estado de mensajería en BD...{Colors.ENDC}")
        check_messaging_db_status(trip_id, whatsapp_group_id, delay=2.0)
        
        # FASE 5: Salida de carga (Wialon)
        fase_5_salida_carga()
        
        # Verificar estado después de salida de carga
        check_db_status(trip_id, "en_ruta_destino", "rumbo_a_descarga")
        
        # FASE 6: Llegada a descarga (Wialon)
        fase_6_llegada_descarga()
        
        # Verificar estado después de llegada a descarga
        check_db_status(trip_id, "en_zona_descarga", "esperando_inicio_descarga")
        
        # ===========================================================
        # FASE 7: Interacción usuario - Cierre (GRANULAR)
        # ===========================================================
        print_step("FASE 7: INTERACCIÓN DEL CONDUCTOR (Cierre de Viaje)")
        
        print(f"{Colors.BOLD}INSTRUCCIONES:{Colors.ENDC}")
        print(f"  Enviarás 2 mensajes para finalizar el viaje.")
        print(f"  Después de cada mensaje, pegarás la respuesta del bot.")
        print(f"  El script verificará la BD después de cada interacción.\n")
        print(f"{Colors.WARNING}IMPORTANTE: Aquí es donde el bot debería finalizar el viaje.{Colors.ENDC}\n")
        
        # Interacción 7.1: Inicia descarga
        log_manual_interaction(
            trip_id,
            user_message_prompt="ya empece a descargar",
            expected_status="en_zona_descarga",
            expected_substatus="descargando"  # Verificaremos si se corrompe aquí
        )
        
        # Interacción 7.2: Termina descarga (AQUÍ DEBERÍA FINALIZAR)
        print(f"\n{Colors.BOLD}{Colors.WARNING}⚠️  MOMENTO CRÍTICO: Este mensaje debería finalizar el viaje{Colors.ENDC}\n")
        log_manual_interaction(
            trip_id,
            user_message_prompt="ya termine de descargar me voy",
            expected_status="finalizado",
            expected_substatus="descarga_completada"  # Esperamos que falle aquí
        )
        
        # Verificar estado completo de mensajería después de finalizar
        print(f"\n{Colors.OKCYAN}>>> Verificando estado FINAL de mensajería en BD...{Colors.ENDC}")
        check_messaging_db_status(trip_id, whatsapp_group_id, delay=2.0)
        
        # FASE 8: Finalización
        fase_8_finalizacion(trip_id, TRIP_CODE)
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrumpido por el usuario (Ctrl+C).{Colors.ENDC}")
        log_to_file("Test interrumpido por el usuario (Ctrl+C)", "INTERRUPT")
        close_log()
        sys.exit(0)
    
    except Exception as e:
        print(f"\n{Colors.FAIL}{'='*80}")
        print(f"ERROR INESPERADO")
        print(f"{'='*80}{Colors.ENDC}")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensaje: {e}")
        import traceback
        print(f"\n{Colors.WARNING}Traceback:{Colors.ENDC}")
        traceback.print_exc()
        
        log_to_file(f"\n{'='*80}", "ERROR")
        log_to_file("ERROR INESPERADO", "ERROR")
        log_to_file(f"{'='*80}", "ERROR")
        log_to_file(f"Tipo: {type(e).__name__}", "ERROR")
        log_to_file(f"Mensaje: {e}", "ERROR")
        log_to_file(f"Traceback: {traceback.format_exc()}", "ERROR")
        
        close_log()
        sys.exit(1)
    
    finally:
        # Asegurar que el log se cierre siempre
        close_log()
        print(f"\n{Colors.OKGREEN}[OK] Log guardado en: {LOG_FILE}{Colors.ENDC}\n")


if __name__ == "__main__":
    main()

