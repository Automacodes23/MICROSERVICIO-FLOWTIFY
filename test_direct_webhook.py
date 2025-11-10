"""
Test directo de WebhookService sin FastAPI
"""
import asyncio
from app.core.database import db
from app.services.webhook_service import WebhookService
from app.config import settings

async def test_direct():
    print("Conectando a BD...")
    await db.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database,
        user=settings.mysql_user,
        password=settings.mysql_password,
    )
    
    print("Creando WebhookService...")
    webhook_service = WebhookService(
        db=db,
        target_url=settings.flowtify_webhook_url,
        secret_key=settings.webhook_secret,
        timeout=settings.webhook_timeout,
    )
    
    print(f"Target URL: {webhook_service.target_url}")
    print(f"Secret: {webhook_service.secret_key[:20]}...")
    
    trip_id = "7d4bbc29-be77-11f0-b0de-f4b5205b5b70"
    
    print(f"\nEnviando webhook de prueba para trip {trip_id}...")
    result = await webhook_service.send_status_update(
        trip_id=trip_id,
        old_status="test_old",
        old_substatus="test_old_sub",
        new_status="test_new",
        new_substatus="test_new_sub",
        change_reason="direct_test",
    )
    
    print(f"\nResultado: {result}")
    
    await db.disconnect()
    await webhook_service.close()

if __name__ == "__main__":
    asyncio.run(test_direct())

