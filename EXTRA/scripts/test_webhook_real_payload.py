"""
Test del webhook con payload REAL de Evolution API (ajustado para grupo)
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

# Usar el grupo del último viaje
GROUP_ID = "120363423044511726@g.us"  # Del último viaje activo

# Payload REAL de Evolution API, ajustado para mensaje de grupo
payload = {
    "event": "messages.upsert",
    "instance": "SATECH-BOT",
    "data": {
        "key": {
            "remoteJid": GROUP_ID,  # ✅ ID del GRUPO
            "fromMe": False,
            "id": f"TEST_MSG_{int(time.time())}",
            "senderLid": "133857336623289@lid",  # Del payload real
            "participant": "5214771817823@s.whatsapp.net"  # Quién envió el mensaje
        },
        "pushName": "AutomaCode",
        "status": "DELIVERY_ACK",
        "message": {
            "conversation": "esperando en el anden",
            "messageContextInfo": {
                "deviceListMetadata": {
                    "senderKeyHash": "FNDfhhodSFbOCQ==",
                    "senderTimestamp": "1761085110",
                    "senderAccountType": "E2EE",
                    "receiverAccountType": "E2EE",
                    "recipientKeyHash": "Hf8OEBxWdxdZXw==",
                    "recipientTimestamp": "1761595140"
                },
                "deviceListMetadataVersion": 2,
                "messageSecret": "TIagEJbtuF6NdGK3ZMuMTnL9sOHX5oKkJDyBwfk7p4A=",
                "limitSharingV2": {
                    "trigger": "UNKNOWN",
                    "initiatedByMe": False
                }
            }
        },
        "messageType": "conversation",
        "messageTimestamp": int(time.time()),
        "instanceId": "7697f881-ec18-4d06-85c5-f492140ec471",
        "source": "web"
    },
    "destination": "https://postasthmatic-dicycly-veda.ngrok-free.dev/api/v1/whatsapp/messages",
    "date_time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "sender": "5214771817823@s.whatsapp.net",
    "server_url": "https://n8n-evolution-api.xqrhao.easypanel.host",
    "apikey": "69860FD49CEA-42EF-A9A2-138B8494DD24"
}

print("=" * 80)
print("TEST DEL WEBHOOK - PAYLOAD REAL DE EVOLUTION API")
print("=" * 80)

print(f"\n[INFO] Grupo: {GROUP_ID}")
print(f"[INFO] Mensaje: 'esperando en el anden'")
print(f"[INFO] Sender: 5214771817823@s.whatsapp.net")

print("\n[1] PAYLOAD A ENVIAR:")
print(json.dumps(payload, indent=2))

print("\n[2] Enviando al webhook local...")

try:
    response = requests.post(
        f"{BASE_URL}/whatsapp/messages",
        json=payload,
        timeout=30,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\n[3] RESPUESTA:")
    print(f"    Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"    Body: {json.dumps(response.json(), indent=2)}")
        print("\n[OK] Webhook procesó el mensaje exitosamente")
        print("\n[SIGUIENTE PASO]")
        print("    Ejecuta: python scripts/verify_message_in_db.py")
        print("    Para verificar que se guardó en la BD")
    else:
        print(f"    Body: {response.text}")
        print(f"\n[ERROR] Webhook falló con status {response.status_code}")
        
except Exception as e:
    print(f"\n[ERROR] Excepción: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

