"""Script rápido para verificar conexión a MySQL"""
import asyncio
import aiomysql

async def test_connection():
    try:
        print("Conectando a MySQL...")
        conn = await aiomysql.connect(
            host='localhost',
            port=3307,
            user='root',
            password='',
            db='logistics_db'
        )
        print("✅ MySQL conectado OK")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)

