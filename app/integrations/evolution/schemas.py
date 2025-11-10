"""
Schemas para Evolution API
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SendTextRequest(BaseModel):
    """Request para enviar mensaje de texto"""

    number: str = Field(..., description="Número o ID del grupo")
    text: str = Field(..., description="Texto del mensaje")


class SendAudioRequest(BaseModel):
    """Request para enviar audio"""

    number: str = Field(..., description="Número o ID del grupo")
    audio: str = Field(..., description="URL o base64 del audio")


class CreateGroupRequest(BaseModel):
    """Request para crear grupo"""

    subject: str = Field(..., description="Nombre del grupo")
    participants: List[str] = Field(..., description="Lista de participantes")


class AddParticipantsRequest(BaseModel):
    """Request para agregar participantes"""

    groupJid: str = Field(..., description="ID del grupo")
    participants: List[str] = Field(..., description="Lista de participantes a agregar")


class EvolutionAPIResponse(BaseModel):
    """Respuesta genérica de Evolution API"""

    status: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None

