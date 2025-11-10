"""
Script rápido para verificar el último viaje creado
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def check_trip():
    # Conectar a MySQL
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
        print("VERIFICACIÓN DEL ÚLTIMO VIAJE")
        print("=" * 80)
        
        # 1. Último viaje
        await cursor.execute("""
            SELECT id, floatify_trip_id, unit_id, driver_id, status, 
                   whatsapp_group_id, created_at
            FROM trips 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        trip = await cursor.fetchone()
        
        if not trip:
            print("\n[ERROR] No se encontró ningún viaje")
            return
        
        print(f"\n[VIAJE]")
        print(f"  ID: {trip['id']}")
        print(f"  Código: {trip['floatify_trip_id']}")
        print(f"  Unit ID: {trip['unit_id']}")
        print(f"  Driver ID: {trip['driver_id']}")
        print(f"  Status: {trip['status']}")
        print(f"  WhatsApp: {trip['whatsapp_group_id']}")
        print(f"  Creado: {trip['created_at']}")
        
        # 2. Verificar unidad
        if trip['unit_id']:
            await cursor.execute("""
                SELECT id, floatify_unit_id, wialon_unit_id, name 
                FROM units 
                WHERE id = %s
            """, (trip['unit_id'],))
            unit = await cursor.fetchone()
            
            if unit:
                print(f"\n[UNIDAD]")
                print(f"  ID: {unit['id']}")
                print(f"  Floatify ID: {unit['floatify_unit_id']}")
                print(f"  Wialon ID: {unit['wialon_unit_id']}")
                print(f"  Nombre: {unit['name']}")
                
                # ⚠️ VERIFICAR SI WIALON_UNIT_ID COINCIDE
                if unit['wialon_unit_id'] == '27538728':
                    print(f"  ✅ Wialon ID correcto: {unit['wialon_unit_id']}")
                else:
                    print(f"  ❌ Wialon ID NO coincide!")
                    print(f"     Esperado: 27538728")
                    print(f"     Actual: {unit['wialon_unit_id']}")
            else:
                print(f"\n[ERROR] Unidad no encontrada (ID: {trip['unit_id']})")
        else:
            print(f"\n[ERROR] Viaje sin unit_id asociado")
        
        # 3. Verificar driver
        if trip['driver_id']:
            await cursor.execute("""
                SELECT id, name, phone 
                FROM drivers 
                WHERE id = %s
            """, (trip['driver_id'],))
            driver = await cursor.fetchone()
            
            if driver:
                print(f"\n[CONDUCTOR]")
                print(f"  ID: {driver['id']}")
                print(f"  Nombre: {driver['name']}")
                print(f"  Teléfono: {driver['phone']}")
            else:
                print(f"\n[ERROR] Conductor no encontrado (ID: {trip['driver_id']})")
        
        # 4. Buscar viaje activo por wialon_id (como lo hace el servicio)
        print(f"\n[BÚSQUEDA POR WIALON_ID]")
        await cursor.execute("""
            SELECT t.* FROM trips t
            JOIN units u ON t.unit_id = u.id
            WHERE u.wialon_unit_id = %s
              AND t.status NOT IN ('completed', 'cancelled')
            ORDER BY t.created_at DESC
            LIMIT 1
        """, ('27538728',))
        
        active_trip = await cursor.fetchone()
        
        if active_trip:
            print(f"  ✅ Viaje activo encontrado: {active_trip['floatify_trip_id']}")
        else:
            print(f"  ❌ NO se encontró viaje activo para wialon_id: 27538728")
            print(f"  DIAGNÓSTICO:")
            
            # Verificar si es problema de columna
            await cursor.execute("SHOW COLUMNS FROM units LIKE 'wialon%'")
            columns = await cursor.fetchall()
            print(f"\n  Columnas 'wialon' en tabla units:")
            for col in columns:
                print(f"    - {col['Field']}")
    
    connection.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_trip())

