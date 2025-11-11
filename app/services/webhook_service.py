"""
Servicio para envío de webhooks a Flowtify

Este servicio maneja:
- Generación de payloads según especificación
- Firma HMAC de webhooks
- Envío con retry y circuit breaker
- Logging de entregas
- Dead letter queue para fallos
"""
import uuid
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.logging import get_logger
from app.core.database import Database
from app.core.errors import BusinessLogicError
from app.config import settings

logger = get_logger(__name__)


class CircuitBreaker:
    """
    Circuit Breaker simple para prevenir cascading failures
    
    Estados:
    - CLOSED: Normal, permite requests
    - OPEN: Rechaza requests después de threshold de fallos
    - HALF_OPEN: Intenta recuperarse con request de prueba
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func, *args, **kwargs):
        """Ejecutar función con lógica de circuit breaker"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info("circuit_breaker_half_open", message="Attempting reset")
            else:
                raise BusinessLogicError("Circuit breaker is OPEN - blocking requests")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Resetear circuit breaker en éxito"""
        self.failure_count = 0
        self.state = "closed"
        logger.info("circuit_breaker_closed", message="Circuit breaker reset to closed")
    
    def _on_failure(self):
        """Incrementar contador de fallos y abrir circuit si necesario"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )
    
    def _should_attempt_reset(self) -> bool:
        """Verificar si ha pasado suficiente tiempo para intentar reset"""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout


