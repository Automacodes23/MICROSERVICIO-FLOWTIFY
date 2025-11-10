"""
Script para verificar que el servidor FastAPI sea accesible desde internet
"""
import requests
import time

PUBLIC_IP = "186.96.24.65"
PORT = 8000

def check_local_server():
    """Verificar que el servidor esté corriendo localmente"""
    try:
        response = requests.get(f"http://localhost:{PORT}/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Servidor corriendo localmente en puerto {PORT}")
            return True
        else:
            print(f"[ERROR] Servidor respondió con código: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No hay servidor corriendo en localhost:{PORT}")
        print(f"        Ejecuta: python -m app.main")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False


def check_public_access():
    """Verificar que el servidor sea accesible desde internet"""
    print(f"\n[INFO] Verificando acceso público desde {PUBLIC_IP}:{PORT}...")
    try:
        response = requests.get(f"http://{PUBLIC_IP}:{PORT}/health", timeout=10)
        if response.status_code == 200:
            print(f"[OK] Servidor accesible desde internet!")
            print(f"     URL pública: http://{PUBLIC_IP}:{PORT}")
            return True
        else:
            print(f"[WARNING] Servidor respondió con código: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al intentar conectar a {PUBLIC_IP}:{PORT}")
        print(f"[SOLUCION] Necesitas abrir el puerto {PORT} en tu router/firewall:")
        print(f"          1. Accede a la configuración de tu router (192.168.1.1 o 192.168.0.1)")
        print(f"          2. Busca 'Port Forwarding' o 'Reenvío de puertos'")
        print(f"          3. Agrega regla: Puerto {PORT} TCP -> IP local de esta PC")
        print(f"          4. También verifica el firewall de Windows")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se pudo conectar a {PUBLIC_IP}:{PORT}")
        print(f"[SOLUCION] Verifica:")
        print(f"          1. Router: Puerto {PORT} abierto y redirigido a tu PC")
        print(f"          2. Firewall de Windows: Permitir puerto {PORT}")
        print(f"          3. ISP: Algunos ISPs bloquean puertos, considera usar ngrok")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False


def main():
    print("=" * 70)
    print("  VERIFICACION DE ACCESO AL SERVIDOR")
    print("=" * 70)
    print(f"  IP Pública: {PUBLIC_IP}")
    print(f"  Puerto: {PORT}")
    print("=" * 70)
    print()
    
    # 1. Verificar servidor local
    if not check_local_server():
        print("\n[ACCION] Primero debes iniciar el servidor:")
        print("         cd C:\\Users\\capac\\OneDrive\\Escritorio\\SHOW-SERVICE")
        print("         python -m app.main")
        return
    
    # 2. Verificar acceso público
    time.sleep(1)
    public_ok = check_public_access()
    
    # 3. Resumen
    print("\n" + "=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    if public_ok:
        print("  [OK] Todo listo!")
        print(f"  Webhook URL: http://{PUBLIC_IP}:{PORT}/api/v1/whatsapp/messages")
    else:
        print("  [PENDIENTE] Necesitas abrir el puerto en tu router")
        print("  ALTERNATIVA: Usa ngrok para crear un túnel:")
        print("               1. Descarga ngrok: https://ngrok.com/download")
        print("               2. Ejecuta: ngrok http 8000")
        print("               3. Usa la URL https que te dé ngrok")
    print("=" * 70)


if __name__ == "__main__":
    main()

