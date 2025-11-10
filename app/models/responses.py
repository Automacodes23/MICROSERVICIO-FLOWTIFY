"""
Modelos de respuesta estandarizados
"""
from typing import Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Respuesta exitosa estándar"""

    success: bool = Field(default=True, description="Indica si la operación fue exitosa")
    message: Optional[str] = Field(None, description="Mensaje descriptivo")
    data: Optional[T] = Field(None, description="Datos de respuesta")


class ErrorDetail(BaseModel):
    """Detalle de error"""

    code: str = Field(..., description="Código de error")
    message: str = Field(..., description="Mensaje de error")
    field: Optional[str] = Field(None, description="Campo que causó el error")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")


class ErrorResponse(BaseModel):
    """Respuesta de error estándar"""

    success: bool = Field(default=False, description="Indica que la operación falló")
    error: ErrorDetail = Field(..., description="Detalles del error")
    trace_id: Optional[str] = Field(None, description="ID de trazabilidad")


class HealthResponse(BaseModel):
    """Respuesta de health check"""

    status: str = Field(..., description="Estado del servicio")
    timestamp: str = Field(..., description="Timestamp del check")
    service: str = Field(..., description="Nombre del servicio")
    version: str = Field(..., description="Versión del servicio")
    database: Optional[str] = Field(None, description="Estado de la base de datos")


class TripCreatedResponse(BaseModel):
    """Respuesta al crear un viaje"""

    success: bool = True
    trip_id: str  # UUID como string
    trip_code: str
    whatsapp_group_id: Optional[str] = None
    welcome_message_sent: bool = False
    message: str = "Viaje creado exitosamente"


class EventProcessedResponse(BaseModel):
    """Respuesta al procesar un evento"""

    success: bool = True
    event_id: Optional[str] = None  # UUID como string (puede ser None en casos de idempotencia)
    trip_id: Optional[str] = None  # UUID como string
    message: str = "Evento procesado exitosamente"


class MessageProcessedResponse(BaseModel):
    """Respuesta al procesar un mensaje"""

    success: bool = True
    message_id: str  # UUID como string
    ai_result: Optional[Dict[str, Any]] = None
    message: str = "Mensaje procesado exitosamente"

