"""
Encontrar el último grupo de test creado y verificar su conversación
"""
import pymysql
import os
from dotenv import load_dotenv

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
        print("ÚLTIMOS VIAJES Y CONVERSACIONES CREADAS")
        print("=" * 80)
        
        # Buscar últimos viajes
        cursor.execute("""
            SELECT 
                t.id as trip_id,
                t.code as trip_code,
                t.status as trip_status,
                t.created_at,
                c.id as conversation_id,
                c.whatsapp_group_id,
                c.status as conv_status
            FROM trips t
            LEFT JOIN conversations c ON c.trip_id = t.id
            ORDER BY t.created_at DESC
            LIMIT 5
        """)
        
        trips = cursor.fetchall()
        
        if not trips:
            print("\n[ERROR] No hay viajes en la base de datos")
        else:
            for i, trip in enumerate(trips, 1):
                print(f"\n[{i}] Trip ID: {trip['trip_id']}")
                print(f"    Code: {trip['trip_code']}")
                print(f"    Status: {trip['trip_status']}")
                print(f"    Created: {trip['created_at']}")
                
                if trip['conversation_id']:
                    print(f"    [OK] Conversation ID: {trip['conversation_id']}")
                    print(f"    [OK] WhatsApp Group: {trip['whatsapp_group_id']}")
                    print(f"    [OK] Conv Status: {trip['conv_status']}")
                else:
                    print(f"    [X] NO TIENE CONVERSACION ASOCIADA")
        
        print("\n" + "=" * 80)
        print("VERIFICACIÓN DE GRUPOS SIN CONVERSACIÓN")
        print("=" * 80)
        
        # Buscar viajes sin conversación
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM trips t
            LEFT JOIN conversations c ON c.trip_id = t.id
            WHERE c.id IS NULL
        """)
        result = cursor.fetchone()
        
        print(f"\nViajes sin conversación: {result['count']}")
        
        if result['count'] > 0:
            print("\n[ERROR] Hay viajes sin conversación asociada.")
            print("Esto es el problema. Cuando mandas mensajes de WhatsApp,")
            print("el bot no puede encontrar el viaje y no responde.")
    
    connection.close()
    print("\n" + "=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")
    import traceback
    traceback.print_exc()

