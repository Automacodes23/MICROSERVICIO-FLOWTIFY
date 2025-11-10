"""
Script de diagnóstico completo para el bot de WhatsApp
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv
import json

async def diagnose():
    load_dotenv()

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3307))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "logistics_db")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    print("=" * 70)
    print(" DIAGNOSTICO COMPLETO DEL BOT DE WHATSAPP")
    print("=" * 70)

    try:
        conn = await aiomysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            autocommit=True,
            charset='utf8mb4',
            cursorclass=aiomysql.DictCursor
        )
        
        print("\n[OK] Conectado a la base de datos\n")

        async with conn.cursor() as cursor:
            # 1. VIAJES ACTIVOS
            print("=" * 70)
            print("[1] VIAJES ACTIVOS (status != 'finalizado')")
            print("=" * 70)
            
            await cursor.execute("""
                SELECT 
                    floatify_trip_id,
                    status,
                    substatus,
                    whatsapp_group_id,
                    whatsapp_group_name,
                    created_at
                FROM trips
                WHERE status != 'finalizado'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            trips = await cursor.fetchall()
            
            if trips:
                for trip in trips:
                    print(f"\n  Viaje: {trip['floatify_trip_id']}")
                    print(f"    Status:      {trip['status']}")
                    print(f"    Substatus:   {trip['substatus']}")
                    print(f"    Grupo WA:    {trip['whatsapp_group_id']}")
                    print(f"    Nombre:      {trip['whatsapp_group_name']}")
                    print(f"    Creado:      {trip['created_at']}")
            else:
                print("\n  [WARNING] No hay viajes activos")
            
            # 2. CONVERSACIONES
            print("\n" + "=" * 70)
            print("[2] CONVERSACIONES REGISTRADAS")
            print("=" * 70)
            
            await cursor.execute("""
                SELECT 
                    c.id,
                    c.whatsapp_group_id,
                    t.floatify_trip_id,
                    t.status,
                    t.substatus,
                    c.created_at,
                    c.metadata
                FROM conversations c
                INNER JOIN trips t ON c.trip_id = t.id
                WHERE t.status != 'finalizado'
                ORDER BY c.created_at DESC
                LIMIT 5
            """)
            conversations = await cursor.fetchall()
            
            if conversations:
                for conv in conversations:
                    print(f"\n  Conversacion ID: {conv['id']}")
                    print(f"    Viaje:       {conv['floatify_trip_id']}")
                    print(f"    Status:      {conv['status']} / {conv['substatus']}")
                    print(f"    Grupo WA:    {conv['whatsapp_group_id']}")
                    print(f"    Creado:      {conv['created_at']}")
                    
                    # Mostrar participantes si están en metadata
                    if conv['metadata']:
                        try:
                            metadata = json.loads(conv['metadata']) if isinstance(conv['metadata'], str) else conv['metadata']
                            if 'participants' in metadata:
                                print(f"    Participantes: {', '.join(metadata['participants'])}")
                        except:
                            pass
            else:
                print("\n  [WARNING] No hay conversaciones registradas")
            
            # 3. MENSAJES RECIENTES
            print("\n" + "=" * 70)
            print("[3] MENSAJES RECIENTES (últimos 10)")
            print("=" * 70)
            
            await cursor.execute("""
                SELECT 
                    m.id,
                    m.content,
                    m.sender_type,
                    m.sender_phone,
                    t.floatify_trip_id,
                    m.created_at
                FROM messages m
                INNER JOIN conversations c ON m.conversation_id = c.id
                INNER JOIN trips t ON c.trip_id = t.id
                ORDER BY m.created_at DESC
                LIMIT 10
            """)
            messages = await cursor.fetchall()
            
            if messages:
                for msg in messages:
                    print(f"\n  Mensaje ID: {msg['id']}")
                    print(f"    Viaje:   {msg['floatify_trip_id']}")
                    print(f"    De:      {msg['sender_phone']} ({msg['sender_type']})")
                    print(f"    Content: {msg['content'][:100] if msg['content'] else 'N/A'}...")
                    print(f"    Fecha:   {msg['created_at']}")
            else:
                print("\n  [WARNING] No hay mensajes registrados")
            
            # 4. VIAJES CON GRUPO WHATSAPP NULO
            print("\n" + "=" * 70)
            print("[4] VIAJES SIN GRUPO WHATSAPP (PROBLEMA)")
            print("=" * 70)
            
            await cursor.execute("""
                SELECT 
                    floatify_trip_id,
                    status,
                    substatus,
                    whatsapp_group_id
                FROM trips
                WHERE status != 'finalizado'
                AND (whatsapp_group_id IS NULL OR whatsapp_group_id = '')
                ORDER BY created_at DESC
            """)
            broken_trips = await cursor.fetchall()
            
            if broken_trips:
                print("\n  [ERROR] Estos viajes NO tienen grupo de WhatsApp:")
                for trip in broken_trips:
                    print(f"    - {trip['floatify_trip_id']} ({trip['status']})")
            else:
                print("\n  [OK] Todos los viajes activos tienen grupo de WhatsApp")

            # 5. RESUMEN Y RECOMENDACIONES
            print("\n" + "=" * 70)
            print("[5] RESUMEN Y RECOMENDACIONES")
            print("=" * 70)
            
            if not trips:
                print("\n  [PROBLEMA] No hay viajes activos")
                print("  [SOLUCION] Ejecuta: python testing_e2e/manual_bot_test.py")
            elif broken_trips:
                print("\n  [PROBLEMA] Hay viajes sin grupo de WhatsApp")
                print("  [SOLUCION] El grupo no se creó correctamente en Evolution API")
            elif not conversations:
                print("\n  [PROBLEMA] No hay conversaciones registradas")
                print("  [SOLUCION] La conversación no se creó al momento del viaje")
            else:
                print("\n  [OK] Todo parece estar bien configurado")
                print("\n  [SIGUIENTE PASO]:")
                print("    1. Ve a WhatsApp")
                if trips and trips[0]['whatsapp_group_name']:
                    print(f"    2. Busca el grupo: '{trips[0]['whatsapp_group_name']}'")
                print("    3. Envía: 'Empecé a cargar'")
                print("    4. El bot debería responder")
                
                print("\n  [PARA DEBUGGING]:")
                print("    - Revisa logs del servidor FastAPI")
                print("    - Revisa ngrok: http://127.0.0.1:4040")
                print("    - Ejecuta: python scripts/check_trip_status.py")

        conn.close()
        print("\n" + "=" * 70)
        print()

    except Exception as e:
        print(f"\n[ERROR] {e}\n")

if __name__ == "__main__":
    asyncio.run(diagnose())

