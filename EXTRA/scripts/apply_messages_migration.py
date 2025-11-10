"""
Script para aplicar la migración de la tabla messages
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def apply_migration():
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
        print("APLICANDO MIGRACIÓN A LA TABLA MESSAGES")
        print("=" * 80)
        
        with connection.cursor() as cursor:
            # 1. Agregar trip_id
            print("\n[1/8] Agregando columna trip_id...")
            try:
                cursor.execute("""
                    ALTER TABLE messages 
                    ADD COLUMN trip_id VARCHAR(36) NULL AFTER conversation_id
                """)
                cursor.execute("""
                    ALTER TABLE messages 
                    ADD INDEX idx_messages_trip_id (trip_id)
                """)
                print("      [OK] trip_id agregada")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("      [SKIP] trip_id ya existe")
                else:
                    raise
            
            # 2. Agregar sender_type
            print("\n[2/8] Agregando columna sender_type...")
            try:
                cursor.execute("""
                    ALTER TABLE messages 
                    ADD COLUMN sender_type VARCHAR(20) NULL AFTER sender_name
                """)
                print("      [OK] sender_type agregada")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("      [SKIP] sender_type ya existe")
                else:
                    raise
            
            # 3. Agregar direction
            print("\n[3/8] Agregando columna direction...")
            try:
                cursor.execute("""
                    ALTER TABLE messages 
                    ADD COLUMN direction VARCHAR(20) NOT NULL DEFAULT 'inbound' AFTER sender_type
                """)
                print("      [OK] direction agregada")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("      [SKIP] direction ya existe")
                else:
                    raise
            
            # 4. Agregar transcription
            print("\n[4/8] Agregando columna transcription...")
            try:
                cursor.execute("""
                    ALTER TABLE messages 
                    ADD COLUMN transcription TEXT NULL AFTER content
                """)
                print("      [OK] transcription agregada")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("      [SKIP] transcription ya existe")
                else:
                    raise
            
            # 5. Agregar ai_result
            print("\n[5/8] Agregando columna ai_result...")
            try:
                cursor.execute("""
                    ALTER TABLE messages 
                    ADD COLUMN ai_result JSON NULL AFTER transcription
                """)
                print("      [OK] ai_result agregada")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("      [SKIP] ai_result ya existe")
                else:
                    raise
            
            # 6. Poblar sender_type
            print("\n[6/8] Poblando sender_type basado en is_from_driver...")
            cursor.execute("""
                UPDATE messages 
                SET sender_type = CASE 
                    WHEN is_from_driver = 1 THEN 'driver'
                    ELSE 'admin'
                END
                WHERE sender_type IS NULL
            """)
            rows_updated = cursor.rowcount
            print(f"      [OK] {rows_updated} filas actualizadas")
            
            # 7. Poblar direction
            print("\n[7/8] Poblando direction basado en is_from_driver...")
            cursor.execute("""
                UPDATE messages
                SET direction = CASE
                    WHEN is_from_driver = 1 THEN 'inbound'
                    ELSE 'outbound'
                END
                WHERE direction = 'inbound'  -- Solo actualizar las que tienen el valor por defecto
            """)
            rows_updated = cursor.rowcount
            print(f"      [OK] {rows_updated} filas actualizadas")
            
            # 8. Commit
            print("\n[8/8] Guardando cambios...")
            connection.commit()
            print("      [OK] Cambios guardados")
            
            # Verificar resultado
            print("\n" + "=" * 80)
            print("VERIFICACIÓN FINAL")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN trip_id IS NOT NULL THEN 1 ELSE 0 END) as con_trip_id,
                    SUM(CASE WHEN sender_type IS NOT NULL THEN 1 ELSE 0 END) as con_sender_type,
                    SUM(CASE WHEN direction IS NOT NULL THEN 1 ELSE 0 END) as con_direction,
                    SUM(CASE WHEN transcription IS NOT NULL THEN 1 ELSE 0 END) as con_transcription,
                    SUM(CASE WHEN ai_result IS NOT NULL THEN 1 ELSE 0 END) as con_ai_result
                FROM messages
            """)
            result = cursor.fetchone()
            
            print(f"\nTotal de mensajes: {result['total_registros']}")
            print(f"  - Con trip_id:       {result['con_trip_id']}")
            print(f"  - Con sender_type:   {result['con_sender_type']}")
            print(f"  - Con direction:     {result['con_direction']}")
            print(f"  - Con transcription: {result['con_transcription']}")
            print(f"  - Con ai_result:     {result['con_ai_result']}")
            
            print("\n" + "=" * 80)
            print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 80)
            print("\nAhora puedes:")
            print("  1. Reiniciar el servidor (si está corriendo)")
            print("  2. Ejecutar el test: python scripts/test_simple_webhook.py")
            print("  3. O ejecutar el E2E completo: python e2e_test_flow.py")
            print("\n" + "=" * 80)
        
        connection.close()
        
    except Exception as e:
        print(f"\n[ERROR] {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    apply_migration()

