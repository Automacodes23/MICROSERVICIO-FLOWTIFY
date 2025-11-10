"""Verificar que WebhookService se inyecta correctamente"""
import asyncio
from app.api.dependencies import get_webhook_service
from app.core.database import db

async def test():
    print("Verificando creación de WebhookService...")
    
    ws = await get_webhook_service(db)
    
    if ws is None:
        print("❌ WebhookService es None!")
        print("\nPosibles causas:")
        print("1. WEBHOOKS_ENABLED=false en .env")
        print("2. Error al crear WebhookService")
        print("3. Problema de importación")
        return False
    else:
        print(f"✅ WebhookService creado correctamente")
        print(f"   Target URL: {ws.target_url}")
        print(f"   Secret: {ws.secret_key[:20] if ws.secret_key else None}...")
        print(f"   Timeout: {ws.timeout}")
        return True

if __name__ == "__main__":
    result = asyncio.run(test())
    exit(0 if result else 1)

