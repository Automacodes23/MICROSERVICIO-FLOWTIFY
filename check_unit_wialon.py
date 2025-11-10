"""Ver wialon_id de la unidad"""
import pymysql

conn = pymysql.connect(host='localhost', port=3307, user='root', password='', db='logistics_db')
cursor = conn.cursor(pymysql.cursors.DictCursor)

unit_id = '25fe009e-be7c-11f0-b0de-f4b5205b5b70'
cursor.execute('SELECT id, wialon_id, wialon_unit_id, floatify_unit_id, name FROM units WHERE id = %s', (unit_id,))
unit = cursor.fetchone()

if unit:
    print("Unit info:")
    print(f"  ID: {unit['id']}")
    print(f"  Wialon ID: {unit.get('wialon_id')}")
    print(f"  Wialon Unit ID: {unit.get('wialon_unit_id')}")
    print(f"  Floatify Unit ID: {unit.get('floatify_unit_id')}")
    print(f"  Name: {unit['name']}")
    
    # Verificar cual usar para el evento
    print("\nPara el evento de Wialon, usar:")
    if unit.get('wialon_unit_id'):
        print(f"  unit_id={unit['wialon_unit_id']}")
    elif unit.get('wialon_id'):
        print(f"  unit_id={unit['wialon_id']}")
    else:
        print("  NO TIENE wialon_id configurado!")
else:
    print(f"Unit no encontrada: {unit_id}")

conn.close()

