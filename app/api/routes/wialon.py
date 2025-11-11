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
from datetime import datetime
from pydantic import ValidationError
import json
import os

router = APIRouter(prefix="/wialon", tags=["Wialon"])
logger = get_logger(__name__)

# Configuración del archivo de log de webhooks
import pathlib
# Usar ruta absoluta basada en la raíz del proyecto
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
WIALON_WEBHOOK_LOG = PROJECT_ROOT / "wialon_webhooks.log"


def log_webhook_to_file(
    content_type: str,
    headers: dict,
    body: bytes,
    parsed_data: dict = None,
    success: bool = True,
    error_message: str = None
):
    """
    Registra todos los webhooks de Wialon en un archivo de texto plano
    
    Args:
        content_type: Content-Type del request
        headers: Headers del request
        body: Body raw del request
        parsed_data: Datos parseados (opcional)
        success: Si el procesamiento fue exitoso
        error_message: Mensaje de error si falló
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        separator = "=" * 100
        
        # Determinar status visual
        if success is True:
            status_text = "✓ PROCESADO EXITOSAMENTE"
        elif success is False:
            status_text = f"✗ ERROR: {error_message}"
        else:
            status_text = "⏳ RECIBIDO - En procesamiento..."
        
        log_entry = f"""
{separator}
WIALON WEBHOOK RECIBIDO
{separator}
Timestamp: {timestamp}
Success: {success}
Content-Type: {content_type}

--- HEADERS ---
{json.dumps(dict(headers), indent=2, ensure_ascii=False)}

--- BODY RAW ({len(body)} bytes) ---
{body.decode('utf-8', errors='replace')}

--- PARSED DATA ---
{json.dumps(parsed_data, indent=2, ensure_ascii=False) if parsed_data else 'N/A'}

--- STATUS ---
{status_text}
{separator}

"""
        
        # 🔥 ESCRIBIR AL ARCHIVO (append mode) con flush inmediato
        log_path = str(WIALON_WEBHOOK_LOG)
        with open(log_path, 'a', encoding='utf-8', buffering=1) as f:
            f.write(log_entry)
            f.flush()  # Forzar escritura inmediata al disco
        
        # Confirmar que se escribió con ruta completa
        print(f"📝 Webhook logged to: {log_path}", flush=True)
            
    except Exception as e:
        # Si falla el logging a archivo, al menos intentar loguear al sistema
        logger.error("webhook_logging_failed", error=str(e))
        # Intentar escribir directamente con print para debugging
        print(f"❌ ERROR AL LOGUEAR WEBHOOK: {e}", flush=True)
        print(f"Body: {body.decode('utf-8', errors='replace')[:200]}", flush=True)


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
    
    TODOS los webhooks recibidos se registran en: wialon_webhooks.log
    """
    raw_data = None
    normalized_data = None
    body = b""  # Inicializar para evitar errores
    
    try:
        # Obtener content type, headers y body
        content_type = request.headers.get("content-type", "")
        headers = request.headers
        body = await request.body()
        
        # 🔥🔥🔥 LOGUEAR INMEDIATAMENTE - PRIMER PUNTO DE CONTACTO
        logger.info("wialon_webhook_received_raw", 
                   content_type=content_type, 
                   body_size=len(body),
                   body_preview=body.decode('utf-8', errors='replace')[:200])
        
        # 🔥 REGISTRAR EN ARCHIVO INMEDIATAMENTE (ANTES de parsear)
        # Esto garantiza que SIEMPRE quede registro, incluso si falla después
        log_webhook_to_file(
            content_type=content_type,
            headers=headers,
            body=body,
            parsed_data={"status": "RECIBIDO - En procesamiento..."},
            success=None,  # Aún no sabemos
            error_message=None
        )
        
        # Parsear evento según el content type
        raw_data = parse_wialon_event(body, content_type)

        if not raw_data:
            logger.warning("wialon_empty_payload")
            # Registrar en archivo incluso si está vacío
            log_webhook_to_file(
                content_type=content_type,
                headers=headers,
                body=body,
                parsed_data=None,
                success=False,
                error_message="Empty or invalid payload"
            )
            return {"success": False, "message": "Empty or invalid payload"}

        # 🔥 LOGUEAR DATOS PARSEADOS (antes de normalizar)
        logger.info("wialon_webhook_parsed", raw_data=raw_data)
        
        # Normalizar evento
        normalized_data = normalize_wialon_event(raw_data)
        
        # 🔥 LOGUEAR DATOS NORMALIZADOS (antes de validar Pydantic)
        logger.info("wialon_webhook_normalized", normalized_data=normalized_data)

        # Validar con Pydantic
        try:
            event = WialonEvent(**normalized_data)
        except ValidationError as validation_error:
            # 🔥 ERROR DE VALIDACIÓN - LOGUEAR DETALLADAMENTE
            logger.error(
                "wialon_pydantic_validation_failed",
                errors=validation_error.errors(),
                normalized_data=normalized_data
            )
            
            # Registrar en archivo con detalles del error
            log_webhook_to_file(
                content_type=content_type,
                headers=headers,
                body=body,
                parsed_data={
                    "raw_data": raw_data,
                    "normalized_data": normalized_data,
                    "validation_errors": validation_error.errors()
                },
                success=False,
                error_message=f"Pydantic validation failed: {validation_error.errors()}"
            )
            
            # Retornar 200 para que Wialon no reenvíe
            return {
                "success": False,
                "message": "Validation error - check fields",
                "errors": validation_error.errors()
            }

        # Procesar evento (incluye envío de notificación WhatsApp si es necesario)
        result = await event_service.process_wialon_event(event)
        
        # ✅ REGISTRAR WEBHOOK EXITOSO EN ARCHIVO
        log_webhook_to_file(
            content_type=content_type,
            headers=headers,
            body=body,
            parsed_data={
                "raw_data": raw_data,
                "normalized_data": normalized_data,
                "processing_result": {
                    "event_id": result.get("event_id"),
                    "trip_id": result.get("trip_id"),
                    "message": result.get("message", "Event processed")
                }
            },
            success=True
        )

        return EventProcessedResponse(
            success=True,
            event_id=result.get("event_id"),  # None es válido para Optional[str]
            trip_id=result.get("trip_id"),
            message=result.get("message", "Event processed"),
        )

    except BaseServiceError as e:
        logger.error("wialon_event_processing_error", error=str(e), code=e.code)
        
        # ✗ REGISTRAR ERROR EN ARCHIVO
        log_webhook_to_file(
            content_type=request.headers.get("content-type", ""),
            headers=request.headers,
            body=await request.body() if hasattr(request, 'body') else b"",
            parsed_data={"raw_data": raw_data, "normalized_data": normalized_data} if raw_data else None,
            success=False,
            error_message=f"{e.code}: {e.message}"
        )
        
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
        
        # ✗ REGISTRAR ERROR INESPERADO EN ARCHIVO
        try:
            log_webhook_to_file(
                content_type=request.headers.get("content-type", ""),
                headers=request.headers,
                body=body if 'body' in locals() else b"",
                parsed_data={"raw_data": raw_data, "normalized_data": normalized_data} if raw_data else None,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
        except:
            pass  # Evitar que el logging falle el webhook
        
        # Retornar 200 para que Wialon no reenvíe
        return {
            "success": False,
            "message": f"Error: {str(e)}",
        }

