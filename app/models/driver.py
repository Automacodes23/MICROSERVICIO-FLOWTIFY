"""
Modelos Pydantic para conductores/operadores
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DriverBase(BaseModel):
    """Base para conductor"""

    name: str = Field(..., description="Nombre del conductor")
    phone: str = Field(..., description="Teléfono del conductor")
    wialon_driver_code: Optional[str] = Field(None, description="Código del conductor en Wialon")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")


class DriverCreate(DriverBase):
    """Schema para crear un conductor"""

    pass


class DriverUpdate(BaseModel):
    """Schema para actualizar un conductor"""

    name: Optional[str] = None
    wialon_driver_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Driver(DriverBase):
    """Schema completo de conductor"""

    id: str  # UUID como string
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

