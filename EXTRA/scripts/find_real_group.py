"""
Script para encontrar el grupo real creado por el test E2E
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def find_groups():
    connection = await aiomysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        db=os.getenv("MYSQL_DATABASE", "logistics_db"),
        cursorclass=aiomysql.DictCursor
    )
    
    async with connection.cursor() as cursor:
        print("=" * 80)
        print("GRUPOS DE WHATSAPP ACTIVOS")
        print("=" * 80)
        
        # Buscar conversaciones activas
        await cursor.execute("""
            SELECT 
                c.id,
                c.trip_id,
                c.whatsapp_group_id,
                c.group_name,
                c.is_active,
                t.floatify_trip_id,
                t.status,
                t.created_at
            FROM conversations c
            INNER JOIN trips t ON c.trip_id = t.id
            WHERE c.is_active = TRUE
            ORDER BY c.created_at DESC
            LIMIT 5
        """)
        
        conversations = await cursor.fetchall()
        
        if conversations:
            print(f"\nConversaciones activas: {len(conversations)}\n")
            for conv in conversations:
                print(f"  Grupo: {conv['group_name']}")
                print(f"  WhatsApp ID: {conv['whatsapp_group_id']}")
                print(f"  Trip: {conv['floatify_trip_id']}")
                print(f"  Status: {conv['status']}")
                print(f"  Creado: {conv['created_at']}")
                print("  " + "-" * 70)
        else:
            print("\n[ERROR] No hay conversaciones activas")
            print("Ejecuta el test E2E primero: python scripts/e2e_test_flow.py\n")
    
    connection.close()
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(find_groups())

