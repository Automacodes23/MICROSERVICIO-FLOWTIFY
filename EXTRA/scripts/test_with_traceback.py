"""
Test del webhook que muestra el traceback completo del error
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
GROUP_ID = "120363404629424294@g.us"

payload = {
    "event": "messages.upsert",
    "instance": "SATECH-BOT",
    "data": {
        "key": {
            "remoteJid": GROUP_ID,
            "fromMe": False,
            "id": f"TEST_MSG_{int(time.time())}",
            "senderLid": "133857336623289@lid",
            "participant": "5214771817823@s.whatsapp.net"
        },
        "pushName": "AutomaCode",
        "message": {
            "conversation": "esperando en el anden"
        },
        "messageType": "conversation",
        "messageTimestamp": int(time.time()),
    },
    "sender": "5214771817823@s.whatsapp.net"
}

print("=" * 80)
print("TEST CON TRACEBACK")
print("=" * 80)

try:
    response = requests.post(
        f"{BASE_URL}/whatsapp/messages",
        json=payload,
        timeout=30
    )
    
    print(f"\nStatus Code: {response.status_code}\n")
    
    data = response.json()
    
    if response.status_code != 200:
        print("[ERROR] TRACEBACK COMPLETO:")
        print("=" * 80)
        if 'error' in data and 'traceback' in data['error']:
            print(data['error']['traceback'])
        else:
            print(json.dumps(data, indent=2))
        print("=" * 80)
    else:
        print("[OK] Exitoso:")
        print(json.dumps(data, indent=2))
        
except Exception as e:
    print(f"\n[ERROR] Excepción: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

