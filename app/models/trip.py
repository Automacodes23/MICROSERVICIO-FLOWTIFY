"""
Modelos Pydantic para viajes
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class GeofenceInfo(BaseModel):
    """Información de geocerca"""

    role: str = Field(..., description="Rol de la geocerca (origin, loading, unloading, waypoint)")
    geofence_id: str = Field(..., description="ID de la geocerca en Wialon")
    geofence_name: str = Field(..., description="Nombre de la geocerca")
    geofence_type: Optional[str] = Field(None, description="Tipo de geocerca (circle, polygon)")
    order: int = Field(default=0, description="Orden en la secuencia")


class TripBase(BaseModel):
    """Base para viaje"""

    code: str = Field(..., description="Código único del viaje")
    tenant_id: int = Field(..., description="ID del tenant/empresa")
    origin: Optional[str] = Field(None, description="Origen del viaje")
    destination: Optional[str] = Field(None, description="Destino del viaje")
    planned_start: Optional[datetime] = Field(None, description="Inicio planificado")
    planned_end: Optional[datetime] = Field(None, description="Fin planificado")
    status: str = Field(default="planned", description="Estado del viaje")
    substatus: str = Field(default="por_iniciar", description="Subestado del viaje")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")


class TripCreate(BaseModel):
    """Schema para crear un viaje (desde Floatify)"""

    event: str = Field(..., description="Tipo de evento")
    action: str = Field(..., description="Acción a realizar")
    tenant_id: int = Field(..., description="ID del tenant")
    trip: Dict[str, Any] = Field(..., description="Información del viaje")
    driver: Dict[str, Any] = Field(..., description="Información del conductor")
    unit: Dict[str, Any] = Field(..., description="Información de la unidad")
    customer: Optional[Dict[str, Any]] = Field(None, description="Información del cliente")
    geofences: List[GeofenceInfo] = Field(default_factory=list, description="Geocercas del viaje")
    whatsapp_participants: List[str] = Field(default_factory=list, description="Participantes de WhatsApp")
    metadata: Optional[Dict[str, Any]] = None


class TripUpdate(BaseModel):
    """Schema para actualizar un viaje"""

    status: Optional[str] = None
    substatus: Optional[str] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class TripStatusChange(BaseModel):
    """Schema para cambio de estado de viaje"""

    event: str
    timestamp: int
    tenant_id: int
    trip_id: str  # UUID como string
    trip_code: str
    from_status: str
    to_status: str
    trigger: str
    trip: Dict[str, Any]
    driver: Optional[Dict[str, Any]] = None
    unit: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class Trip(TripBase):
    """Schema completo de viaje"""

    id: str  # UUID como string
    external_id: Optional[str] = None
    unit_id: Optional[str] = None  # UUID como string
    driver_id: Optional[str] = None  # UUID como string
    customer_id: Optional[str] = None  # UUID como string
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripCompletion(BaseModel):
    """Schema para completar un viaje"""

    event: str = Field(default="trip.completed", description="Tipo de evento")
    tenant_id: int
    trip_id: str  # UUID como string
    trip_code: str
    final_status: str = Field(default="finalizado")
    final_substatus: str
    timestamp: str
    trigger_details: Dict[str, Any]
    completion_data: Optional[Dict[str, Any]] = None

