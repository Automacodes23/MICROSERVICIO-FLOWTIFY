"""
Script para verificar el esquema de la tabla conversations
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
        print("ESQUEMA DE LA TABLA CONVERSATIONS")
        print("=" * 80)
        
        cursor.execute("DESCRIBE conversations")
        columns = cursor.fetchall()
        
        print(f"\nColumnas encontradas ({len(columns)}):\n")
        for col in columns:
            nullable = "NULL" if col['Null'] == 'YES' else "NOT NULL"
            key = f"[{col['Key']}]" if col['Key'] else ""
            print(f"  {col['Field']:30} {col['Type']:25} {nullable:10} {key}")
        
        print("\n" + "=" * 80)
        print("VERIFICACION DE COLUMNAS ESPERADAS")
        print("=" * 80)
        
        column_names = [col['Field'] for col in columns]
        
        expected_columns = [
            'id',
            'trip_id',
            'group_id',
            'whatsapp_group_id',
            'status',
            'created_at',
            'updated_at'
        ]
        
        for expected in expected_columns:
            if expected in column_names:
                print(f"  [OK] {expected}")
            else:
                print(f"  [ERROR] {expected} - NO EXISTE")
    
    connection.close()
    print("\n" + "=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")

