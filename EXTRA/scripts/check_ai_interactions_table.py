"""
Script para verificar si existe la tabla ai_interactions
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
        print("VERIFICANDO TABLA ai_interactions")
        print("=" * 80)
        
        # Verificar si existe la tabla
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = 'logistics_db' 
            AND table_name = 'ai_interactions'
        """)
        result = cursor.fetchone()
        
        if result['count'] == 0:
            print("\n[ERROR] La tabla 'ai_interactions' NO EXISTE")
            print("\nEsto causa el error 500 cuando el bot intenta guardar interacciones de IA.")
            print("\n[SOLUCION] Necesitas crear esta tabla.")
        else:
            print("\n[OK] La tabla 'ai_interactions' existe")
            
            # Mostrar el esquema
            cursor.execute("DESCRIBE ai_interactions")
            columns = cursor.fetchall()
            
            print(f"\nColumnas ({len(columns)}):\n")
            for col in columns:
                nullable = "NULL" if col['Null'] == 'YES' else "NOT NULL"
                key = f"[{col['Key']}]" if col['Key'] else ""
                print(f"  {col['Field']:30} {col['Type']:25} {nullable:10} {key}")
    
    connection.close()
    print("\n" + "=" * 80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")
    import traceback
    traceback.print_exc()

