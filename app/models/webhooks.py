"""
Modelos Pydantic para webhooks de Flowtify
"""
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WebhookBase(BaseModel):
    """Modelo base para todos los webhooks"""
    event: str = Field(..., description="Tipo de evento del webhook")
    timestamp: str = Field(..., description="Timestamp ISO 8601 con zona horaria")
    tenant_id: int = Field(..., description="ID del tenant/organización")
    api_version: str = Field(default="1.0", description="Versión de la API del webhook")


class TripInfo(BaseModel):
    """Información resumida del viaje para webhooks"""
    id: str = Field(..., description="UUID del viaje")
    floatify_trip_id: Optional[str] = Field(None, description="ID del viaje en Floatify")
    code: Optional[str] = Field(None, description="Código del viaje")
    status: str = Field(..., description="Estado actual del viaje")
    substatus: str = Field(..., description="Subestado actual del viaje")
    origin: Optional[str] = Field(None, description="Origen del viaje")
    destination: Optional[str] = Field(None, description="Destino del viaje")


class DriverInfo(BaseModel):
    """Información del conductor para webhooks"""
    id: Optional[str] = Field(None, description="UUID del conductor")
    name: Optional[str] = Field(None, description="Nombre del conductor")
    phone: Optional[str] = Field(None, description="Teléfono del conductor")
    wialon_driver_code: Optional[str] = Field(None, description="Código del conductor en Wialon")


class UnitInfo(BaseModel):
    """Información de la unidad para webhooks"""
    id: Optional[str] = Field(None, description="UUID de la unidad")
    code: Optional[str] = Field(None, description="Código de la unidad")
    plate: Optional[str] = Field(None, description="Placa de la unidad")
    wialon_id: Optional[str] = Field(None, description="ID de la unidad en Wialon")
    imei: Optional[str] = Field(None, description="IMEI del dispositivo GPS")
    name: Optional[str] = Field(None, description="Nombre de la unidad")


class LocationInfo(BaseModel):
    """Información de ubicación para webhooks"""
    latitude: Optional[float] = Field(None, description="Latitud en grados decimales")
    longitude: Optional[float] = Field(None, description="Longitud en grados decimales")
    altitude: Optional[float] = Field(None, description="Altitud en metros")
    speed: Optional[float] = Field(None, description="Velocidad en km/h")
    course: Optional[float] = Field(None, description="Curso/dirección en grados")
    address: Optional[str] = Field(None, description="Dirección geocodificada")
    last_update: Optional[str] = Field(None, description="Timestamp de última actualización")


class CustomerInfo(BaseModel):
    """Información del cliente para webhooks"""
    id: Optional[str] = Field(None, description="UUID del cliente")
    name: Optional[str] = Field(None, description="Nombre del cliente")


class TimelineInfo(BaseModel):
    """Información de timeline del viaje"""
    created_at: Optional[str] = Field(None, description="Timestamp de creación")
    started_at: Optional[str] = Field(None, description="Timestamp de inicio real")
    updated_at: Optional[str] = Field(None, description="Timestamp de última actualización")


class StatusUpdateWebhook(WebhookBase):
    """Webhook para actualizaciones de estado de viaje"""
    event: str = Field(default="status_update", description="Tipo de evento")
    trip: Dict[str, Any] = Field(..., description="Información completa del viaje con timeline")
    driver: Dict[str, Any] = Field(default_factory=dict, description="Información del conductor")
    unit: Dict[str, Any] = Field(default_factory=dict, description="Información de la unidad")
    location: Dict[str, Any] = Field(default_factory=dict, description="Ubicación actual")
    customer: Optional[Dict[str, Any]] = Field(None, description="Información del cliente")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")


