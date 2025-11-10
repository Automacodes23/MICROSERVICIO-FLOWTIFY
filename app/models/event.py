"""
Modelos Pydantic para eventos de Wialon
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WialonEventBase(BaseModel):
    """Base para evento de Wialon"""

    unit_name: str = Field(..., description="Nombre de la unidad")
    unit_id: str = Field(..., description="ID de la unidad en Wialon")
    notification_type: str = Field(..., description="Tipo de notificación")
    notification_id: Optional[str] = Field(None, description="ID único de notificación de Wialon para idempotencia")
    event_time: int = Field(..., description="Timestamp del evento")
    latitude: float = Field(..., description="Latitud")
    longitude: float = Field(..., description="Longitud")
    imei: Optional[str] = Field(None, description="IMEI del dispositivo")
    altitude: Optional[float] = Field(None, description="Altitud")
    speed: Optional[float] = Field(None, description="Velocidad")
    course: Optional[int] = Field(None, description="Curso/dirección")
    address: Optional[str] = Field(None, description="Dirección geocodificada")
    pos_time: Optional[str] = Field(None, description="Timestamp de posición")
    driver_name: Optional[str] = Field(None, description="Nombre del conductor")
    driver_code: Optional[str] = Field(None, description="Código del conductor")
    geofence_name: Optional[str] = Field(None, description="Nombre de la geocerca")
    geofence_id: Optional[str] = Field(None, description="ID de la geocerca")
    max_speed: Optional[float] = Field(None, description="Velocidad máxima permitida")
    deviation_distance_km: Optional[float] = Field(None, description="Distancia de desviación en km")
    last_message_time: Optional[str] = Field(None, description="Última vez que se recibió mensaje")


class WialonEvent(WialonEventBase):
    """Schema completo de evento de Wialon"""

    pass


class EventCreate(BaseModel):
    """Schema para crear un evento en la BD"""

    trip_id: str  # UUID como string
    unit_id: str  # UUID como string
    source: str = Field(default="wialon", description="Fuente del evento")
    event_type: str = Field(..., description="Tipo de evento")
    latitude: float
    longitude: float
    speed: Optional[float] = None
    address: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(..., description="Payload completo del evento")
    external_id: str = Field(..., description="ID único del evento")


class Event(BaseModel):
    """Schema completo de evento almacenado"""

    id: str  # UUID como string
    external_id: str
    trip_id: str  # UUID como string
    unit_id: str  # UUID como string
    source: str
    event_type: str
    latitude: float
    longitude: float
    speed: Optional[float]
    address: Optional[str]
    raw_payload: Dict[str, Any]
    processed: bool
    processed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

