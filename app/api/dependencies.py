"""
Dependencias de FastAPI para inyección de servicios
"""
from typing import Optional
from fastapi import Depends

from app.core.database import Database, db
from app.config import settings


# Instancia global de WebhookService (singleton)
_webhook_service: Optional[any] = None


async def get_database() -> Database:
    """
    Obtener instancia de base de datos
    
    Returns:
        Instancia de Database
    """
    return db


async def get_webhook_service(database: Database = Depends(get_database)):
    """
    Obtener instancia de WebhookService
    
    Usa singleton para reutilizar la misma instancia y su cliente HTTP
    
    Args:
        database: Dependencia de base de datos
        
    Returns:
        Instancia de WebhookService o None si webhooks están deshabilitados
    """
    global _webhook_service
    
    # Si webhooks están deshabilitados globalmente, retornar None
    if not settings.webhooks_enabled:
        return None
    
    # Si no existe la instancia, crearla
    if _webhook_service is None:
        try:
            # Importar aquí para evitar circular imports
            from app.services.webhook_service import WebhookService
            
            _webhook_service = WebhookService(
                db=database,
                target_url=settings.flowtify_webhook_url,
                secret_key=settings.webhook_secret,
                timeout=settings.webhook_timeout,
            )
        except Exception as e:
            # Log error pero retornar None para que el sistema funcione
            print(f"ERROR creando WebhookService: {e}")
            return None
    
    return _webhook_service


async def get_evolution_client():
    """
    Obtener instancia de Evolution API client
    
    Returns:
        Instancia de EvolutionClient o None si no está configurado
    """
    # Si no está configurado, retornar None
    if not settings.evolution_api_url or not settings.evolution_api_key:
        return None
    
    # Importar aquí para evitar circular imports
    from app.integrations.evolution.client import EvolutionClient
    
    return EvolutionClient(
        api_url=settings.evolution_api_url,
        api_key=settings.evolution_api_key,
        instance=settings.evolution_instance_name,
        timeout=settings.http_timeout,
    )


async def get_trip_service(
    database: Database = Depends(get_database),
    evolution_client = Depends(get_evolution_client),
    webhook_service = Depends(get_webhook_service),
):
    """
    Obtener instancia de TripService con todas sus dependencias
    
    Args:
        database: Dependencia de base de datos
        evolution_client: Cliente de Evolution API
        webhook_service: Servicio de webhooks (opcional)
        
    Returns:
        Instancia configurada de TripService
    """
    from app.services.trip_service import TripService
    
    return TripService(
        db=database,
        evolution_client=evolution_client,
        webhook_service=webhook_service,
    )


async def get_event_service(
    database: Database = Depends(get_database),
    evolution_client = Depends(get_evolution_client),
    webhook_service = Depends(get_webhook_service),
):
    """
    Obtener instancia de EventService con todas sus dependencias
    
    Args:
        database: Dependencia de base de datos
        evolution_client: Cliente de Evolution API
        webhook_service: Servicio de webhooks (opcional)
        
    Returns:
        Instancia configurada de EventService
    """
    from app.services.event_service import EventService
    
    return EventService(
        db=database,
        evolution_client=evolution_client,
        webhook_service=webhook_service,
    )


async def get_message_service(
    database: Database = Depends(get_database),
):
    """
    Obtener instancia de MessageService
    
    Args:
        database: Dependencia de base de datos
        
    Returns:
        Instancia de MessageService
    """
    from app.services.message_service import MessageService
    from app.integrations.gemini.client import GeminiClient
    
    gemini_client = GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=settings.gemini_timeout,
    )
    
    evolution_client = await get_evolution_client()
    
    return MessageService(
        db=database,
        gemini_client=gemini_client,
        evolution_client=evolution_client,
    )


async def get_notification_service(
    database: Database = Depends(get_database),
    evolution_client = Depends(get_evolution_client),
    webhook_service = Depends(get_webhook_service),
):
    """
    Obtener instancia de NotificationService
    
    Args:
        database: Dependencia de base de datos
        evolution_client: Cliente de Evolution API
        webhook_service: Servicio de webhooks (opcional)
        
    Returns:
        Instancia de NotificationService
    """
    from app.services.notification_service import NotificationService
    
    return NotificationService(
        db=database,
        evolution_client=evolution_client,
        webhook_service=webhook_service,
    )


async def shutdown_webhook_service():
    """
    Cerrar cliente HTTP de WebhookService en shutdown
    
    Debe llamarse en el evento de shutdown de FastAPI
    """
    global _webhook_service
    if _webhook_service:
        await _webhook_service.close()
        _webhook_service = None
