"""
Script para mostrar los grupos activos de WhatsApp
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

async def show_groups():
    load_dotenv()

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3307))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "logistics_db")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    print("=" * 70)
    print(" GRUPOS DE WHATSAPP ACTIVOS")
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

        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT 
                    floatify_trip_id,
                    whatsapp_group_name,
                    whatsapp_group_id,
                    status,
                    substatus,
                    created_at
                FROM trips
                WHERE status != 'finalizado'
                AND whatsapp_group_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5
            """)
            trips = await cursor.fetchall()
            
            if trips:
                print("\n[GRUPOS ACTIVOS (los 5 mas recientes)]:\n")
                for i, trip in enumerate(trips, 1):
                    print(f"{i}. GRUPO: '{trip['whatsapp_group_name']}'")
                    print(f"   Viaje:     {trip['floatify_trip_id']}")
                    print(f"   Status:    {trip['status']} / {trip['substatus']}")
                    print(f"   Creado:    {trip['created_at']}")
                    print(f"   ID Grupo:  {trip['whatsapp_group_id']}\n")
                
                print("=" * 70)
                print("\n[INSTRUCCION]:")
                print(f"  Envia un mensaje al grupo mas reciente:")
                print(f"  '{trips[0]['whatsapp_group_name']}'")
                print(f"\n  Mensaje: 'Empece a cargar'")
                print("=" * 70)
            else:
                print("\n[ERROR] No hay grupos activos")

        conn.close()

    except Exception as e:
        print(f"\n[ERROR] {e}\n")

if __name__ == "__main__":
    asyncio.run(show_groups())

