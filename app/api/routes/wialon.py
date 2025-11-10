"""
Router para webhooks de Wialon
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from app.core.logging import get_logger
from app.core.errors import BaseServiceError
from app.services.event_service import EventService
from app.api.dependencies import get_event_service
from app.integrations.wialon.parser import parse_wialon_event, normalize_wialon_event
from app.models.event import WialonEvent
from app.models.responses import EventProcessedResponse

router = APIRouter(prefix="/wialon", tags=["Wialon"])
logger = get_logger(__name__)


@router.get("/debug/trip/{wialon_unit_id}")
async def debug_find_trip(
    wialon_unit_id: str,
    event_service: EventService = Depends(get_event_service),
):
    """
    Endpoint de depuración temporal para verificar búsqueda de viajes
    """
    from app.repositories.trip_repository import TripRepository
    from app.repositories.unit_repository import UnitRepository
    from app.core.database import db as database
    
    trip_repo = TripRepository(database)
    unit_repo = UnitRepository(database)
    
    # 1. Buscar unidad
    unit = await unit_repo.find_by_wialon_id(wialon_unit_id)
    
    # 2. Buscar viaje activo
    trip = await trip_repo.find_active_by_wialon_id(wialon_unit_id)
    
    return {
        "wialon_unit_id": wialon_unit_id,
        "unit_found": unit is not None,
        "unit": unit,
        "trip_found": trip is not None,
        "trip": trip
    }


@router.post("/events", response_model=EventProcessedResponse)
async def receive_wialon_event(
    request: Request,
    event_service: EventService = Depends(get_event_service),
):
    """
    Recibir eventos de Wialon

    Wialon puede enviar eventos en diferentes formatos:
    - application/json
    - application/x-www-form-urlencoded
    - text/plain

    Este endpoint los procesa todos y los normaliza.
    """
    try:
        # Obtener content type y body
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        
        # DEBUG: Log del evento recibido
        logger.info("wialon_event_received", content_type=content_type, body_size=len(body))

        # Parsear evento según el content type
        raw_data = parse_wialon_event(body, content_type)

        if not raw_data:
            logger.warning("wialon_empty_payload")
            return {"success": False, "message": "Empty or invalid payload"}

        # Normalizar evento
        normalized_data = normalize_wialon_event(raw_data)

        # Validar con Pydantic
        event = WialonEvent(**normalized_data)

        # Procesar evento (incluye envío de notificación WhatsApp si es necesario)
        result = await event_service.process_wialon_event(event)

        return EventProcessedResponse(
            success=True,
            event_id=result.get("event_id"),  # None es válido para Optional[str]
            trip_id=result.get("trip_id"),
            message=result.get("message", "Event processed"),
        )

    except BaseServiceError as e:
        logger.error("wialon_event_processing_error", error=str(e), code=e.code)
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "success": False,
                "error": {
                    "code": e.code,
                    "message": e.message,
                },
            },
        )
    except Exception as e:
        logger.error("wialon_unexpected_error", error=str(e))
        # Retornar 200 para que Wialon no reenvíe
        return {
            "success": False,
            "message": f"Error: {str(e)}",
        }

