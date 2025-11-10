"""Limpiar BD - Version Windows sin emojis"""
import pymysql

print("Conectando a BD...")
conn = pymysql.connect(
    host='localhost',
    port=3307,
    user='root',
    password='',
    database='logistics_db',
)
cursor = conn.cursor()

# Obtener tablas
cursor.execute("SHOW TABLES")
tables = [row[0] for row in cursor.fetchall()]

print(f"Encontradas {len(tables)} tablas")
print("\nLimpiando...")
print("-" * 60)

# Desactivar FK checks
cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

cleaned = 0
for table in tables:
    try:
        cursor.execute(f"TRUNCATE TABLE `{table}`")
        print(f"OK  {table}")
        cleaned += 1
    except Exception as e:
        print(f"ERR {table}: {e}")

# Reactivar FK checks
cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()

print("-" * 60)
print(f"Limpiadas: {cleaned}/{len(tables)} tablas")

cursor.close()
conn.close()

print("\nBD limpiada exitosamente!")

