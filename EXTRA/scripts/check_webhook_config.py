"""
Script para ver la configuración actual del webhook
"""
import requests

# Configuración
EVOLUTION_API_URL = "https://n8n-evolution-api.xqrhao.easypanel.host"
EVOLUTION_API_KEY = "429683C4C977415CAAFCCE10F7D57E11"
EVOLUTION_INSTANCE_NAME = "SATECH-BOT"

def check_webhook():
    """Ver configuración actual del webhook"""
    
    print("=" * 60)
    print("VERIFICAR CONFIGURACION DE WEBHOOK")
    print("=" * 60)
    print(f"\n[INFO] Instance: {EVOLUTION_INSTANCE_NAME}\n")
    
    # Endpoint para ver webhook actual
    url = f"{EVOLUTION_API_URL}/webhook/find/{EVOLUTION_INSTANCE_NAME}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY
    }
    
    try:
        print("[1] Consultando configuracion actual...")
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"[2] Status code: {response.status_code}\n")
        
        if response.status_code == 200:
            print("[OK] Configuracion actual:")
            import json
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    check_webhook()

