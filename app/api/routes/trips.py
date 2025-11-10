"""
Router para endpoints de viajes
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.logging import get_logger
from app.core.errors import TripNotFoundError, BaseServiceError, BusinessLogicError
from app.services.trip_service import TripService
from app.api.dependencies import get_trip_service
from app.models.trip import TripCreate, TripCompletion
from app.models.responses import TripCreatedResponse, SuccessResponse, ErrorResponse, ErrorDetail

router = APIRouter(prefix="/trips", tags=["Trips"])
logger = get_logger(__name__)


@router.post("/create", response_model=TripCreatedResponse)
async def create_trip(
    payload: TripCreate,
    trip_service: TripService = Depends(get_trip_service),
):
    """
    Crear un nuevo viaje desde Floatify

    Este endpoint recibe el payload completo de Floatify y orquesta:
    - Creación de unidad y conductor
    - Creación del viaje
    - Creación de geocercas
    - Creación de grupo de WhatsApp
    - Envío de mensaje de bienvenida
    """
    try:
        result = await trip_service.create_trip_from_floatify(payload)
        return result

    except BaseServiceError as e:
        logger.error("trip_creation_endpoint_error", error=str(e), code=e.code)
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "success": False,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "context": e.context,
                },
            },
        )
    except Exception as e:
        logger.error("trip_creation_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                },
            },
        )


@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,  # Cambio a str para soportar UUID
    trip_service: TripService = Depends(get_trip_service),
):
    """Obtener información de un viaje por ID"""
    try:
        trip = await trip_service.get_trip_by_id(trip_id)
        return SuccessResponse(data=trip)

    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_trip_error", error=str(e), trip_id=trip_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{trip_id}/complete")
async def complete_trip(
    trip_id: str,  # Cambio a str para soportar UUID
    payload: TripCompletion,
    trip_service: TripService = Depends(get_trip_service),
):
    """
    Completar un viaje

    Marca el viaje como finalizado y actualiza el subestado final.
    """
    try:
        trip = await trip_service.complete_trip(trip_id, payload.final_substatus)
        return SuccessResponse(
            data=trip,
            message="Viaje completado exitosamente",
        )

    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("complete_trip_error", error=str(e), trip_id=trip_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{trip_id}/status")
async def update_trip_status(
    trip_id: str,  # Cambio a str para soportar UUID
    status: str,
    substatus: str,
    trip_service: TripService = Depends(get_trip_service),
):
    """Actualizar estado de un viaje"""
    try:
        trip = await trip_service.update_trip_status(trip_id, status, substatus)
        return SuccessResponse(
            data=trip,
            message="Estado actualizado exitosamente",
        )

    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("update_status_error", error=str(e), trip_id=trip_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{trip_id}/cleanup_group",
    response_model=SuccessResponse,
    summary="Limpiar Grupo de WhatsApp (Testing)"
)
async def cleanup_trip_group(
    trip_id: str,
    trip_service: TripService = Depends(get_trip_service),
):
    """
    Endpoint para pruebas: Hace que el bot abandone el grupo
    de WhatsApp asociado al viaje y desactiva la conversación.
    
    **IMPORTANTE**: Este endpoint está diseñado para limpieza después de pruebas.
    No debe usarse en producción sin considerar las implicaciones.
    
    **Advertencias**:
    - El bot no podrá volver a unirse al grupo sin ser agregado manualmente
    - La conversación se marcará como inactiva en la base de datos
    - Si el grupo ya fue eliminado o el bot ya fue expulsado, la operación puede fallar
    """
    try:
        result = await trip_service.cleanup_trip_group(trip_id)
        
        if not result.get("success"):
            raise BusinessLogicError(result.get("message", "Error desconocido en la limpieza"))
             
        return SuccessResponse(
            message=result.get("message"),
            data={"trip_id": trip_id, "cleaned": True}
        )
        
    except (TripNotFoundError, BusinessLogicError) as e:
        logger.error(
            "cleanup_trip_group_endpoint_error", 
            error=str(e), 
            code=e.code, 
            trip_id=trip_id
        )
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "success": False,
                "error": {
                    "code": e.code, 
                    "message": e.message, 
                    "context": e.context
                },
            },
        )
    except Exception as e:
        logger.error("cleanup_trip_group_unexpected_error", error=str(e), trip_id=trip_id)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR", 
                    "message": str(e)
                },
            },
        )