class ViolationInfo(BaseModel):
    """Información de violación de velocidad"""
    type: str = Field(default="excessive_speed", description="Tipo de violación")
    severity: str = Field(..., description="Severidad: low, medium, high")
    detected_speed: float = Field(..., description="Velocidad detectada en km/h")
    max_allowed_speed: float = Field(..., description="Velocidad máxima permitida")
    speed_difference: float = Field(..., description="Diferencia de velocidad")
    percentage_over_limit: float = Field(..., description="Porcentaje sobre el límite")
    duration_seconds: int = Field(default=0, description="Duración de la violación")
    distance_covered_km: float = Field(default=0, description="Distancia recorrida durante violación")
    violation_id: str = Field(..., description="ID único de la violación")
    is_ongoing: bool = Field(default=False, description="Si la violación está en curso")


class ViolationHistoryInfo(BaseModel):
    """Historial de violaciones"""
    total_violations_today: int = Field(default=0, description="Total de violaciones hoy")
    total_violations_trip: int = Field(default=0, description="Total de violaciones en este viaje")
    previous_violation: Optional[Dict[str, Any]] = Field(None, description="Violación anterior")
    violation_streak: int = Field(default=0, description="Racha de violaciones consecutivas")
    time_since_last_violation_minutes: Optional[int] = Field(None, description="Minutos desde última violación")


class WialonSourceInfo(BaseModel):
    """Información de la fuente Wialon"""
    notification_id: Optional[str] = Field(None, description="ID de notificación de Wialon")
    notification_type: Optional[str] = Field(None, description="Tipo de notificación")
    external_id: Optional[str] = Field(None, description="ID externo del evento")


class SpeedViolationWebhook(WebhookBase):
    """Webhook para violaciones de velocidad"""
    event: str = Field(default="speed_violation", description="Tipo de evento")
    violation: Dict[str, Any] = Field(..., description="Información de la violación")
    trip: Dict[str, Any] = Field(..., description="Información del viaje")
    driver: Dict[str, Any] = Field(default_factory=dict, description="Información del conductor")
    unit: Dict[str, Any] = Field(default_factory=dict, description="Información de la unidad")
    location: Dict[str, Any] = Field(default_factory=dict, description="Ubicación de la violación")
    violation_history: Dict[str, Any] = Field(default_factory=dict, description="Historial de violaciones")
    customer: Optional[Dict[str, Any]] = Field(None, description="Información del cliente")
    wialon_source: Dict[str, Any] = Field(default_factory=dict, description="Fuente Wialon")


class TransitionInfo(BaseModel):
    """Información de transición de geocerca"""
    type: str = Field(..., description="Tipo: entry o exit")
    previous_type: Optional[str] = Field(None, description="Tipo anterior")
    transition_id: str = Field(..., description="ID único de la transición")
    direction: str = Field(..., description="Dirección: entering o exiting")


class GeofenceInfo(BaseModel):
    """Información de geocerca"""
    id: str = Field(..., description="ID de la geocerca")
    name: str = Field(..., description="Nombre de la geocerca")
    role: str = Field(..., description="Rol: origin, loading, unloading, route, waypoint, depot")
    type: Optional[str] = Field(None, description="Tipo: circle, polygon, polyline")
    order: Optional[int] = Field(None, description="Orden en la secuencia")
    is_critical_zone: bool = Field(default=False, description="Si es una zona crítica")
    requires_confirmation: bool = Field(default=False, description="Si requiere confirmación")


class TimingInfo(BaseModel):
    """Información de tiempos del viaje"""
    trip_elapsed_time_minutes: int = Field(default=0, description="Tiempo transcurrido del viaje")
    time_since_previous_geofence_minutes: int = Field(default=0, description="Tiempo desde geocerca anterior")
    estimated_wait_time_minutes: Optional[int] = Field(None, description="Tiempo de espera estimado")
    scheduled_departure_time: Optional[str] = Field(None, description="Hora programada de salida")
    on_time_status: Optional[str] = Field(None, description="Estado de puntualidad: early, on-time, late")


