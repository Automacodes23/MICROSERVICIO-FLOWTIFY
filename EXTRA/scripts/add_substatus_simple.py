"""
Script simple para agregar columna substatus a trips
"""
import pymysql
import sys

# Configuración
config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': '',
    'database': 'logistics_db',
    'charset': 'utf8mb4',
    'connect_timeout': 5
}

def main():
    print("\n" + "="*60)
    print("Agregando columna 'substatus' a tabla 'trips'")
    print("="*60 + "\n")
    
    try:
        # Conectar a MySQL
        print("[1/3] Conectando a MySQL...")
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        print("      [OK] Conectado\n")
        
        # Verificar si la columna ya existe
        print("[2/3] Verificando si columna 'substatus' existe...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'logistics_db' 
            AND TABLE_NAME = 'trips' 
            AND COLUMN_NAME = 'substatus'
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("      [INFO] La columna 'substatus' ya existe\n")
        else:
            print("      [INFO] La columna no existe, agregando...\n")
            
            # Agregar columna
            print("[3/3] Agregando columna 'substatus'...")
            cursor.execute("""
                ALTER TABLE trips 
                ADD COLUMN substatus VARCHAR(50) DEFAULT NULL AFTER status
            """)
            conn.commit()
            print("      [OK] Columna agregada\n")
            
            # Agregar índice
            print("[4/3] Agregando índice...")
            try:
                cursor.execute("""
                    ALTER TABLE trips 
                    ADD INDEX idx_substatus (substatus)
                """)
                conn.commit()
                print("      [OK] Indice agregado\n")
            except pymysql.err.OperationalError as e:
                if "Duplicate key name" in str(e):
                    print("      [INFO] El indice ya existe\n")
                else:
                    raise
        
        # Verificar resultado
        print("[VERIFICACION] Consultando estructura de tabla...")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'logistics_db' 
            AND TABLE_NAME = 'trips'
            AND COLUMN_NAME IN ('status', 'substatus')
            ORDER BY ORDINAL_POSITION
        """)
        
        rows = cursor.fetchall()
        print("\n  Columnas encontradas:")
        for row in rows:
            print(f"    - {row[0]}: {row[1]} (NULL={row[2]}, DEFAULT={row[3]})")
        
        print("\n" + "="*60)
        print("[EXITO] Migracion completada exitosamente")
        print("="*60 + "\n")
        
    except pymysql.err.OperationalError as e:
        print(f"\n[ERROR] Error de conexion: {e}")
        print("Verifica que MySQL este corriendo en localhost:3307")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()

