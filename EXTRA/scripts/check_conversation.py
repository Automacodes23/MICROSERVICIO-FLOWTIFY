"""
Verificar si el grupo tiene una conversación asociada
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
        print(f"VERIFICANDO CONVERSACIÓN PARA GRUPO: {GROUP_ID}")
        print("=" * 80)
        
        # Buscar conversación
        cursor.execute("""
            SELECT 
                c.id as conversation_id,
                c.trip_id,
                c.group_id,
                c.status,
                c.created_at,
                t.code as trip_code,
                t.status as trip_status
            FROM conversations c
            LEFT JOIN trips t ON t.id = c.trip_id
            WHERE c.group_id = %s
        """, (GROUP_ID,))
        
        conv = cursor.fetchone()
        
        if conv:
            print("\n[OK] Conversación encontrada:")
            print(f"  - Conversation ID: {conv['conversation_id']}")
            print(f"  - Trip ID:         {conv['trip_id']}")
            print(f"  - Trip Code:       {conv['trip_code']}")
            print(f"  - Trip Status:     {conv['trip_status']}")
            print(f"  - Conv Status:     {conv['status']}")
            print(f"  - Created:         {conv['created_at']}")
        else:
            print(f"\n[ERROR] No se encontró conversación para el grupo: {GROUP_ID}")
            print("\nProbablemente por eso el webhook falla.")
            print("\nSoluciones posibles:")
            print("  1. Usar un grupo que SÍ tenga conversación asociada")
            print("  2. Ejecutar el E2E completo: python e2e_test_flow.py")
            
            # Buscar grupos con conversación
            print("\n" + "=" * 80)
            print("GRUPOS CON CONVERSACIÓN ACTIVA:")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    c.group_id,
                    t.code as trip_code,
                    c.status as conv_status,
                    t.status as trip_status
                FROM conversations c
                JOIN trips t ON t.id = c.trip_id
                WHERE c.group_id IS NOT NULL
                ORDER BY c.created_at DESC
                LIMIT 5
            """)
            
            groups = cursor.fetchall()
            if groups:
                for g in groups:
                    print(f"\n  Group ID:    {g['group_id']}")
                    print(f"  Trip Code:   {g['trip_code']}")
                    print(f"  Trip Status: {g['trip_status']}")
                    print(f"  Conv Status: {g['conv_status']}")
            else:
                print("\n  No hay grupos con conversación activa.")
                print("  Ejecuta el E2E completo para crear uno.")
    
    connection.close()
    print("\n" + "=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")

