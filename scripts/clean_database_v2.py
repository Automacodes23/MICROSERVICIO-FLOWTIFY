"""
Limpiador de BD v2 - Versión mejorada sin trabas
"""
import pymysql
import sys
from typing import List, Tuple


def clean_database_v2(
    host='localhost',
    port=3307,
    user='root',
    password='',
    database='logistics_db',
    exclude_tables: List[str] = None
) -> bool:
    """
    Limpiar todas las tablas de la BD
    
    Returns:
        True si fue exitoso
    """
    exclude_tables = exclude_tables or []
    
    conn = None
    cursor = None
    
    try:
        # 1. CONECTAR
        print(f"\n🔌 Conectando a {database}...")
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            autocommit=False,  # Importante para control manual
        )
        cursor = conn.cursor()
        print("✓ Conectado")
        
        # 2. OBTENER TABLAS
        print("\n📋 Obteniendo lista de tablas...")
        cursor.execute("SHOW TABLES")
        all_tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Encontradas {len(all_tables)} tablas")
        
        if not all_tables:
            print("⚠️  No hay tablas en la BD")
            return True
        
        # Mostrar tablas con datos
        print("\n📊 Verificando contenido...")
        tables_info = []
        for table in all_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                tables_info.append((table, count))
                if count > 0:
                    print(f"  • {table}: {count:,} filas")
            except Exception as e:
                print(f"  ⚠️  {table}: Error contando ({e})")
                tables_info.append((table, 0))
        
        total_rows = sum(count for _, count in tables_info)
        
        if total_rows == 0:
            print("\n✅ La BD ya está vacía")
            return True
        
        # 3. CONFIRMAR
        print(f"\n⚠️  Se borrarán {total_rows:,} filas de {len(all_tables)} tablas")
        response = input("Escribe 'SI' para confirmar: ")
        
        if response.strip().upper() != 'SI':
            print("❌ Cancelado")
            return False
        
        # 4. LIMPIAR
        print("\n🗑️  Limpiando tablas...")
        print("-" * 60)
        
        # CRÍTICO: Desactivar FK checks ANTES de empezar
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        print("🔓 Foreign keys desactivados")
        
        cleaned = 0
        errors = 0
        
        for i, (table, count) in enumerate(tables_info, 1):
            if table in exclude_tables:
                print(f"[{i}/{len(all_tables)}] ⊘ {table} (excluida)")
                continue
            
            try:
                # TRUNCATE es más rápido y seguro que DELETE
                cursor.execute(f"TRUNCATE TABLE `{table}`")
                
                if count > 0:
                    print(f"[{i}/{len(all_tables)}] ✓ {table} ({count:,} filas)")
                else:
                    print(f"[{i}/{len(all_tables)}] - {table} (vacía)")
                
                cleaned += 1
                
            except Exception as e:
                print(f"[{i}/{len(all_tables)}] ✗ {table}: {e}")
                errors += 1
        
        # 5. REACTIVAR FK checks
        print("\n🔒 Reactivando foreign keys...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("✓ Foreign keys reactivados")
        
        # 6. COMMIT
        print("\n💾 Guardando cambios...")
        conn.commit()
        print("✓ Cambios guardados")
        
        # 7. RESUMEN
        print("\n" + "=" * 60)
        print("✅ LIMPIEZA COMPLETADA")
        print("=" * 60)
        print(f"  • Tablas limpiadas: {cleaned}")
        print(f"  • Errores: {errors}")
        print(f"  • Total filas eliminadas: {total_rows:,}")
        print("=" * 60)
        
        return errors == 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado por el usuario")
        if conn:
            conn.rollback()
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if conn:
            print("🔙 Haciendo rollback...")
            conn.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # SIEMPRE cerrar conexión
        if cursor:
            try:
                cursor.close()
                print("\n✓ Cursor cerrado")
            except:
                pass
        
        if conn:
            try:
                conn.close()
                print("✓ Conexión cerrada")
            except:
                pass


def main():
    """Función principal"""
    print("\n" + "=" * 60)
    print("🧹 LIMPIADOR DE BASE DE DATOS v2")
    print("=" * 60)
    
    # Configuración
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3307,
        'user': 'root',
        'password': '',
        'database': 'logistics_db',
    }
    
    # Tablas a NO tocar (opcional)
    EXCLUDE_TABLES = [
        # 'users',  # Descomentar para preservar
    ]
    
    try:
        success = clean_database_v2(**DB_CONFIG, exclude_tables=EXCLUDE_TABLES)
        
        if success:
            print("\n✅ Todo OK")
            sys.exit(0)
        else:
            print("\n⚠️  Limpieza terminó con errores")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Interrumpido")
        sys.exit(1)


if __name__ == "__main__":
    main()

