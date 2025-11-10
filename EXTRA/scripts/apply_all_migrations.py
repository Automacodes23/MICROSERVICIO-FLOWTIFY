"""
Script para aplicar todas las migraciones faltantes
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def apply_migrations():
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
        print("APLICANDO MIGRACIONES A TODAS LAS TABLAS")
        print("=" * 80)
        
        with connection.cursor() as cursor:
            
            # ========== TABLA: trips ==========
            print("\n[TABLA: trips]")
            
            # code
            print("  [1/6] Agregando columna 'code'...")
            try:
                cursor.execute("ALTER TABLE trips ADD COLUMN code VARCHAR(50) NULL AFTER id")
                cursor.execute("ALTER TABLE trips ADD UNIQUE INDEX idx_trips_code (code)")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # customer_id
            print("  [2/6] Agregando columna 'customer_id'...")
            try:
                cursor.execute("ALTER TABLE trips ADD COLUMN customer_id VARCHAR(36) NULL AFTER floatify_trip_id")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # origin
            print("  [3/6] Agregando columna 'origin'...")
            try:
                cursor.execute("ALTER TABLE trips ADD COLUMN origin JSON NULL AFTER substatus")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # destination
            print("  [4/6] Agregando columna 'destination'...")
            try:
                cursor.execute("ALTER TABLE trips ADD COLUMN destination JSON NULL AFTER origin")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # started_at
            print("  [5/6] Agregando columna 'started_at'...")
            try:
                cursor.execute("ALTER TABLE trips ADD COLUMN started_at TIMESTAMP NULL AFTER destination")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # completed_at
            print("  [6/6] Agregando columna 'completed_at'...")
            try:
                cursor.execute("ALTER TABLE trips ADD COLUMN completed_at TIMESTAMP NULL AFTER started_at")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # ========== TABLA: units ==========
            print("\n[TABLA: units]")
            
            # plates
            print("  [1/2] Agregando columna 'plates'...")
            try:
                cursor.execute("ALTER TABLE units ADD COLUMN plates VARCHAR(20) NULL AFTER name")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # wialon_id
            print("  [2/2] Agregando columna 'wialon_id'...")
            try:
                cursor.execute("ALTER TABLE units ADD COLUMN wialon_id VARCHAR(50) NULL AFTER plates")
                cursor.execute("ALTER TABLE units ADD UNIQUE INDEX idx_units_wialon_id (wialon_id)")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # ========== TABLA: drivers ==========
            print("\n[TABLA: drivers]")
            
            # floatify_driver_id
            print("  [1/1] Agregando columna 'floatify_driver_id'...")
            try:
                cursor.execute("ALTER TABLE drivers ADD COLUMN floatify_driver_id VARCHAR(50) NULL AFTER phone")
                cursor.execute("ALTER TABLE drivers ADD UNIQUE INDEX idx_drivers_floatify_driver_id (floatify_driver_id)")
                print("        [OK]")
            except pymysql.err.OperationalError as e:
                if "Duplicate" in str(e):
                    print("        [SKIP] Ya existe")
                else:
                    print(f"        [ERROR] {e}")
            
            # ========== COMMIT ==========
            print("\n[COMMIT] Guardando cambios...")
            connection.commit()
            print("         [OK] Cambios guardados")
            
            # ========== VERIFICACIÓN ==========
            print("\n" + "=" * 80)
            print("VERIFICACIÓN FINAL")
            print("=" * 80)
            
            for table in ['trips', 'units', 'drivers']:
                cursor.execute(f"""
                    SELECT COUNT(COLUMN_NAME) as total_columnas
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'logistics_db' AND TABLE_NAME = '{table}'
                """)
                result = cursor.fetchone()
                print(f"\n{table}: {result['total_columnas']} columnas totales")
            
            print("\n" + "=" * 80)
            print("MIGRACIONES COMPLETADAS EXITOSAMENTE")
            print("=" * 80)
            print("\nAhora puedes:")
            print("  1. Reiniciar el servidor")
            print("  2. Ejecutar el test: python scripts/test_simple_webhook.py")
            print("  3. O ejecutar el E2E completo: python e2e_test_flow.py")
            print("\n" + "=" * 80)
        
        connection.close()
        
    except Exception as e:
        print(f"\n[ERROR] {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    apply_migrations()

