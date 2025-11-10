"""
Verificar si un grupo tiene conversación asociada
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

GROUP_ID = "120363421688497664@g.us"

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
        print(f"VERIFICANDO GRUPO: {GROUP_ID}")
        print("=" * 80)
        
        # Buscar conversación usando whatsapp_group_id (no group_id)
        cursor.execute("""
            SELECT 
                c.id as conversation_id,
                c.trip_id,
                c.whatsapp_group_id,
                c.status as conv_status,
                t.code as trip_code,
                t.status as trip_status
            FROM conversations c
            LEFT JOIN trips t ON t.id = c.trip_id
            WHERE c.whatsapp_group_id = %s
        """, (GROUP_ID,))
        
        conv = cursor.fetchone()
        
        if conv:
            print("\n[OK] Conversaci\u00f3n encontrada:")
            print(f"  - Conversation ID: {conv['conversation_id']}")
            print(f"  - Trip ID:         {conv['trip_id']}")
            print(f"  - Trip Code:       {conv['trip_code']}")
            print(f"  - Trip Status:     {conv['trip_status']}")
            print(f"  - Conv Status:     {conv['conv_status']}")
        else:
            print(f"\n[ERROR] No hay conversaci\u00f3n para este grupo")
            print("\nEste es el problema. El webhook necesita un grupo con conversaci\u00f3n asociada.")
            
            # Buscar grupos con conversación
            print("\n" + "=" * 80)
            print("GRUPOS DISPONIBLES CON CONVERSACION:")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    c.whatsapp_group_id,
                    t.code as trip_code,
                    t.status as trip_status,
                    c.status as conv_status
                FROM conversations c
                JOIN trips t ON t.id = c.trip_id
                WHERE c.whatsapp_group_id IS NOT NULL
                ORDER BY c.created_at DESC
                LIMIT 5
            """)
            
            groups = cursor.fetchall()
            if groups:
                for g in groups:
                    print(f"\n  Group: {g['whatsapp_group_id']}")
                    print(f"  Trip:  {g['trip_code']} ({g['trip_status']})")
                    print(f"  Conv:  {g['conv_status']}")
            else:
                print("\n  [VACIO] No hay grupos con conversaci\u00f3n.")
                print("  SOLUCION: Ejecuta 'python e2e_test_flow.py' para crear uno.")
    
    connection.close()
    print("\n" + "=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")
    import traceback
    traceback.print_exc()

