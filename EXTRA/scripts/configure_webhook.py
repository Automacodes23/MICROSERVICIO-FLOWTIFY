"""
Script para configurar el webhook de Evolution API
"""
import requests
import sys

# Configuración
EVOLUTION_API_URL = "https://n8n-evolution-api.xqrhao.easypanel.host"
EVOLUTION_API_KEY = "429683C4C977415CAAFCCE10F7D57E11"
EVOLUTION_INSTANCE_NAME = "SATECH-BOT"

# URL de tu ngrok
NGROK_URL = "https://postasthmatic-dicycly-veda.ngrok-free.dev"
WEBHOOK_URL = f"{NGROK_URL}/api/v1/whatsapp/messages"

def configure_webhook():
    """Configura el webhook en Evolution API"""
    
    print("=" * 60)
    print("CONFIGURACION DE WEBHOOK - EVOLUTION API")
    print("=" * 60)
    print(f"\n[INFO] Instance: {EVOLUTION_INSTANCE_NAME}")
    print(f"[INFO] Webhook URL: {WEBHOOK_URL}\n")
    
    # Endpoint para configurar webhook
    url = f"{EVOLUTION_API_URL}/webhook/set/{EVOLUTION_INSTANCE_NAME}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "webhook": {
            "url": WEBHOOK_URL,
            "enabled": True,
            "webhookByEvents": False,
            "webhookBase64": False,
            "events": [
                "MESSAGES_UPSERT"
            ]
        }
    }
    
    try:
        print("[1] Enviando configuracion...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"[2] Status code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("\n[OK] Webhook configurado exitosamente!")
            print(f"\n[RESPONSE] {response.text}\n")
            
            # Verificar configuración
            print("[3] Verificando configuracion...")
            verify_url = f"{EVOLUTION_API_URL}/webhook/find/{EVOLUTION_INSTANCE_NAME}"
            verify_response = requests.get(verify_url, headers=headers, timeout=30)
            
            if verify_response.status_code == 200:
                print(f"[OK] Configuracion actual:\n{verify_response.text}\n")
            
            print("=" * 60)
            print("LISTO PARA PROBAR")
            print("=" * 60)
            print("\n[SIGUIENTE PASO]")
            print("1. Ve a tu WhatsApp")
            print("2. Busca el grupo: 'Viaje E2E_FULL-20251103174307'")
            print("3. Envia: 'Empece a cargar'")
            print("4. El bot deberia responderte automaticamente\n")
            
        else:
            print(f"\n[ERROR] No se pudo configurar el webhook")
            print(f"[RESPONSE] {response.text}\n")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Error al conectar con Evolution API: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    configure_webhook()