class WorkflowTriggersInfo(BaseModel):
    """Información de triggers de workflow"""
    auto_status_update: bool = Field(default=False, description="Si debe actualizar estado automáticamente")
    whatsapp_notification_enabled: bool = Field(default=False, description="Si debe enviar notificación WhatsApp")
    supervisor_alert: bool = Field(default=False, description="Si debe alertar al supervisor")
    requires_driver_action: bool = Field(default=False, description="Si requiere acción del conductor")
    expected_next_status: Optional[str] = Field(None, description="Próximo estado esperado")


class GeofenceTransitionWebhook(WebhookBase):
    """Webhook para transiciones de geocerca"""
    event: str = Field(default="geofence_transition", description="Tipo de evento")
    transition: Dict[str, Any] = Field(..., description="Información de la transición")
    trip: Dict[str, Any] = Field(..., description="Información del viaje")
    driver: Dict[str, Any] = Field(default_factory=dict, description="Información del conductor")
    unit: Dict[str, Any] = Field(default_factory=dict, description="Información de la unidad")
    geofence: Dict[str, Any] = Field(..., description="Información de la geocerca")
    location: Dict[str, Any] = Field(default_factory=dict, description="Ubicación en la transición")
    timing: Dict[str, Any] = Field(default_factory=dict, description="Información de tiempos")
    customer: Optional[Dict[str, Any]] = Field(None, description="Información del cliente")
    wialon_source: Dict[str, Any] = Field(default_factory=dict, description="Fuente Wialon")
    workflow_triggers: Dict[str, Any] = Field(default_factory=dict, description="Triggers de workflow")


class DeviationInfo(BaseModel):
    """Información de desviación de ruta"""
    type: str = Field(default="route_deviation", description="Tipo de desviación")
    severity: str = Field(default="critical", description="Severidad de la desviación")
    deviation_id: str = Field(..., description="ID único de la desviación")
    distance_from_route_meters: float = Field(..., description="Distancia de la ruta en metros")
    max_allowed_deviation: float = Field(default=100, description="Desviación máxima permitida")
    excess_deviation_meters: float = Field(..., description="Exceso de desviación")
    deviation_duration_seconds: int = Field(default=0, description="Duración de la desviación")
    current_location: Dict[str, Any] = Field(default_factory=dict, description="Ubicación actual")
    nearest_point_on_route: Optional[Dict[str, Any]] = Field(None, description="Punto más cercano en la ruta")


class RouteInfo(BaseModel):
    """Información de progreso de ruta"""
    current_leg: str = Field(default="unknown", description="Tramo actual de la ruta")
    progress_percentage: float = Field(default=0, description="Porcentaje de progreso")
    estimated_time_to_destination_hours: Optional[float] = Field(None, description="Tiempo estimado a destino")
    last_known_route_position: Optional[Dict[str, Any]] = Field(None, description="Última posición conocida en ruta")


class ImmediateActionsInfo(BaseModel):
    """Acciones inmediatas tomadas"""
    supervisor_notified: bool = Field(default=False, description="Supervisor notificado")
    driver_contact_attempted: bool = Field(default=False, description="Intento de contacto con conductor")
    whatsapp_alert_sent: bool = Field(default=False, description="Alerta WhatsApp enviada")
    flowtify_critical_alert: bool = Field(default=False, description="Alerta crítica en Flowtify")


class RouteDeviationWebhook(WebhookBase):
    """Webhook para desviaciones de ruta"""
    event: str = Field(default="route_deviation", description="Tipo de evento")
    deviation: Dict[str, Any] = Field(..., description="Información de la desviación")
    trip: Dict[str, Any] = Field(..., description="Información del viaje")
    driver: Dict[str, Any] = Field(default_factory=dict, description="Información del conductor")
    unit: Dict[str, Any] = Field(default_factory=dict, description="Información de la unidad")
    route_info: Dict[str, Any] = Field(default_factory=dict, description="Información de la ruta")
    immediate_actions: Dict[str, Any] = Field(default_factory=dict, description="Acciones inmediatas")
    wialon_source: Dict[str, Any] = Field(default_factory=dict, description="Fuente Wialon")


