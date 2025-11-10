"""
Modelos Pydantic para unidades de transporte
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class UnitBase(BaseModel):
    """Base para unidad de transporte"""

    code: str = Field(..., description="Código/nombre de la unidad")
    wialon_id: Optional[str] = Field(None, description="ID de la unidad en Wialon")
    plate: Optional[str] = Field(None, description="Placa de la unidad")
    imei: Optional[str] = Field(None, description="IMEI del dispositivo GPS")
    provider: str = Field(default="wialon", description="Proveedor de rastreo")
    whatsapp_group_id: Optional[str] = Field(None, description="ID del grupo de WhatsApp permanente de la unidad")
    whatsapp_group_name: Optional[str] = Field(None, description="Nombre del grupo de WhatsApp de la unidad")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")


class UnitCreate(UnitBase):
    """Schema para crear una unidad"""

    pass


class UnitUpdate(BaseModel):
    """Schema para actualizar una unidad"""

    wialon_id: Optional[str] = None
    plate: Optional[str] = None
    imei: Optional[str] = None
    provider: Optional[str] = None
    whatsapp_group_id: Optional[str] = None
    whatsapp_group_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Unit(UnitBase):
    """Schema completo de unidad"""

    id: str  # UUID como string
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

