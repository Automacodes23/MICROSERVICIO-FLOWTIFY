"""Verificar estado del viaje"""
import pymysql

conn = pymysql.connect(host='localhost', port=3307, user='root', password='', db='logistics_db')
cursor = conn.cursor(pymysql.cursors.DictCursor)

trip_id = '7d4bbc29-be77-11f0-b0de-f4b5205b5b70'
cursor.execute('SELECT id, floatify_trip_id, status, unit_id, driver_id FROM trips WHERE id = %s', (trip_id,))
trip = cursor.fetchone()

if trip:
    print(f"Trip ID: {trip['id']}")
    print(f"Code: {trip['floatify_trip_id']}")
    print(f"Status: {trip['status']}")
    print(f"Unit ID: {trip['unit_id']}")
    print(f"Driver ID: {trip['driver_id']}")
    
    # Verificar si la unidad existe
    cursor.execute('SELECT id, floatify_unit_id, wialon_unit_id, name FROM units WHERE id = %s', (trip['unit_id'],))
    unit = cursor.fetchone()
    if unit:
        print(f"\nUnit encontrada:")
        print(f"  ID: {unit['id']}")
        print(f"  Floatify ID: {unit['floatify_unit_id']}")
        print(f"  Wialon ID: {unit['wialon_unit_id']}")
        print(f"  Name: {unit['name']}")
    else:
        print(f"\nUnit NO encontrada: {trip['unit_id']}")
else:
    print("Trip no encontrado")

conn.close()

