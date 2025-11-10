"""
Script para verificar el estado actual del viaje de prueba
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

async def check_trip_status():
    load_dotenv()

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3307))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "logistics_db")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    trip_code = "E2E_FULL-20251103174307"

    print("=" * 60)
    print(f"ESTADO DEL VIAJE: {trip_code}")
    print("=" * 60)

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

        async with conn.cursor() as cursor:
            # Estado del viaje
            await cursor.execute(
                "SELECT status, substatus, whatsapp_group_id, whatsapp_group_name, updated_at FROM trips WHERE floatify_trip_id = %s",
                (trip_code,)
            )
            trip = await cursor.fetchone()

            if trip:
                print(f"\n[VIAJE ENCONTRADO]")
                print(f"  Status:      {trip['status']}")
                print(f"  Substatus:   {trip['substatus']}")
                print(f"  Grupo WA:    {trip['whatsapp_group_name']}")
                print(f"  Actualizado: {trip['updated_at']}\n")
            else:
                print(f"\n[ERROR] No se encontró el viaje con código: {trip_code}\n")
                return

            # Mensajes del bot
            await cursor.execute(
                """
                SELECT c.whatsapp_group_id, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.trip_id = (SELECT id FROM trips WHERE floatify_trip_id = %s LIMIT 1)
                GROUP BY c.whatsapp_group_id
                """,
                (trip_code,)
            )
            messages = await cursor.fetchone()

            if messages:
                print(f"[MENSAJES]")
                print(f"  Total: {messages['message_count']} mensajes en el grupo\n")

            # Eventos Wialon
            await cursor.execute(
                """
                SELECT COUNT(*) as event_count
                FROM events
                WHERE trip_id = (SELECT id FROM trips WHERE floatify_trip_id = %s LIMIT 1)
                """,
                (trip_code,)
            )
            events = await cursor.fetchone()

            if events:
                print(f"[EVENTOS WIALON]")
                print(f"  Total: {events['event_count']} eventos procesados\n")

        conn.close()

    except Exception as e:
        print(f"[ERROR] {e}\n")

if __name__ == "__main__":
    asyncio.run(check_trip_status())

