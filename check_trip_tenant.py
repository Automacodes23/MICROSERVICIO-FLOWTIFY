"""Verificar tenant_id del viaje"""
import pymysql
import json

conn = pymysql.connect(
    host='localhost',
    port=3307,
    user='root',
    password='',
    db='logistics_db'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)
trip_id = '7d4bbc29-be77-11f0-b0de-f4b5205b5b70'

cursor.execute('''
    SELECT id, floatify_trip_id, tenant_id, status, substatus, metadata
    FROM trips 
    WHERE id = %s
''', (trip_id,))

trip = cursor.fetchone()

if trip:
    print(f"Trip ID: {trip['id']}")
    print(f"Code: {trip['floatify_trip_id']}")
    print(f"Tenant ID (columna): {trip['tenant_id']}")
    print(f"Status: {trip['status']}")
    print(f"Substatus: {trip['substatus']}")
    
    # Check metadata
    if trip['metadata']:
        try:
            meta = json.loads(trip['metadata']) if isinstance(trip['metadata'], str) else trip['metadata']
            print(f"Metadata tenant_id: {meta.get('tenant_id')}")
        except:
            print(f"Metadata: (no parseable)")
else:
    print(f"Trip no encontrado: {trip_id}")

conn.close()

