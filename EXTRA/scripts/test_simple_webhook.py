"""
Test ultra simple del webhook - paso por paso
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 80)
print("TEST SIMPLE DEL WEBHOOK")
print("=" * 80)

# Usar el grupo del último viaje (más reciente)
GROUP_ID = "120363404629424294@g.us"  # Del último viaje activo

payload = {
    "event": "messages.upsert",
    "instance": "SATECH-BOT",
    "data": {
        "key": {
            "remoteJid": GROUP_ID,
            "fromMe": False,
            "id": "TEST_MSG_123",
            "participantPn": "5214771817823"
        },
        "pushName": "Test User",
        "message": {
            "conversation": "Test message"
        },
        "messageType": "conversation",
        "messageTimestamp": 1762273400
    },
    "sender": "5214771817823@s.whatsapp.net"
}

print(f"\n[TEST] Enviando mensaje al grupo: {GROUP_ID}")
print(f"[TEST] Texto: 'Test message'\n")

try:
    response = requests.post(
        f"{BASE_URL}/whatsapp/messages",
        json=payload,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200:
        print("\n[OK] Webhook funciona correctamente")
    else:
        print(f"\n[ERROR] Webhook fallo con status {response.status_code}")
        print("\n[ACCION] Revisa los logs del servidor para ver el error detallado")
        print("Busca el trace_id en los logs del servidor")
        
except Exception as e:
    print(f"\n[ERROR] Excepcion: {e}")

print("\n" + "=" * 80)

