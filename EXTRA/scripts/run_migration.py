"""
Script para ejecutar migraciones SQL en MySQL
"""
import asyncio
import aiomysql
import sys
import os
from pathlib import Path

# Configuración de MySQL
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': '',
    'db': 'logistics_db',
    'charset': 'utf8mb4'
}


async def run_migration(migration_file: str):
    """Ejecutar un archivo de migración SQL"""
    print(f"\n{'='*60}")
    print(f"Ejecutando migración: {migration_file}")
    print(f"{'='*60}\n")
    
    # Leer el archivo SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Conectar a MySQL
    conn = await aiomysql.connect(**MYSQL_CONFIG)
    
    try:
        cursor = await conn.cursor()
        
        # Ejecutar cada statement SQL
        # Separar por ';' pero solo fuera de comentarios
        statements = []
        current_statement = []
        in_comment = False
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Saltar líneas vacías
            if not line:
                continue
                
            # Manejar comentarios
            if line.startswith('--'):
                if 'USE' not in line and 'SELECT' not in line and 'ALTER' not in line:
                    continue
            
            current_statement.append(line)
            
            # Si la línea termina con ';', es el final del statement
            if line.endswith(';'):
                statement = ' '.join(current_statement)
                if statement.strip() and not statement.strip().startswith('--'):
                    statements.append(statement)
                current_statement = []
        
        # Ejecutar cada statement
        for i, statement in enumerate(statements, 1):
            try:
                # Limpiar el statement
                clean_statement = statement.strip()
                if not clean_statement or clean_statement.startswith('--'):
                    continue
                
                print(f"[{i}/{len(statements)}] Ejecutando:")
                print(f"  {clean_statement[:100]}{'...' if len(clean_statement) > 100 else ''}")
                
                await cursor.execute(clean_statement)
                await conn.commit()
                
                # Si es un SELECT, mostrar resultados
                if clean_statement.upper().startswith('SELECT'):
                    rows = await cursor.fetchall()
                    if rows:
                        print(f"\n  Resultados:")
                        for row in rows:
                            print(f"    {row}")
                
                print(f"  [OK] Ejecutado exitosamente\n")
                
            except Exception as e:
                print(f"  [ERROR] Error: {e}\n")
                # Continuar con el siguiente statement
                continue
        
        print(f"{'='*60}")
        print(f"[OK] Migracion completada")
        print(f"{'='*60}\n")
        
    finally:
        await cursor.close()
        conn.close()


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Uso: python run_migration.py <archivo_migracion.sql>")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    
    if not os.path.exists(migration_file):
        print(f"Error: El archivo {migration_file} no existe")
        sys.exit(1)
    
    await run_migration(migration_file)


if __name__ == "__main__":
    asyncio.run(main())

