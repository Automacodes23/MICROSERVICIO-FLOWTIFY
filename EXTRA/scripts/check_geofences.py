"""
Script para verificar si las geocercas necesarias existen
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def check_geofences():
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
        print("VERIFICACION DE GEOCERCAS")
        print("=" * 80)
        
        # Buscar geocercas con IDs 9001 y 9002
        await cursor.execute("""
            SELECT id, floatify_geofence_id, wialon_geofence_id, name
            FROM geofences
            WHERE floatify_geofence_id IN ('9001', '9002')
               OR wialon_geofence_id IN ('9001', '9002')
        """)
        
        geofences = await cursor.fetchall()
        
        if geofences:
            print(f"\nGeocercas encontradas: {len(geofences)}")
            for gf in geofences:
                print(f"\n  ID: {gf['id']}")
                print(f"  Floatify ID: {gf['floatify_geofence_id']}")
                print(f"  Wialon ID: {gf['wialon_geofence_id']}")
                print(f"  Nombre: {gf['name']}")
        else:
            print("\n[ERROR] NO se encontraron geocercas con IDs 9001 o 9002")
            print("\nEsto causara error al procesar eventos de Wialon")
            print("Las geocercas deben crearse junto con el viaje")
        
        # Verificar la tabla geofences
        await cursor.execute("DESCRIBE geofences")
        columns = await cursor.fetchall()
        
        print("\n" + "=" * 80)
        print("ESTRUCTURA DE LA TABLA GEOFENCES")
        print("=" * 80)
        for col in columns:
            print(f"  {col['Field']:30} {col['Type']:20} {col['Null']:10} {col['Key']:10}")
        
        # Verificar si events tiene FK a geofences
        await cursor.execute("""
            SELECT 
                CONSTRAINT_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'events'
              AND REFERENCED_TABLE_NAME = 'geofences'
        """, (os.getenv("MYSQL_DATABASE", "logistics_db"),))
        
        fks = await cursor.fetchall()
        
        print("\n" + "=" * 80)
        print("FOREIGN KEYS: events -> geofences")
        print("=" * 80)
        if fks:
            for fk in fks:
                print(f"  {fk['CONSTRAINT_NAME']}: {fk['COLUMN_NAME']} -> {fk['REFERENCED_COLUMN_NAME']}")
        else:
            print("  [INFO] No hay FK entre events y geofences")
    
    connection.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_geofences())

