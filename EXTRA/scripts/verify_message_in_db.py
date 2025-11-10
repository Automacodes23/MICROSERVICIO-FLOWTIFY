"""
Verificar los últimos mensajes guardados en la BD
"""
import pymysql
import os
from dotenv import load_dotenv
import json

load_dotenv()

try:
    connection = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "logistics_db"),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        print("=" * 80)
        print("ÚLTIMOS MENSAJES GUARDADOS EN LA BD")
        print("=" * 80)
        
        # Buscar últimos mensajes
        cursor.execute("""
            SELECT 
                m.id,
                m.conversation_id,
                m.trip_id,
                m.sender_phone,
                m.sender_type,
                m.direction,
                m.content,
                m.created_at,
                c.whatsapp_group_id,
                t.status as trip_status
            FROM messages m
            LEFT JOIN conversations c ON c.id = m.conversation_id
            LEFT JOIN trips t ON t.id = m.trip_id
            ORDER BY m.created_at DESC
            LIMIT 10
        """)
        
        messages = cursor.fetchall()
        
        if not messages:
            print("\n[ERROR] No hay mensajes en la base de datos")
        else:
            for i, msg in enumerate(messages, 1):
                print(f"\n[{i}] Message ID: {msg['id']}")
                print(f"    Content: {msg['content'][:100]}...")
                print(f"    Sender: {msg['sender_phone']} ({msg['sender_type']})")
                print(f"    Direction: {msg['direction']}")
                print(f"    Group: {msg['whatsapp_group_id']}")
                print(f"    Trip ID: {msg['trip_id']}")
                print(f"    Trip Status: {msg['trip_status']}")
                print(f"    Created: {msg['created_at']}")
        
        print("\n" + "=" * 80)
        print("ÚLTIMAS INTERACCIONES DE IA")
        print("=" * 80)
        
        # Buscar últimas interacciones de IA
        cursor.execute("""
            SELECT 
                ai.id,
                ai.message_id,
                ai.trip_id,
                ai.driver_message,
                ai.ai_classification,
                ai.ai_confidence,
                ai.ai_response,
                ai.created_at
            FROM ai_interactions ai
            ORDER BY ai.created_at DESC
            LIMIT 5
        """)
        
        interactions = cursor.fetchall()
        
        if not interactions:
            print("\n[INFO] No hay interacciones de IA en la base de datos")
        else:
            for i, interaction in enumerate(interactions, 1):
                print(f"\n[{i}] Interaction ID: {interaction['id']}")
                print(f"    Driver Message: {interaction['driver_message'][:80]}...")
                print(f"    Classification: {interaction['ai_classification']}")
                print(f"    Confidence: {interaction['ai_confidence']}")
                print(f"    AI Response: {interaction['ai_response'][:80] if interaction['ai_response'] else 'None'}...")
                print(f"    Created: {interaction['created_at']}")
    
    connection.close()
    print("\n" + "=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")
    import traceback
    traceback.print_exc()

