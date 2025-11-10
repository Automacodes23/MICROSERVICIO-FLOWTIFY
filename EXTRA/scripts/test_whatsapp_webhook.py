"""
Script para probar el endpoint de WhatsApp directamente
"""
import requests
import json

# Payload simulado que Evolution API enviaría
payload = {
    "event": "messages.upsert",
    "instance": "SATECH-BOT",
    "data": {
        "key": {
            "remoteJid": "120363421223607812@g.us",  # ID del grupo
            "fromMe": False,
            "id": "TEST_MESSAGE_ID_" + str(int(__import__('time').time())),
            "participant": "5214771817823@s.whatsapp.net",  # Participant (standard field)
            "participantPn": "5214771817823"  # Phone number sin @s.whatsapp.net
        },
        "pushName": "Usuario Test",
        "message": {
            "conversation": "Hola bot, este es un mensaje de prueba"
        },
        "messageType": "conversation",
        "messageTimestamp": int(__import__('time').time())
    },
    "sender": "5214771817823@s.whatsapp.net"
}

print("=" * 80)
print("TEST DEL WEBHOOK DE WHATSAPP")
print("=" * 80)
print(f"\n[1] Payload a enviar:")
print(json.dumps(payload, indent=2))

# Test 1: Servidor local
print(f"\n[2] Probando servidor local...")
try:
    response = requests.post(
        "http://localhost:8000/api/v1/whatsapp/messages",
        json=payload,
        timeout=10
    )
    print(f"    Status Code: {response.status_code}")
    print(f"    Response: {response.text}")
    
    if response.status_code == 200:
        print("    [OK] Servidor local responde correctamente")
    else:
        print(f"    [ERROR] Status: {response.status_code}")
        
except Exception as e:
    print(f"    [ERROR] Error al conectar con servidor local: {e}")

# Test 2: A través de ngrok
print(f"\n[3] Probando a través de ngrok...")
try:
    response = requests.post(
        "https://postasthmatic-dicycly-veda.ngrok-free.dev/api/v1/whatsapp/messages",
        json=payload,
        timeout=10
    )
    print(f"    Status Code: {response.status_code}")
    print(f"    Response: {response.text[:200]}")
    
    if response.status_code == 200:
        print("    [OK] ngrok funciona correctamente")
    else:
        print(f"    [ERROR] Status: {response.status_code}")
        
except Exception as e:
    print(f"    [ERROR] Error al conectar con ngrok: {e}")

print("\n" + "=" * 80)
print("REVISA LOS LOGS DEL SERVIDOR AHORA")
print("=" * 80)
print("Deberías ver logs como:")
print("  - whatsapp_webhook_received")
print("  - whatsapp_message_received")
print("  - looking_for_conversation")
print("=" * 80 + "\n")

