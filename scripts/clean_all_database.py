"""
Script para limpiar TODA la base de datos (todas las tablas)
Útil para pruebas cuando la BD se llena de datos innecesarios

ADVERTENCIA: Este script BORRA TODOS LOS DATOS de TODAS las tablas
"""
import sys
import pymysql
from datetime import datetime
from typing import List, Tuple


class DatabaseCleaner:
    """Limpiador de base de datos completa"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Conectar a la base de datos"""
        try:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
            )
            self.cursor = self.conn.cursor()
            print(f"✓ Conectado a: {self.database} en {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Error al conectar: {e}")
            return False
    
    def get_all_tables(self) -> List[str]:
        """Obtener lista de todas las tablas en la BD"""
        try:
            self.cursor.execute("SHOW TABLES")
            tables = [row[0] for row in self.cursor.fetchall()]
            return tables
        except Exception as e:
            print(f"✗ Error al obtener tablas: {e}")
            return []
    
    def get_table_row_count(self, table: str) -> int:
        """Obtener cantidad de filas de una tabla"""
        try:
            self.cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = self.cursor.fetchone()[0]
            return count
        except:
            return 0
    
    def get_database_stats(self) -> Tuple[List[Tuple[str, int]], int]:
        """Obtener estadísticas de la BD"""
        tables = self.get_all_tables()
        stats = []
        total_rows = 0
        
        for table in tables:
            count = self.get_table_row_count(table)
            stats.append((table, count))
            total_rows += count
        
        return stats, total_rows
    
    def truncate_all_tables(self, exclude_tables: List[str] = None) -> bool:
        """
        Truncar todas las tablas de la BD
        
        Args:
            exclude_tables: Lista de tablas a excluir (opcional)
        
        Returns:
            True si fue exitoso
        """
        exclude_tables = exclude_tables or []
        
        try:
            tables = self.get_all_tables()
            
            if not tables:
                print("⚠ No hay tablas en la base de datos")
                return True
            
            # Desactivar foreign key checks
            self.cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            print("\n🔓 Foreign key checks desactivados")
            
            cleaned_count = 0
            skipped_count = 0
            
            print(f"\n🗑️  Limpiando {len(tables)} tablas...\n")
            
            for table in tables:
                if table in exclude_tables:
                    print(f"  ⊘ Saltando: {table} (excluida)")
                    skipped_count += 1
                    continue
                
                try:
                    # Obtener count antes de limpiar
                    before_count = self.get_table_row_count(table)
                    
                    # TRUNCATE es más rápido que DELETE
                    self.cursor.execute(f"TRUNCATE TABLE `{table}`")
                    
                    if before_count > 0:
                        print(f"  ✓ {table:30} ({before_count:,} filas eliminadas)")
                    else:
                        print(f"  - {table:30} (ya estaba vacía)")
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    print(f"  ✗ Error en {table}: {e}")
            
            # Reactivar foreign key checks
            self.cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            print("\n🔒 Foreign key checks reactivados")
            
            # Commit
            self.conn.commit()
            
            print(f"\n✅ Limpieza completada:")
            print(f"   - Tablas limpiadas: {cleaned_count}")
            print(f"   - Tablas excluidas: {skipped_count}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error durante limpieza: {e}")
            self.conn.rollback()
            return False
    
    def close(self):
        """Cerrar conexión"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("\n✓ Conexión cerrada")


def confirm_action(database: str) -> bool:
    """Pedir confirmación al usuario"""
    print("\n" + "=" * 70)
    print("⚠️  ADVERTENCIA: OPERACIÓN DESTRUCTIVA ⚠️")
    print("=" * 70)
    print(f"\nEstás a punto de BORRAR TODOS LOS DATOS de la base de datos:")
    print(f"  📦 Database: {database}")
    print("\nEsta operación es IRREVERSIBLE.")
    print("=" * 70)
    
    response = input("\n¿Estás seguro? Escribe 'CONFIRMAR' para continuar: ")
    
    return response.strip().upper() == "CONFIRMAR"


def main():
    """Función principal"""
    
    # Configuración de BD (puedes modificarla o usar variables de entorno)
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3307,
        'user': 'root',
        'password': '',
        'database': 'logistics_db',
    }
    
    print("\n" + "=" * 70)
    print("🧹 LIMPIADOR DE BASE DE DATOS - TODAS LAS TABLAS")
    print("=" * 70)
    print(f"\nBase de datos objetivo: {DB_CONFIG['database']}")
    
    # Crear cleaner
    cleaner = DatabaseCleaner(**DB_CONFIG)
    
    # Conectar
    if not cleaner.connect():
        sys.exit(1)
    
    # Obtener estadísticas ANTES
    print("\n📊 Estado actual de la base de datos:\n")
    stats, total_rows = cleaner.get_database_stats()
    
    if not stats:
        print("⚠ La base de datos está vacía o no se pudieron obtener estadísticas")
        cleaner.close()
        sys.exit(0)
    
    # Mostrar tablas con datos
    tables_with_data = [(table, count) for table, count in stats if count > 0]
    
    if not tables_with_data:
        print("✓ Todas las tablas están vacías. No hay nada que limpiar.")
        cleaner.close()
        sys.exit(0)
    
    print("Tablas con datos:")
    for table, count in tables_with_data:
        print(f"  • {table:30} → {count:,} filas")
    
    print(f"\n  TOTAL: {total_rows:,} filas en {len(tables_with_data)} tablas")
    
    # Tablas a excluir (opcional - puedes descomentar si quieres preservar alguna)
    EXCLUDE_TABLES = [
        # 'users',  # Ejemplo: preservar tabla de usuarios
        # 'config', # Ejemplo: preservar configuración
    ]
    
    if EXCLUDE_TABLES:
        print(f"\n⊘ Tablas que NO se limpiarán: {', '.join(EXCLUDE_TABLES)}")
    
    # Pedir confirmación
    if not confirm_action(DB_CONFIG['database']):
        print("\n❌ Operación cancelada por el usuario")
        cleaner.close()
        sys.exit(0)
    
    # Ejecutar limpieza
    print("\n" + "=" * 70)
    print("🚀 Iniciando limpieza...")
    print("=" * 70)
    
    timestamp_before = datetime.now()
    
    success = cleaner.truncate_all_tables(exclude_tables=EXCLUDE_TABLES)
    
    timestamp_after = datetime.now()
    duration = (timestamp_after - timestamp_before).total_seconds()
    
    if success:
        # Verificar después
        print("\n📊 Verificando limpieza...")
        stats_after, total_after = cleaner.get_database_stats()
        
        if total_after == 0:
            print("✅ Limpieza exitosa - Base de datos completamente vacía")
        else:
            print(f"⚠ Quedan {total_after:,} filas en la BD (probablemente en tablas excluidas)")
        
        print(f"\n⏱️  Tiempo de ejecución: {duration:.2f} segundos")
    else:
        print("\n❌ La limpieza falló. Revisa los errores arriba.")
    
    # Cerrar conexión
    cleaner.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

