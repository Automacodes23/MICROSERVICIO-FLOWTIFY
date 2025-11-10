"""
Script para probar si el endpoint del webhook está respondiendo
"""
import requests
import json

# URL de tu servidor (ngrok)
SERVER_URL = "https://postasthmatic-dicycly-veda.ngrok-free.dev"
WEBHOOK_ENDPOINT = f"{SERVER_URL}/api/v1/whatsapp/messages"

def test_endpoint():
    """Prueba si el endpoint está activo"""
    
    print("=" * 60)
    print("PRUEBA DE ENDPOINT DE WEBHOOK")
    print("=" * 60)
    print(f"\n[INFO] Probando: {WEBHOOK_ENDPOINT}\n")
    
    # Payload de prueba (simula un mensaje de Evolution API)
    test_payload = {
        "event": "messages.upsert",
        "instance": "SATECH-BOT",
        "data": {
            "key": {
                "remoteJid": "5214771817823@s.whatsapp.net",
                "fromMe": False,
                "id": "TEST123456789"
            },
            "message": {
                "conversation": "Prueba de conexión"
            },
            "messageType": "conversation",
            "messageTimestamp": 1699000000
        }
    }
    
    try:
        print("[1] Enviando petición de prueba...")
        response = requests.post(
            WEBHOOK_ENDPOINT,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"[2] Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("\n[OK] El servidor está respondiendo correctamente!")
            print(f"[RESPONSE] {response.text}\n")
        elif response.status_code == 404:
            print("\n[ERROR] El endpoint no existe (404)")
            print("[SOLUCION] Verifica que el servidor FastAPI esté corriendo\n")
        elif response.status_code == 502 or response.status_code == 503:
            print("\n[ERROR] El servidor no está disponible")
            print("[SOLUCION] Inicia el servidor con: python -m app.main\n")
        else:
            print(f"\n[WARNING] Status code inesperado: {response.status_code}")
            print(f"[RESPONSE] {response.text}\n")
            
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] No se pudo conectar al servidor")
        print("\n[POSIBLES CAUSAS]:")
        print("  1. El servidor FastAPI no está corriendo")
        print("  2. ngrok no está activo")
        print("  3. La URL de ngrok cambió\n")
        print("[SOLUCION]:")
        print("  1. Inicia FastAPI: python -m app.main")
        print("  2. Verifica ngrok: http://127.0.0.1:4040")
        print("  3. Actualiza la URL del webhook si cambió\n")
        
    except requests.exceptions.Timeout:
        print("\n[ERROR] El servidor tardó demasiado en responder")
        print("[SOLUCION] Revisa los logs del servidor FastAPI\n")
        
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}\n")

if __name__ == "__main__":
    test_endpoint()

