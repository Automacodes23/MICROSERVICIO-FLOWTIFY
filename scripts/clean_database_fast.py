"""
Limpiador RÁPIDO de base de datos (sin confirmación)
Para usar en scripts automatizados de testing

USO:
    python scripts/clean_database_fast.py
    python scripts/clean_database_fast.py --keep users,config  # Preservar tablas
"""
import sys
import pymysql
import argparse


def clean_database(
    host='localhost',
    port=3307,
    user='root',
    password='',
    database='logistics_db',
    keep_tables=None
):
    """Limpiar base de datos rápidamente"""
    keep_tables = keep_tables or []
    
    try:
        # Conectar
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        cursor = conn.cursor()
        
        print(f"🗑️  Limpiando BD: {database}")
        
        # Obtener tablas
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("✓ No hay tablas")
            return
        
        # Desactivar FK checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        cleaned = 0
        skipped = 0
        
        for table in tables:
            if table in keep_tables:
                print(f"  ⊘ Saltando: {table}")
                skipped += 1
                continue
            
            try:
                cursor.execute(f"TRUNCATE TABLE `{table}`")
                cleaned += 1
                print(f"  ✓ {table}")
            except Exception as e:
                print(f"  ✗ {table}: {e}")
        
        # Reactivar FK checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        
        print(f"\n✅ Limpiadas: {cleaned} | Excluidas: {skipped}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Limpiar base de datos rápidamente')
    parser.add_argument('--host', default='localhost', help='Host de MySQL')
    parser.add_argument('--port', type=int, default=3307, help='Puerto de MySQL')
    parser.add_argument('--user', default='root', help='Usuario de MySQL')
    parser.add_argument('--password', default='', help='Password de MySQL')
    parser.add_argument('--database', default='logistics_db', help='Nombre de la BD')
    parser.add_argument('--keep', default='', help='Tablas a preservar (separadas por coma)')
    
    args = parser.parse_args()
    
    keep_tables = [t.strip() for t in args.keep.split(',') if t.strip()]
    
    clean_database(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        keep_tables=keep_tables,
    )

