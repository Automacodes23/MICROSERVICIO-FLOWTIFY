"""
Dependencias compartidas para FastAPI
"""
from app.core.database import db
from app.config import settings
from app.services.trip_service import TripService
from app.services.event_service import EventService
from app.services.message_service import MessageService
from app.services.notification_service import NotificationService
from app.integrations.evolution.client import EvolutionClient
from app.integrations.gemini.client import GeminiClient
from app.integrations.floatify.client import FloatifyClient


# Clientes de integración (singleton)
_evolution_client = None
_gemini_client = None
_floatify_client = None


def get_evolution_client() -> EvolutionClient:
    """Obtener cliente de Evolution API"""
    global _evolution_client
    if _evolution_client is None:
        _evolution_client = EvolutionClient(
            api_url=settings.evolution_api_url,
            api_key=settings.evolution_api_key,
            instance=settings.evolution_instance_name,
            timeout=settings.http_timeout,
        )
    return _evolution_client


def get_gemini_client() -> GeminiClient:
    """Obtener cliente de Gemini AI"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=settings.gemini_timeout,
        )
    return _gemini_client


def get_floatify_client() -> FloatifyClient:
    """Obtener cliente de Floatify"""
    global _floatify_client
    if _floatify_client is None:
        _floatify_client = FloatifyClient(
            api_url=settings.floatify_api_url,
            api_key=settings.floatify_api_key,
            timeout=settings.http_timeout,
        )
    return _floatify_client


def get_trip_service() -> TripService:
    """Obtener servicio de viajes"""
    return TripService(
        db=db,
        evolution_client=get_evolution_client(),
    )


def get_event_service() -> EventService:
    """Obtener servicio de eventos"""
    return EventService(
        db=db,
        evolution_client=get_evolution_client(),
    )


def get_message_service() -> MessageService:
    """Obtener servicio de mensajes"""
    return MessageService(
        db=db,
        gemini_client=get_gemini_client(),
        evolution_client=get_evolution_client(),
    )


def get_notification_service() -> NotificationService:
    """Obtener servicio de notificaciones"""
    return NotificationService(
        db=db,
        evolution_client=get_evolution_client(),
    )

