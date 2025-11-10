"""
Modelos Pydantic para mensajes de WhatsApp
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WhatsAppMessageData(BaseModel):
    """Datos del mensaje de WhatsApp desde Evolution API"""

    key: Dict[str, Any] = Field(..., description="Clave del mensaje")
    pushName: Optional[str] = Field(None, description="Nombre del remitente")
    message: Dict[str, Any] = Field(..., description="Contenido del mensaje")
    messageType: str = Field(..., description="Tipo de mensaje")
    messageTimestamp: int = Field(..., description="Timestamp del mensaje")


class WhatsAppMessage(BaseModel):
    """Schema de mensaje de WhatsApp desde Evolution API"""

    event: str = Field(..., description="Tipo de evento")
    instance: str = Field(..., description="Instancia de Evolution API")
    data: WhatsAppMessageData = Field(..., description="Datos del mensaje")
    sender: str = Field(..., description="Remitente del mensaje")


class MessageCreate(BaseModel):
    """Schema para crear un mensaje en la BD"""

    conversation_id: str  # UUID como string
    trip_id: str  # UUID como string
    whatsapp_message_id: Optional[str] = None
    sender_type: str = Field(..., description="Tipo de remitente (driver, bot, supervisor, system)")
    sender_phone: Optional[str] = None
    direction: str = Field(..., description="Dirección (inbound, outbound)")
    content: str = Field(..., description="Contenido del mensaje")
    transcription: Optional[str] = Field(None, description="Transcripción si era audio")
    ai_result: Optional[Dict[str, Any]] = Field(None, description="Resultado de IA")


class Message(MessageCreate):
    """Schema completo de mensaje"""

    id: str  # UUID como string
    created_at: datetime

    model_config = {"from_attributes": True}


class AIInteractionCreate(BaseModel):
    """Schema para crear una interacción de IA"""

    message_id: str  # UUID como string
    trip_id: str  # UUID como string
    input_text: str
    response_text: Optional[str] = None
    response_metadata: Dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None
    confidence: Optional[float] = None
    entities: Dict[str, Any] = Field(default_factory=dict)


class AIInteraction(AIInteractionCreate):
    """Schema completo de interacción de IA"""

    id: str  # UUID como string
    created_at: datetime

    model_config = {"from_attributes": True}


class GeminiResponse(BaseModel):
    """Respuesta de Gemini AI"""

    intent: str = Field(..., description="Intención detectada")
    confidence: float = Field(..., description="Confianza de la clasificación")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entidades extraídas")
    response: str = Field(..., description="Respuesta generada para el conductor")
    action: str = Field(..., description="Acción a realizar")
    new_substatus: Optional[str] = Field(None, description="Nuevo subestado si aplica")

