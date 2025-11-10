"""
Script para actualizar la URL del webhook en Evolution API
"""
import requests
import sys

# Configuración
EVOLUTION_API_URL = "https://n8n-evolution-api.xqrhao.easypanel.host"
EVOLUTION_API_KEY = "429683C4C977415CAAFCCE10F7D57E11"
EVOLUTION_INSTANCE_NAME = "SATECH-BOT"

# ⚠️ IMPORTANTE: Cambia esta URL si tu ngrok se reinicia o cambias de servidor
WEBHOOK_URL = "https://postasthmatic-dicycly-veda.ngrok-free.dev/api/v1/whatsapp/messages"

def update_webhook(new_url: str = None):
    """Actualiza la URL del webhook"""
    
    url_to_set = new_url or WEBHOOK_URL
    
    print("=" * 60)
    print("ACTUALIZAR URL DEL WEBHOOK")
    print("=" * 60)
    print(f"\n[INFO] Instance: {EVOLUTION_INSTANCE_NAME}")
    print(f"[INFO] Nueva URL: {url_to_set}\n")
    
    # Endpoint para configurar webhook
    url = f"{EVOLUTION_API_URL}/webhook/set/{EVOLUTION_INSTANCE_NAME}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Estructura correcta según la documentación de Evolution API
    payload = {
        "enabled": True,
        "url": url_to_set,
        "webhookByEvents": False,
        "webhookBase64": False,
        "events": [
            "MESSAGES_UPSERT",      # Mensaje nuevo recibido
            "MESSAGES_UPDATE",      # Mensaje actualizado
            "SEND_MESSAGE"          # Mensaje enviado
        ]
    }
    
    try:
        print("[1] Enviando actualizacion...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"[2] Status code: {response.status_code}\n")
        
        if response.status_code in [200, 201]:
            print("[OK] Webhook actualizado exitosamente!\n")
            
            # Verificar configuración
            print("[3] Verificando configuracion...")
            verify_url = f"{EVOLUTION_API_URL}/webhook/find/{EVOLUTION_INSTANCE_NAME}"
            verify_response = requests.get(verify_url, headers=headers, timeout=30)
            
            if verify_response.status_code == 200:
                import json
                print("\n[CONFIGURACION ACTUAL]")
                config = verify_response.json()
                print(f"  URL:     {config.get('url')}")
                print(f"  Enabled: {config.get('enabled')}")
                print(f"  Events:  {', '.join(config.get('events', []))}\n")
            
            print("=" * 60)
            print("[LISTO] Evolution API redireccionara los mensajes a:")
            print(f"        {url_to_set}")
            print("=" * 60)
            
        else:
            print(f"[ERROR] No se pudo actualizar el webhook")
            print(f"[RESPONSE] {response.text}\n")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error al conectar con Evolution API: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    # Puedes pasar una URL como argumento
    if len(sys.argv) > 1:
        custom_url = sys.argv[1]
        print(f"\n[INFO] URL personalizada detectada: {custom_url}\n")
        update_webhook(custom_url)
    else:
        update_webhook()

