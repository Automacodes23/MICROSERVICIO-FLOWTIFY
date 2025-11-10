"""
Script forzado para agregar substatus (con autocommit)
"""
import pymysql

config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': '',
    'database': 'logistics_db',
    'autocommit': True,  # IMPORTANTE: autocommit para evitar locks
    'connect_timeout': 10
}

print("\n=== AGREGANDO COLUMNA SUBSTATUS (MODO FORZADO) ===\n")

try:
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Verificar si existe
    cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'logistics_db' 
        AND TABLE_NAME = 'trips' 
        AND COLUMN_NAME = 'substatus'
    """)
    
    if cursor.fetchone()[0] > 0:
        print("[INFO] La columna 'substatus' YA EXISTE\n")
    else:
        print("[1/2] Agregando columna...")
        cursor.execute("ALTER TABLE trips ADD COLUMN substatus VARCHAR(50) DEFAULT NULL AFTER status")
        print("      [OK]\n")
        
        print("[2/2] Agregando indice...")
        try:
            cursor.execute("ALTER TABLE trips ADD INDEX idx_substatus (substatus)")
            print("      [OK]\n")
        except:
            print("      [SKIP] Indice ya existe\n")
    
    # Verificar
    cursor.execute("DESCRIBE trips")
    print("Estructura de tabla 'trips':")
    for row in cursor.fetchall():
        if row[0] in ['status', 'substatus']:
            print(f"  - {row[0]}: {row[1]}")
    
    print("\n[EXITO] Columna 'substatus' lista para usar\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}\n")
    print("SOLUCION MANUAL:")
    print("1. Abre XAMPP > phpMyAdmin")
    print("2. Selecciona base de datos 'logistics_db'")
    print("3. Selecciona tabla 'trips'")
    print("4. Ve a pestaña 'Estructura'")
    print("5. Agrega columna 'substatus' VARCHAR(50) NULL despues de 'status'\n")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()