class CommunicationInfo(BaseModel):
    """Información de comunicación"""
    type: str = Field(..., description="Tipo: bot_response, operator_response, system_notification")
    direction: str = Field(default="outbound", description="Dirección: inbound, outbound")
    message_id: str = Field(..., description="ID del mensaje")
    original_message_id: Optional[str] = Field(None, description="ID del mensaje original")
    conversation_id: Optional[str] = Field(None, description="ID de la conversación")
    response_content: str = Field(..., description="Contenido de la respuesta")
    response_type: Optional[str] = Field(None, description="Tipo de respuesta")
    language: str = Field(default="es", description="Idioma del mensaje")
    character_count: Optional[int] = Field(None, description="Cantidad de caracteres")
    estimated_read_time_seconds: Optional[int] = Field(None, description="Tiempo estimado de lectura")


class SenderInfo(BaseModel):
    """Información del remitente"""
    type: str = Field(..., description="Tipo: bot, operator, system")
    name: str = Field(..., description="Nombre del remitente")
    model_used: Optional[str] = Field(None, description="Modelo de IA usado")
    confidence_score: Optional[float] = Field(None, description="Score de confianza")
    processing_time_ms: Optional[int] = Field(None, description="Tiempo de procesamiento")
    is_automated: bool = Field(default=True, description="Si es automatizado")


class AIAnalysisInfo(BaseModel):
    """Información de análisis de IA"""
    original_message: Optional[str] = Field(None, description="Mensaje original")
    detected_intent: Optional[str] = Field(None, description="Intent detectado")
    intent_confidence: Optional[float] = Field(None, description="Confianza del intent")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict, description="Entidades extraídas")
    response_strategy: Optional[str] = Field(None, description="Estrategia de respuesta")
    suggested_action: Optional[str] = Field(None, description="Acción sugerida")
    new_recommended_status: Optional[str] = Field(None, description="Nuevo estado recomendado")


class WhatsAppDeliveryInfo(BaseModel):
    """Información de entrega de WhatsApp"""
    message_sent: bool = Field(default=False, description="Mensaje enviado")
    delivery_timestamp: Optional[str] = Field(None, description="Timestamp de entrega")
    delivery_status: Optional[str] = Field(None, description="Estado de entrega")
    read_timestamp: Optional[str] = Field(None, description="Timestamp de lectura")
    read_status: Optional[str] = Field(None, description="Estado de lectura")


class CommunicationContextInfo(BaseModel):
    """Contexto de la comunicación"""
    message_sequence_number: Optional[int] = Field(None, description="Número de secuencia del mensaje")
    total_messages_in_conversation: Optional[int] = Field(None, description="Total de mensajes")
    time_since_last_message_minutes: Optional[int] = Field(None, description="Minutos desde último mensaje")
    current_geofence: Optional[str] = Field(None, description="Geocerca actual")
    trip_phase: Optional[str] = Field(None, description="Fase del viaje")


class CommunicationResponseWebhook(WebhookBase):
    """Webhook para respuestas de comunicación (bot/operador)"""
    event: str = Field(default="communication_response", description="Tipo de evento")
    communication: Dict[str, Any] = Field(..., description="Información de la comunicación")
    trip: Dict[str, Any] = Field(..., description="Información del viaje")
    sender: Dict[str, Any] = Field(..., description="Información del remitente")
    recipient: Dict[str, Any] = Field(..., description="Información del destinatario")
    ai_analysis: Dict[str, Any] = Field(default_factory=dict, description="Análisis de IA")
    whatsapp_delivery: Dict[str, Any] = Field(default_factory=dict, description="Estado de entrega WhatsApp")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexto de la comunicación")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")


# Tipo unión para todos los webhooks
WebhookPayload = (
    StatusUpdateWebhook 
    | SpeedViolationWebhook 
    | GeofenceTransitionWebhook 
    | RouteDeviationWebhook 
    | CommunicationResponseWebhook
)

