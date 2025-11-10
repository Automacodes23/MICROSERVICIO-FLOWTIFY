"""
Script para ver el último webhook que llegó desde ngrok
"""
import requests
import json

print("=" * 70)
print(" CAPTURAR PAYLOAD DE WEBHOOK DESDE NGROK")
print("=" * 70)
print("\n[INFO] Conectando a ngrok inspector: http://127.0.0.1:4040\n")

try:
    # API de ngrok para obtener requests
    response = requests.get("http://127.0.0.1:4040/api/requests/http", timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        requests_list = data.get("requests", [])
        
        if not requests_list:
            print("[WARNING] No hay requests capturadas en ngrok")
            print("[SOLUCION] Envia un mensaje desde WhatsApp y vuelve a ejecutar este script\n")
        else:
            # Buscar la última request POST a /whatsapp/messages
            for req in requests_list:
                uri = req.get("uri", "")
                method = req.get("method", "")
                
                if method == "POST" and "/whatsapp/messages" in uri:
                    print(f"[OK] Request encontrada: {method} {uri}")
                    print(f"[TIMESTAMP] {req.get('start', 'N/A')}\n")
                    
                    # Mostrar el body del request
                    request_obj = req.get("request", {})
                    body_raw = request_obj.get("raw", "")
                    
                    if body_raw:
                        try:
                            body_json = json.loads(body_raw)
                            print("[PAYLOAD RECIBIDO]:")
                            print(json.dumps(body_json, indent=2, ensure_ascii=False))
                            
                            # Extraer group_id
                            data_section = body_json.get("data", {})
                            key_section = data_section.get("key", {})
                            group_id = key_section.get("remoteJid")
                            
                            if group_id:
                                print(f"\n[GROUP ID DETECTADO]: {group_id}")
                                print(f"\n[SIGUIENTE PASO]:")
                                print(f"  1. Verifica que este group_id existe en la tabla conversations:")
                                print(f"     SELECT * FROM conversations WHERE whatsapp_group_id = '{group_id}';")
                                print(f"  2. Si NO existe, el grupo no fue registrado correctamente")
                            
                            break
                        except json.JSONDecodeError:
                            print("[ERROR] No se pudo parsear el body como JSON")
                    else:
                        print("[WARNING] El request no tiene body")
                    
                    break
            else:
                print("[WARNING] No se encontraron requests a /whatsapp/messages")
                print("[SOLUCION] Envia un mensaje desde WhatsApp\n")
    else:
        print(f"[ERROR] ngrok API respondió con status {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("[ERROR] No se pudo conectar a ngrok")
    print("[SOLUCION] Verifica que ngrok esté corriendo: http://127.0.0.1:4040\n")
except Exception as e:
    print(f"[ERROR] {e}\n")

print("=" * 70)

