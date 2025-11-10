"""
Script para verificar el esquema de todas las tablas críticas
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

EXPECTED_SCHEMAS = {
    'trips': [
        'id', 'code', 'floatify_trip_id', 'customer_id', 'driver_id', 'unit_id',
        'status', 'substatus', 'origin', 'destination', 'started_at', 'completed_at',
        'created_at', 'updated_at'
    ],
    'conversations': [
        'id', 'trip_id', 'whatsapp_group_id', 'driver_id', 'status',
        'created_at', 'updated_at'
    ],
    'messages': [
        'id', 'conversation_id', 'trip_id', 'sender_type', 'sender_phone',
        'direction', 'content', 'transcription', 'ai_result', 'created_at'
    ],
    'units': [
        'id', 'name', 'plates', 'wialon_id', 'floatify_unit_id', 'created_at'
    ],
    'drivers': [
        'id', 'name', 'phone', 'floatify_driver_id', 'created_at'
    ],
    'events': [
        'id', 'trip_id', 'unit_id', 'event_type', 'geofence_id', 'latitude',
        'longitude', 'event_time', 'created_at'
    ]
}

try:
    connection = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "logistics_db"),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    print("=" * 80)
    print("VERIFICACIÓN DE ESQUEMAS DE TABLAS CRÍTICAS")
    print("=" * 80)
    
    all_ok = True
    
    with connection.cursor() as cursor:
        for table_name, expected_cols in EXPECTED_SCHEMAS.items():
            print(f"\n[TABLA: {table_name}]")
            
            try:
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                column_names = [col['Field'] for col in columns]
                
                missing = []
                for expected_col in expected_cols:
                    if expected_col in column_names:
                        print(f"  [OK] {expected_col}")
                    else:
                        print(f"  [X] {expected_col} - FALTA")
                        missing.append(expected_col)
                        all_ok = False
                
                if missing:
                    print(f"\n  [RESUMEN] {len(missing)} columnas faltantes: {', '.join(missing)}")
                else:
                    print(f"\n  [RESUMEN] Todas las columnas esperadas están presentes")
                    
            except pymysql.err.ProgrammingError as e:
                print(f"  [ERROR] Tabla no existe: {e}")
                all_ok = False
    
    connection.close()
    
    print("\n" + "=" * 80)
    if all_ok:
        print("[OK] TODAS LAS TABLAS TIENEN LAS COLUMNAS ESPERADAS")
    else:
        print("[ERROR] HAY COLUMNAS FALTANTES EN ALGUNAS TABLAS")
        print("\nSe necesita ejecutar migraciones para agregar las columnas faltantes.")
    print("=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")
    import traceback
    traceback.print_exc()

