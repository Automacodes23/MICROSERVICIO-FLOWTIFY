"""Ver schema de trips"""
import pymysql

conn = pymysql.connect(
    host='localhost',
    port=3307,
    user='root',
    password='',
    db='logistics_db'
)

cursor = conn.cursor()
cursor.execute('DESCRIBE trips')

print("Columnas de la tabla 'trips':")
print("-" * 50)
for row in cursor.fetchall():
    print(f"  {row[0]} ({row[1]})")

conn.close()