class WebhookService:
    """
    Servicio para envío de webhooks a Flowtify
    
    Responsabilidades:
    - Generar payloads según especificación
    - Firmar con HMAC SHA256
    - Enviar con retry automático
    - Logging de entregas
    - Circuit breaker para prevenir cascading failures
    """
    
    def __init__(
        self,
        db: Database,
        target_url: Optional[str] = None,
        secret_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Inicializar servicio de webhooks
        
        Args:
            db: Conexión a base de datos
            target_url: URL base de webhooks Flowtify
            secret_key: Secret compartido para HMAC
            timeout: Timeout HTTP en segundos
        """
        self.db = db
        self.target_url = target_url or settings.flowtify_webhook_url
        self.secret_key = secret_key or settings.webhook_secret
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        
        # Circuit breaker
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=settings.webhook_circuit_breaker_threshold,
            recovery_timeout=settings.webhook_circuit_breaker_timeout,
            expected_exception=httpx.HTTPError,
        )
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()
    
    def _generate_signature(self, payload: str) -> str:
        """
        Generar firma HMAC SHA256 para el payload
        
        Args:
            payload: Payload JSON como string
            
        Returns:
            Firma hexadecimal
        """
        if not self.secret_key:
            logger.warning("webhook_secret_not_configured")
            return ""
        
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        
        return signature
    
    def _is_enabled_for_tenant(self, tenant_id: int) -> bool:
        """
        Verificar si webhooks están habilitados para un tenant
        
        Args:
            tenant_id: ID del tenant
            
        Returns:
            True si webhooks están habilitados
        """
        return settings.is_webhook_enabled_for_tenant(tenant_id)
    
    async def _log_webhook_attempt(
        self,
        webhook_type: str,
        trip_id: Optional[str],
        payload: Dict[str, Any],
        target_url: str,
    ) -> str:
        """
        Registrar intento de envío de webhook
        
        Args:
            webhook_type: Tipo de webhook
            trip_id: ID del viaje (opcional)
            payload: Payload completo
            target_url: URL destino
            
        Returns:
            ID del registro de delivery log
        """
        delivery_log_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO webhook_delivery_log 
            (id, webhook_type, trip_id, payload, target_url, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        
        await self.db.execute(
            query,
            delivery_log_id,
            webhook_type,
            trip_id,
            json.dumps(payload, default=str),
            target_url,
            "pending",
        )
        
        logger.info(
            "webhook_attempt_logged",
            delivery_log_id=delivery_log_id,
            webhook_type=webhook_type,
            trip_id=trip_id,
        )
        
        return delivery_log_id
    
    async def _log_webhook_success(self, delivery_log_id: str):
        """Marcar webhook como enviado exitosamente"""
        query = """
            UPDATE webhook_delivery_log
            SET status = %s, delivered_at = NOW()
            WHERE id = %s
        """
        await self.db.execute(query, "sent", delivery_log_id)
    
    async def _log_webhook_failure(self, delivery_log_id: str, error: str):
        """Marcar webhook como fallido"""
        query = """
            UPDATE webhook_delivery_log
            SET status = %s, last_error = %s, retry_count = retry_count + 1
            WHERE id = %s
        """
        await self.db.execute(query, "failed", error, delivery_log_id)
    
    async def _move_to_dead_letter_queue(self, delivery_log_id: str):
        """
        Mover webhook a dead letter queue después de max retries
        
        Args:
            delivery_log_id: ID del webhook que falló
        """
        # Obtener webhook original
        webhook = await self.db.fetchrow(
            "SELECT * FROM webhook_delivery_log WHERE id = %s",
            delivery_log_id,
        )
        
        if not webhook:
            logger.error("webhook_not_found_for_dlq", delivery_log_id=delivery_log_id)
            return
        
        # Insertar en DLQ
        dlq_id = str(uuid.uuid4())
        query = """
            INSERT INTO webhook_dead_letter_queue
            (id, original_delivery_log_id, webhook_type, trip_id, payload, 
             target_url, failure_reason, retry_count, last_attempt_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        await self.db.execute(
            query,
            dlq_id,
            delivery_log_id,
            webhook["webhook_type"],
            webhook["trip_id"],
            webhook["payload"],
            webhook["target_url"],
            webhook["last_error"] or "Unknown error",
            webhook["retry_count"],
        )
        
        logger.warning(
            "webhook_moved_to_dlq",
            delivery_log_id=delivery_log_id,
            dlq_id=dlq_id,
            webhook_type=webhook["webhook_type"],
        )
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _send_webhook_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        webhook_type: str,
        trip_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enviar webhook con retry automático
        
        Args:
            endpoint: Endpoint del webhook (ej: /status-update)
            payload: Payload del webhook
            webhook_type: Tipo de webhook
            trip_id: ID del viaje (opcional)
            
        Returns:
            Diccionario con resultado del envío
        """
        if not self.target_url:
            logger.error("webhook_target_url_not_configured", webhook_type=webhook_type)
            return {"success": False, "error": "Target URL not configured"}
        
        url = f"{self.target_url}{endpoint}"
        payload_json = json.dumps(payload, default=str)
        signature = self._generate_signature(payload_json)
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Type": webhook_type,
            "X-Webhook-Timestamp": str(int(datetime.now(timezone.utc).timestamp())),
        }
        
        # Log attempt
        delivery_log_id = await self._log_webhook_attempt(
            webhook_type=webhook_type,
            trip_id=trip_id,
            payload=payload,
            target_url=url,
        )
        
        try:
            # Usar circuit breaker
            response = await self._circuit_breaker.call(
                self.client.post,
                url,
                content=payload_json,
                headers=headers,
            )
            
            response.raise_for_status()
            
            # Log success
            await self._log_webhook_success(delivery_log_id)
            
            logger.info(
                "webhook_sent_successfully",
                webhook_type=webhook_type,
                trip_id=trip_id,
                status_code=response.status_code,
                delivery_log_id=delivery_log_id,
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "delivery_log_id": delivery_log_id,
            }
        
        except Exception as e:
            # Log failure
            await self._log_webhook_failure(delivery_log_id, str(e))
            
            logger.error(
                "webhook_send_failed",
                webhook_type=webhook_type,
                trip_id=trip_id,
                error=str(e),
                delivery_log_id=delivery_log_id,
            )
            
            # Si agotó retries, mover a DLQ
            webhook = await self.db.fetchrow(
                "SELECT retry_count FROM webhook_delivery_log WHERE id = %s",
                delivery_log_id,
            )
            
            if webhook and webhook["retry_count"] >= settings.webhook_retry_max:
                await self._move_to_dead_letter_queue(delivery_log_id)
            
            return {
                "success": False,
                "error": str(e),
                "delivery_log_id": delivery_log_id,
            }
    
    async def _fetch_trip_complete_data(self, trip_id: str) -> Dict[str, Any]:
        """
        Obtener datos completos del viaje con joins
        
        Args:
            trip_id: UUID del viaje
            
        Returns:
            Diccionario con datos completos del viaje
        """
        query = """
            SELECT 
                t.*,
                d.id as driver_id, d.name as driver_name, d.phone as driver_phone,
                d.wialon_driver_code,
                u.id as unit_id, u.floatify_unit_id as unit_code, u.plate as unit_plate,
                u.wialon_id as unit_wialon_id, u.metadata as unit_metadata, u.name as unit_name
            FROM trips t
            LEFT JOIN drivers d ON t.driver_id = d.id
            LEFT JOIN units u ON t.unit_id = u.id
            WHERE t.id = %s
        """
        
        result = await self.db.fetchrow(query, trip_id)
        
        if not result:
            raise ValueError(f"Trip not found: {trip_id}")
        
        # Obtener tenant_id del metadata (no es columna directa)
        import json
        metadata = result.get("metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif metadata is None:
            metadata = {}
        
        tenant_id = metadata.get("tenant_id", 24)  # Default 24 si no está
        
        # Estructurar datos
        return {
            **result,
            "tenant_id": tenant_id,  # Agregar tenant_id extraído
            "driver": {
                "id": result.get("driver_id"),
                "name": result.get("driver_name"),
                "phone": result.get("driver_phone"),
                "wialon_driver_code": result.get("wialon_driver_code"),
            },
            "unit": {
                "id": result.get("unit_id"),
                "code": result.get("unit_code"),  # floatify_unit_id
                "plate": result.get("unit_plate"),
                "wialon_id": result.get("unit_wialon_id"),
                "imei": None,  # No existe en units, se podría obtener de metadata
                "name": result.get("unit_name"),
            },
        }
    
    def _format_driver_data(self, driver: Optional[Dict]) -> Dict[str, Any]:
        """Formatear datos del conductor para webhook"""
        if not driver:
            return {}
        return {
            "id": driver.get("id"),
            "name": driver.get("name"),
            "phone": driver.get("phone"),
            "wialon_driver_code": driver.get("wialon_driver_code"),
        }
    
    def _format_unit_data(self, unit: Optional[Dict]) -> Dict[str, Any]:
        """Formatear datos de la unidad para webhook"""
        if not unit:
            return {}
        return {
            "id": unit.get("id"),
            "code": unit.get("code"),
            "plate": unit.get("plate"),
            "wialon_id": unit.get("wialon_id"),
            "imei": unit.get("imei"),
            "name": unit.get("name"),
        }
    
    def _format_customer_data(self, customer: Optional[Dict]) -> Dict[str, Any]:
        """Formatear datos del cliente para webhook"""
        if not customer:
            return {}
        return {
            "id": customer.get("id"),
            "name": customer.get("name"),
        }
    
    def _format_trip_summary(self, trip_data: Dict) -> Dict[str, Any]:
        """Formatear resumen del viaje para webhooks"""
        return {
            "id": trip_data.get("id"),
            "floatify_trip_id": trip_data.get("floatify_trip_id"),
            "code": trip_data.get("floatify_trip_id"),
            "status": trip_data.get("status"),
            "substatus": trip_data.get("substatus"),
            "origin": trip_data.get("origin"),
            "destination": trip_data.get("destination"),
        }
    
    async def _get_current_location(self, wialon_id: str) -> Dict[str, Any]:
        """
        Obtener ubicación actual desde último evento
        
        Args:
            wialon_id: ID de la unidad en Wialon
            
        Returns:
            Diccionario con datos de ubicación
        """
        query = """
            SELECT latitude, longitude, event_time
            FROM events
            WHERE unit_id = (SELECT id FROM units WHERE wialon_id = %s)
            ORDER BY event_time DESC
            LIMIT 1
        """
        
        location = await self.db.fetchrow(query, wialon_id)
        
        if location:
            return {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "last_update": (
                    location.get("event_time").isoformat()
                    if location.get("event_time")
                    else None
                ),
            }
        
        return {}
    
    # ========================================================================
    # PUBLIC WEBHOOK METHODS
    # ========================================================================
    
    async def send_status_update(
        self,
        trip_id: str,
        old_status: str,
        old_substatus: str,
        new_status: str,
        new_substatus: str,
        change_reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enviar webhook de actualización de estado
        
        Args:
            trip_id: UUID del viaje
            old_status: Estado anterior
            old_substatus: Subestado anterior
            new_status: Nuevo estado
            new_substatus: Nuevo subestado
            change_reason: Razón del cambio
            metadata: Metadatos adicionales
            
        Returns:
            Resultado del envío
        """
        # Obtener datos completos del viaje
        trip_data = await self._fetch_trip_complete_data(trip_id)
        
        # Verificar si webhooks están habilitados para este tenant
        if not self._is_enabled_for_tenant(trip_data.get("tenant_id", 0)):
            logger.info(
                "webhook_disabled_for_tenant",
                tenant_id=trip_data.get("tenant_id"),
                webhook_type="status_update",
            )
            return {"success": False, "error": "Webhooks disabled for tenant"}
        
        # Construir payload
        payload = {
            "event": "status_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": trip_data.get("tenant_id"),
            "trip": {
                "id": trip_data.get("id"),
                "floatify_trip_id": trip_data.get("floatify_trip_id"),
                "code": trip_data.get("floatify_trip_id"),
                "status": new_status,
                "substatus": new_substatus,
                "status_change_reason": change_reason,
                "previous_status": old_status,
                "previous_substatus": old_substatus,
                "timeline": {
                    "created_at": (
                        trip_data.get("created_at").isoformat()
                        if trip_data.get("created_at")
                        else None
                    ),
                    "started_at": (
                        trip_data.get("actual_start").isoformat()
                        if trip_data.get("actual_start")
                        else None
                    ),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            },
            "driver": self._format_driver_data(trip_data.get("driver")),
            "unit": self._format_unit_data(trip_data.get("unit")),
            "location": await self._get_current_location(
                trip_data["unit"]["wialon_id"]
            )
            if trip_data.get("unit", {}).get("wialon_id")
            else {},
            "customer": {},  # TODO: Agregar customer si existe
            "metadata": metadata or {},
        }
        
        return await self._send_webhook_with_retry(
            endpoint="/status-update",
            payload=payload,
            webhook_type="status_update",
            trip_id=trip_id,
        )
    
    async def send_speed_violation(
        self,
        event_id: str,
        trip_id: str,
        violation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enviar webhook de violación de velocidad
        
        Args:
            event_id: UUID del evento
            trip_id: UUID del viaje
            violation_data: Datos de la violación
            
        Returns:
            Resultado del envío
        """
        trip_data = await self._fetch_trip_complete_data(trip_id)
        
        if not self._is_enabled_for_tenant(trip_data.get("tenant_id", 0)):
            return {"success": False, "error": "Webhooks disabled for tenant"}
        
        # Calcular métricas
        detected_speed = violation_data.get("speed", 0)
        max_speed = violation_data.get("max_speed", 80)
        speed_diff = detected_speed - max_speed
        percentage_over = (speed_diff / max_speed * 100) if max_speed > 0 else 0
        
        # Determinar severidad
        if percentage_over > 40:
            severity = "high"
        elif percentage_over > 20:
            severity = "medium"
        else:
            severity = "low"
        
        payload = {
            "event": "speed_violation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": trip_data.get("tenant_id"),
            "violation": {
                "type": "excessive_speed",
                "severity": severity,
                "detected_speed": detected_speed,
                "max_allowed_speed": max_speed,
                "speed_difference": speed_diff,
                "percentage_over_limit": round(percentage_over, 2),
                "duration_seconds": violation_data.get("duration_seconds", 0),
                "distance_covered_km": violation_data.get("distance_km", 0),
                "violation_id": f"speed_viol_{event_id}",
                "is_ongoing": False,
            },
            "trip": self._format_trip_summary(trip_data),
            "driver": self._format_driver_data(trip_data.get("driver")),
            "unit": self._format_unit_data(trip_data.get("unit")),
            "location": violation_data.get("location", {}),
            "violation_history": {},  # TODO: Implementar historial
            "customer": {},
            "wialon_source": {
                "notification_id": violation_data.get("notification_id"),
                "notification_type": "speed_violation",
                "external_id": violation_data.get("external_id"),
            },
        }
        
        return await self._send_webhook_with_retry(
            endpoint="/speed-violation",
            payload=payload,
            webhook_type="speed_violation",
            trip_id=trip_id,
        )
    
    async def send_geofence_transition(
        self,
        event_id: str,
        trip_id: str,
        transition_type: str,
        geofence_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enviar webhook de transición de geocerca
        
        Args:
            event_id: UUID del evento
            trip_id: UUID del viaje
            transition_type: "entry" o "exit"
            geofence_data: Datos de la geocerca
            
        Returns:
            Resultado del envío
        """
        trip_data = await self._fetch_trip_complete_data(trip_id)
        
        if not self._is_enabled_for_tenant(trip_data.get("tenant_id", 0)):
            return {"success": False, "error": "Webhooks disabled for tenant"}
        
        payload = {
            "event": "geofence_transition",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": trip_data.get("tenant_id"),
            "transition": {
                "type": transition_type,
                "transition_id": f"geo_trans_{event_id}",
                "direction": "entering" if transition_type == "entry" else "exiting",
            },
            "trip": self._format_trip_summary(trip_data),
            "driver": self._format_driver_data(trip_data.get("driver")),
            "unit": self._format_unit_data(trip_data.get("unit")),
            "geofence": {
                "id": geofence_data.get("geofence_id"),
                "name": geofence_data.get("geofence_name"),
                "role": geofence_data.get("role", "unknown"),
                "type": geofence_data.get("geofence_type"),
                "is_critical_zone": geofence_data.get("role") in ["loading", "unloading"],
            },
            "location": geofence_data.get("location", {}),
            "timing": {},  # TODO: Calcular timing metrics
            "customer": {},
            "wialon_source": {
                "notification_id": geofence_data.get("notification_id"),
                "notification_type": f"geofence_{transition_type}",
                "external_id": geofence_data.get("external_id"),
            },
            "workflow_triggers": {
                "auto_status_update": (
                    transition_type == "entry"
                    and geofence_data.get("role") in ["loading", "unloading"]
                ),
                "whatsapp_notification_enabled": True,
                "supervisor_alert": False,
                "requires_driver_action": transition_type == "entry",
            },
        }
        
        return await self._send_webhook_with_retry(
            endpoint="/geofence-transition",
            payload=payload,
            webhook_type="geofence_transition",
            trip_id=trip_id,
        )
    
    async def send_route_deviation(
        self,
        event_id: str,
        trip_id: str,
        deviation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enviar webhook de desviación de ruta
        
        Args:
            event_id: UUID del evento
            trip_id: UUID del viaje
            deviation_data: Datos de la desviación
            
        Returns:
            Resultado del envío
        """
        trip_data = await self._fetch_trip_complete_data(trip_id)
        
        if not self._is_enabled_for_tenant(trip_data.get("tenant_id", 0)):
            return {"success": False, "error": "Webhooks disabled for tenant"}
        
        payload = {
            "event": "route_deviation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": trip_data.get("tenant_id"),
            "deviation": {
                "type": "route_deviation",
                "severity": "critical",
                "deviation_id": f"route_dev_{event_id}",
                "distance_from_route_meters": deviation_data.get("distance_meters"),
                "max_allowed_deviation": deviation_data.get("max_allowed", 100),
                "excess_deviation_meters": max(
                    0,
                    deviation_data.get("distance_meters", 0)
                    - deviation_data.get("max_allowed", 100),
                ),
                "deviation_duration_seconds": deviation_data.get("duration_seconds", 0),
                "current_location": deviation_data.get("current_location", {}),
                "nearest_point_on_route": deviation_data.get("nearest_point", {}),
            },
            "trip": self._format_trip_summary(trip_data),
            "driver": self._format_driver_data(trip_data.get("driver")),
            "unit": self._format_unit_data(trip_data.get("unit")),
            "route_info": {},  # TODO: Calcular route progress
            "immediate_actions": {
                "supervisor_notified": True,
                "driver_contact_attempted": True,
                "whatsapp_alert_sent": True,
                "flowtify_critical_alert": True,
            },
            "wialon_source": {
                "notification_id": deviation_data.get("notification_id"),
                "notification_type": "position_update",
                "external_id": deviation_data.get("external_id"),
            },
        }
        
        return await self._send_webhook_with_retry(
            endpoint="/route-deviation",
            payload=payload,
            webhook_type="route_deviation",
            trip_id=trip_id,
        )
    
    async def send_communication_response(
        self,
        trip_id: str,
        message_id: str,
        response_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enviar webhook de respuesta de comunicación
        
        Args:
            trip_id: UUID del viaje
            message_id: UUID del mensaje
            response_data: Datos de la respuesta
            
        Returns:
            Resultado del envío
        """
        trip_data = await self._fetch_trip_complete_data(trip_id)
        
        if not self._is_enabled_for_tenant(trip_data.get("tenant_id", 0)):
            return {"success": False, "error": "Webhooks disabled for tenant"}
        
        payload = {
            "event": "communication_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": trip_data.get("tenant_id"),
            "communication": {
                "type": response_data.get("sender_type", "bot_response"),
                "direction": "outbound",
                "message_id": message_id,
                "original_message_id": response_data.get("original_message_id"),
                "conversation_id": response_data.get("conversation_id"),
                # ✅ NUEVO: Agregar mensaje original del conductor
                "driver_message": response_data.get("driver_message"),
                "response_content": response_data.get("content"),
                "response_type": response_data.get("response_type"),
                "language": "es",
            },
            "trip": self._format_trip_summary(trip_data),
            "sender": {
                "type": response_data.get("sender_type", "bot"),
                "name": "AI Assistant",
                "model_used": response_data.get("ai_model", "gemini-pro"),
                "confidence_score": response_data.get("confidence", 0),
                "is_automated": response_data.get("sender_type") == "bot",
            },
            "recipient": self._format_driver_data(trip_data.get("driver")),
            "ai_analysis": response_data.get("ai_analysis", {}),
            "whatsapp_delivery": response_data.get("delivery_status", {}),
            "context": response_data.get("context", {}),
            "metadata": response_data.get("metadata", {}),
        }
        
        return await self._send_webhook_with_retry(
            endpoint="/communication-response",
            payload=payload,
            webhook_type="communication_response",
            trip_id=trip_id,
        )

