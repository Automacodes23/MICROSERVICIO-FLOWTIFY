"""
Servicio para procesamiento de eventos de Wialon
"""
from typing import Dict, Any, Optional
import uuid
import time
from datetime import datetime
from app.core.logging import get_logger, log_context
from app.core.errors import BusinessLogicError
from app.core.database import Database
from app.core.constants import WIALON_EVENT_TYPES
from app.repositories.event_repository import EventRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.unit_repository import UnitRepository
from app.models.event import WialonEvent
from app.integrations.evolution.client import EvolutionClient
from app.config import settings

logger = get_logger(__name__)


class EventService:
    """Servicio para procesar eventos de Wialon"""

    def __init__(
        self,
        db: Database,
        evolution_client: Optional[EvolutionClient] = None,
        webhook_service=None,  # Inyección opcional de WebhookService
    ):
        self.db = db
        self.event_repo = EventRepository(db)
        self.trip_repo = TripRepository(db)
        self.unit_repo = UnitRepository(db)
        self.evolution_client = evolution_client
        self.webhook_service = webhook_service
        
        # Tracking de notificaciones de desviación de ruta para período de gracia
        self._route_deviation_notifications = {}  # {trip_id: {"last_notification_time": timestamp}}
        
        # DEBUG - Forzar print a consola
        import sys
        sys.stdout.write("=" * 80 + "\n")
        sys.stdout.write("EventService INITIALIZED\n")
        sys.stdout.write(f"  webhook_service: {webhook_service}\n")
        sys.stdout.write(f"  webhook_service is None: {webhook_service is None}\n")
        sys.stdout.write("=" * 80 + "\n")
        sys.stdout.flush()
        
        logger.info(
            "event_service_initialized",
            has_webhook_service=webhook_service is not None,
            has_evolution_client=evolution_client is not None,
        )

    def _check_grace_period(self, trip_id: str, grace_period_seconds: int = 300) -> bool:
        """
        Verificar si han pasado suficientes segundos desde la última notificación de desviación
        
        Args:
            trip_id: ID del viaje
            grace_period_seconds: Período de gracia en segundos (default: 5 minutos)
        
        Returns:
            True si se puede enviar notificación, False si está en período de gracia
        """
        # Limpiar entradas antiguas (cada hora)
        self._cleanup_old_notifications(max_age_seconds=3600)
        
        current_time = time.time()
        
        if trip_id not in self._route_deviation_notifications:
            # Primera notificación para este viaje
            self._route_deviation_notifications[trip_id] = {
                "last_notification_time": current_time
            }
            logger.info(
                "route_deviation_notification_allowed",
                trip_id=trip_id,
                reason="first_notification"
            )
            return True
        
        last_notification_time = self._route_deviation_notifications[trip_id]["last_notification_time"]
        time_since_last = current_time - last_notification_time
        
        if time_since_last >= grace_period_seconds:
            # Período de gracia expirado, actualizar timestamp
            self._route_deviation_notifications[trip_id]["last_notification_time"] = current_time
            logger.info(
                "route_deviation_notification_allowed",
                trip_id=trip_id,
                reason="grace_period_expired",
                time_since_last=time_since_last
            )
            return True
        else:
            # Período de gracia activo
            logger.info(
                "route_deviation_notification_blocked",
                trip_id=trip_id,
                reason="grace_period_active",
                time_since_last=time_since_last,
                grace_period_seconds=grace_period_seconds
            )
            return False

    def _cleanup_old_notifications(self, max_age_seconds: int = 3600):
        """
        Limpiar entradas antiguas del tracking de notificaciones
        
        Args:
            max_age_seconds: Edad máxima en segundos (default: 1 hora)
        """
        current_time = time.time()
        trips_to_remove = []
        
        for trip_id, data in self._route_deviation_notifications.items():
            age = current_time - data["last_notification_time"]
            if age > max_age_seconds:
                trips_to_remove.append(trip_id)
        
        for trip_id in trips_to_remove:
            del self._route_deviation_notifications[trip_id]
        
        if trips_to_remove:
            logger.info(
                "route_deviation_notifications_cleaned",
                count=len(trips_to_remove)
            )

    async def process_wialon_event(
        self, event: WialonEvent
    ) -> Dict[str, Any]:
        """
        Procesar evento de Wialon

        Args:
            event: Evento de Wialon

        Returns:
            Resultado del procesamiento
        """
        trace_id = str(uuid.uuid4())
        log_context(
            trace_id=trace_id,
            event_type=event.notification_type,
            unit_id=event.unit_id,
        )

        try:
            logger.info("wialon_event_received", event_data=event.model_dump())

            # 1. Buscar viaje activo por wialon_id de la unidad
            trip = await self.trip_repo.find_active_by_wialon_id(event.unit_id)

            if not trip:
                logger.warning(
                    "no_active_trip_for_event",
                    unit_id=event.unit_id,
                    unit_name=event.unit_name,
                )
                return {
                    "success": True,
                    "message": "No active trip found for unit",
                    "event_saved": False,
                }

            # 2. Obtener unit_id de la base de datos
            unit = await self.unit_repo.find_by_wialon_id(event.unit_id)
            if not unit:
                logger.error("unit_not_found", wialon_id=event.unit_id)
                raise BusinessLogicError(f"Unit not found: {event.unit_id}")

            # 3. Buscar geofence_id en BD si viene del evento (para foreign key)
            geofence_db_id = None
            if event.geofence_id:
                # Buscar la geocerca por floatify_geofence_id (usando fetchval para obtener valor directo)
                geofence_db_id = await self.db.fetchval(
                    "SELECT id FROM geofences WHERE floatify_geofence_id = %s OR wialon_geofence_id = %s",
                    event.geofence_id,
                    event.geofence_id
                )
                if geofence_db_id:
                    logger.info("geofence_found_for_event", floatify_id=event.geofence_id, db_id=geofence_db_id)
                else:
                    logger.warning("geofence_not_found_for_event", floatify_id=event.geofence_id)
            
            # 4. Registrar evento (con idempotencia usando wialon_notification_id)
            event_data = {
                "wialon_notification_id": event.notification_id,
                "trip_id": trip["id"],
                "unit_id": unit["id"],
                "event_type": event.notification_type,
                "event_time": event.event_time,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "geofence_id": geofence_db_id,  # Usar ID de BD o None
                "raw_payload": event.model_dump(),
            }

            created_event = await self.event_repo.create_event(event_data)

            if not created_event:
                # Evento duplicado (idempotencia) - recuperar el evento existente para devolver sus IDs
                logger.info(
                    "event_already_processed_idempotency",
                    wialon_notification_id=event.notification_id,
                    event_type=event.notification_type
                )
                existing_event = await self.event_repo.find_by_wialon_notification_id(event.notification_id)
                
                return {
                    "success": True,
                    "message": "Event already processed (idempotent)",
                    "event_saved": False,
                    "idempotent": True,
                    "event_id": existing_event["id"] if existing_event else None,
                    "trip_id": existing_event.get("trip_id") if existing_event else trip["id"],
                }

            logger.info("event_saved", event_id=created_event["id"])

            # 5. Determinar acción según tipo de evento
            action_result = await self._determine_action(event, trip)
            logger.info("action_determined", action=action_result, event_type=event.notification_type)

            # 6. Actualizar estado del viaje si es necesario
            if action_result.get("update_status"):
                await self.trip_repo.update_status(
                    trip["id"],
                    action_result["new_status"],
                    action_result["new_substatus"],
                )
                logger.info(
                    "trip_status_updated_by_event",
                    trip_id=trip["id"],
                    new_status=action_result["new_status"],
                    new_substatus=action_result["new_substatus"],
                )

            # 7. Enviar notificación WhatsApp si es necesario
            logger.info(
                "whatsapp_notification_check",
                send_notification=action_result.get('send_notification'),
                has_evolution_client=self.evolution_client is not None,
                has_message=bool(action_result.get('notification_message')),
            )
            
            if action_result.get("send_notification") and self.evolution_client:
                whatsapp_group_id = trip.get("whatsapp_group_id")
                notification_message = action_result.get("notification_message")
                
                logger.info(
                    "sending_whatsapp_notification",
                    group_id=whatsapp_group_id,
                    message_preview=notification_message[:50] if notification_message else None,
                )
                
                if whatsapp_group_id and notification_message:
                    try:
                        logger.info(
                            "sending_event_notification",
                            trip_id=trip["id"],
                            group_id=whatsapp_group_id,
                            event_type=event.notification_type
                        )
                        await self.evolution_client.send_text(
                            whatsapp_group_id,
                            notification_message
                        )
                        logger.info(
                            "event_notification_sent",
                            trip_id=trip["id"],
                            group_id=whatsapp_group_id,
                            event_type=event.notification_type
                        )
                    except Exception as e:
                        logger.error(
                            "event_notification_failed",
                            error=str(e),
                            trip_id=trip["id"],
                            group_id=whatsapp_group_id
                        )
                        # No fallar el proceso si solo falla el WhatsApp
                else:
                    logger.warning(
                        "event_notification_skipped_no_group",
                        trip_id=trip["id"],
                        has_group_id=bool(whatsapp_group_id),
                        has_message=bool(notification_message)
                    )

            # 8. Enviar webhooks a Flowtify según tipo de evento
            logger.info(
                "event_webhook_check",
                has_webhook_service=self.webhook_service is not None,
                event_type=event.notification_type,
                event_id=created_event.get("id"),
            )
            
            if self.webhook_service:
                try:
                    logger.info(
                        "sending_event_webhook",
                        event_type=event.notification_type,
                        event_id=created_event.get("id"),
                        trip_id=trip.get("id"),
                    )
                    
                    await self._send_webhooks_for_event(
                        event=event,
                        created_event=created_event,
                        trip=trip,
                        action_result=action_result,
                    )
                    
                    logger.info(
                        "event_webhook_sent_successfully",
                        event_type=event.notification_type,
                        event_id=created_event.get("id"),
                    )
                except Exception as e:
                    # Log pero no fallar el procesamiento
                    logger.error(
                        "webhook_send_failed_for_event",
                        error=str(e),
                        event_id=created_event["id"],
                        event_type=event.notification_type,
                    )
                    import traceback
                    logger.error("webhook_error_traceback", traceback=traceback.format_exc())
            else:
                logger.warning(
                    "webhook_service_is_none_skipping_event_webhook",
                    event_type=event.notification_type,
                    event_id=created_event.get("id"),
                )
            
            # 9. Si es desviación de ruta, crear evento adicional de tipo route_deviation
            route_deviation_event = None
            if action_result.get("create_route_deviation_event") and event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:
                try:
                    # Crear evento adicional de tipo route_deviation
                    route_deviation_notification_id = f"{event.notification_id}_route_deviation" if event.notification_id else f"route_deviation_{event.event_time}_{event.unit_id}_{uuid.uuid4().hex[:8]}"
                    
                    route_deviation_event_data = {
                        "wialon_notification_id": route_deviation_notification_id,
                        "trip_id": trip["id"],
                        "unit_id": unit["id"],
                        "event_type": WIALON_EVENT_TYPES["ROUTE_DEVIATION"],  # Tipo route_deviation
                        "event_time": event.event_time,
                        "latitude": event.latitude,
                        "longitude": event.longitude,
                        "geofence_id": geofence_db_id,  # Misma geocerca
                        "raw_payload": {
                            **event.model_dump(),
                            "detected_from": "geofence_exit",
                            "geofence_role": "route",
                            "route_deviation_source_event_id": created_event["id"],
                        },
                    }
                    
                    route_deviation_event = await self.event_repo.create_event(route_deviation_event_data)
                    
                    if route_deviation_event:
                        logger.info(
                            "route_deviation_event_created",
                            event_id=route_deviation_event["id"],
                            source_event_id=created_event["id"],
                            trip_id=trip["id"]
                        )
                        
                        # Marcar el evento route_deviation como procesado también (ya se procesó con el geofence_exit)
                        await self.event_repo.mark_as_processed(route_deviation_event["id"])
                    else:
                        logger.warning(
                            "route_deviation_event_not_created_duplicate",
                            notification_id=route_deviation_notification_id,
                            trip_id=trip["id"]
                        )
                except Exception as e:
                    # No fallar el procesamiento si falla la creación del evento adicional
                    logger.error(
                        "route_deviation_event_creation_failed",
                        error=str(e),
                        trip_id=trip["id"],
                        source_event_id=created_event["id"]
                    )
            
            # 10. Marcar evento como procesado
            await self.event_repo.mark_as_processed(created_event["id"])

            return {
                "success": True,
                "event_id": created_event["id"],
                "trip_id": trip["id"],
                "action": action_result,
                "message": "Event processed successfully",
                "route_deviation_event_id": route_deviation_event["id"] if route_deviation_event else None,
            }

        except Exception as e:
            logger.error("event_processing_failed", error=str(e))
            raise BusinessLogicError(f"Error procesando evento: {str(e)}")

    async def _determine_action(
        self, event: WialonEvent, trip: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determinar acción a tomar según el tipo de evento

        Args:
            event: Evento de Wialon
            trip: Viaje actual

        Returns:
            Diccionario con la acción a realizar
        """
        current_status = trip["status"]
        current_substatus = trip["substatus"]

        action = {
            "update_status": False,
            "send_notification": False,
            "notification_message": None,
            "new_status": current_status,
            "new_substatus": current_substatus,
        }

        # Entrada a geocerca
        if event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_ENTRY"]:
            # Primero intentar determinar el rol desde la BD (más confiable)
            geofence_role = None
            if event.geofence_id:
                try:
                    geofence_role = await self.db.fetchval(
                        """
                        SELECT tg.visit_type 
                        FROM trip_geofences tg
                        JOIN geofences g ON g.id = tg.geofence_id
                        WHERE tg.trip_id = %s 
                          AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
                        LIMIT 1
                        """,
                        trip["id"],
                        event.geofence_id,
                        event.geofence_id
                    )
                    logger.info(
                        "geofence_role_detected",
                        geofence_id=event.geofence_id,
                        geofence_name=event.geofence_name,
                        role=geofence_role,
                        trip_id=trip["id"]
                    )
                except Exception as e:
                    logger.warning("geofence_role_lookup_failed", error=str(e), geofence_id=event.geofence_id)
            
            # Si encontramos el rol en BD, usarlo
            if geofence_role == "loading":
                action["update_status"] = True
                action["new_status"] = "en_zona_carga"
                action["new_substatus"] = "esperando_inicio_carga"
                action["send_notification"] = True
                action["notification_message"] = (
                    f"[CARGA] Llegaste a {event.geofence_name}. "
                    "Ya iniciaste la carga?"
                )
            
            elif geofence_role == "unloading":
                action["update_status"] = True
                action["new_status"] = "en_zona_descarga"
                action["new_substatus"] = "esperando_inicio_descarga"
                action["send_notification"] = True
                action["notification_message"] = (
                    f"[DESCARGA] Llegaste a {event.geofence_name}. "
                    "Confirma cuando inicies la descarga."
                )
            
            # Fallback: si no hay rol en BD, usar detección por nombre (compatibilidad con geocercas no asociadas)
            elif not geofence_role:
                geofence_name_lower = (event.geofence_name or "").lower()
                
                if "carga" in geofence_name_lower or "loading" in geofence_name_lower:
                    action["update_status"] = True
                    action["new_status"] = "en_zona_carga"
                    action["new_substatus"] = "esperando_inicio_carga"
                    action["send_notification"] = True
                    action["notification_message"] = (
                        f"[CARGA] Llegaste a {event.geofence_name}. "
                        "Ya iniciaste la carga?"
                    )
                    logger.info("geofence_detected_by_name_fallback", type="loading", geofence_name=event.geofence_name)
                
                elif "descarga" in geofence_name_lower or "unload" in geofence_name_lower:
                    action["update_status"] = True
                    action["new_status"] = "en_zona_descarga"
                    action["new_substatus"] = "esperando_inicio_descarga"
                    action["send_notification"] = True
                    action["notification_message"] = (
                        f"[DESCARGA] Llegaste a {event.geofence_name}. "
                        "Confirma cuando inicies la descarga."
                    )
                    logger.info("geofence_detected_by_name_fallback", type="unloading", geofence_name=event.geofence_name)

        # Salida de geocerca
        elif event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:
            # Primero intentar determinar el rol desde la BD (más confiable)
            geofence_role = None
            if event.geofence_id:
                try:
                    geofence_role = await self.db.fetchval(
                        """
                        SELECT tg.visit_type 
                        FROM trip_geofences tg
                        JOIN geofences g ON g.id = tg.geofence_id
                        WHERE tg.trip_id = %s 
                          AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
                        LIMIT 1
                        """,
                        trip["id"],
                        event.geofence_id,
                        event.geofence_id
                    )
                    logger.info(
                        "geofence_role_detected",
                        geofence_id=event.geofence_id,
                        geofence_name=event.geofence_name,
                        role=geofence_role,
                        trip_id=trip["id"]
                    )
                except Exception as e:
                    logger.warning("geofence_role_lookup_failed", error=str(e), geofence_id=event.geofence_id)
            
            # Si encontramos el rol en BD, usarlo
            if geofence_role == "loading":
                action["update_status"] = True
                action["new_status"] = "en_ruta_destino"
                action["new_substatus"] = "rumbo_a_descarga"
            
            # NUEVO: Detección de desviación de ruta
            elif geofence_role == "route":
                # Marcar que debemos crear un evento adicional de tipo route_deviation
                action["create_route_deviation_event"] = True
                
                # Verificar período de gracia antes de enviar notificación
                grace_period = getattr(settings, 'route_deviation_grace_period', 300)
                
                if self._check_grace_period(trip["id"], grace_period):
                    action["send_notification"] = True
                    action["notification_message"] = (
                        f"⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. "
                        f"Ubicación actual: {event.address or 'No disponible'}"
                    )
                    logger.info(
                        "route_deviation_detected",
                        trip_id=trip["id"],
                        geofence_name=event.geofence_name,
                        geofence_id=event.geofence_id
                    )
                else:
                    # Período de gracia activo, no enviar notificación pero sí webhook
                    action["send_notification"] = False
                    logger.info(
                        "route_deviation_notification_blocked_by_grace_period",
                        trip_id=trip["id"],
                        geofence_name=event.geofence_name
                    )
                # NO cambiar el estado del viaje (solo notificaciones y webhooks)
            
            # Fallback: si no hay rol en BD, usar detección por nombre (compatibilidad)
            elif not geofence_role:
                geofence_name_lower = (event.geofence_name or "").lower()
                
                if "carga" in geofence_name_lower or "loading" in geofence_name_lower:
                    action["update_status"] = True
                    action["new_status"] = "en_ruta_destino"
                    action["new_substatus"] = "rumbo_a_descarga"
                
                # NUEVO: Detección por nombre para geocercas de ruta
                elif "ruta" in geofence_name_lower or "route" in geofence_name_lower:
                    # Marcar que debemos crear un evento adicional de tipo route_deviation
                    action["create_route_deviation_event"] = True
                    
                    # Verificar período de gracia antes de enviar notificación
                    grace_period = getattr(settings, 'route_deviation_grace_period', 300)
                    
                    if self._check_grace_period(trip["id"], grace_period):
                        action["send_notification"] = True
                        action["notification_message"] = (
                            f"⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. "
                            f"Ubicación actual: {event.address or 'No disponible'}"
                        )
                        logger.info(
                            "route_deviation_detected_by_name_fallback",
                            trip_id=trip["id"],
                            geofence_name=event.geofence_name
                        )
                    else:
                        # Período de gracia activo, no enviar notificación pero sí webhook
                        action["send_notification"] = False
                        logger.info(
                            "route_deviation_notification_blocked_by_grace_period",
                            trip_id=trip["id"],
                            geofence_name=event.geofence_name
                        )

        # Exceso de velocidad
        elif event.notification_type == WIALON_EVENT_TYPES["SPEED_VIOLATION"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"ALERTA: Exceso de velocidad detectado: {event.speed}km/h "
                f"(limite: {event.max_speed}km/h). Por favor reduce la velocidad."
            )

        # Botón de pánico
        elif event.notification_type == WIALON_EVENT_TYPES["PANIC_BUTTON"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"ALERTA: Boton de panico activado en {event.unit_name}. "
                f"Ubicacion: {event.address}"
            )

        # Pérdida de conexión
        elif event.notification_type == WIALON_EVENT_TYPES["CONNECTION_LOST"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"ALERTA: Perdida de conexion en {event.unit_name}. "
                f"Ultima ubicacion: {event.address}"
            )

        # Desviación de ruta
        elif event.notification_type == WIALON_EVENT_TYPES["ROUTE_DEVIATION"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"ALERTA: Desviacion de ruta detectada: {event.deviation_distance_km}km "
                f"de distancia de la ruta planificada."
            )

        return action
    
    async def _send_webhooks_for_event(
        self,
        event: WialonEvent,
        created_event: Dict[str, Any],
        trip: Dict[str, Any],
        action_result: Dict[str, Any],
    ):
        """
        Enviar webhooks a Flowtify según tipo de evento
        
        Args:
            event: Evento original de Wialon
            created_event: Evento guardado en BD
            trip: Viaje asociado
            action_result: Resultado de la acción determinada
        """
        event_id = created_event["id"]
        trip_id = trip["id"]
        
        # Speed Violation
        if event.notification_type == WIALON_EVENT_TYPES["SPEED_VIOLATION"]:
            violation_data = {
                "speed": event.speed or 0,
                "max_speed": event.max_speed or 80,
                "duration_seconds": 0,  # TODO: Calcular duración
                "distance_km": 0,  # TODO: Calcular distancia
                "notification_id": event.notification_id,
                "external_id": f"wialon_speed_{event.unit_id}_{event.event_time}",
                "location": {
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "address": event.address,
                },
            }
            
            await self.webhook_service.send_speed_violation(
                event_id=event_id,
                trip_id=trip_id,
                violation_data=violation_data,
            )
            logger.info(
                "speed_violation_webhook_sent",
                event_id=event_id,
                trip_id=trip_id,
            )
        
        # Geofence Entry/Exit
        elif event.notification_type in [
            WIALON_EVENT_TYPES["GEOFENCE_ENTRY"],
            WIALON_EVENT_TYPES["GEOFENCE_EXIT"],
        ]:
            transition_type = (
                "entry"
                if event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_ENTRY"]
                else "exit"
            )
            
            # Obtener role y tipo de la geocerca desde BD (MySQL)
            geofence_role = "unknown"
            geofence_type = "polygon"  # Default
            if event.geofence_id:
                geofence_info = await self.db.fetchrow(
                    """
                    SELECT tg.visit_type, g.geofence_type
                    FROM trip_geofences tg
                    JOIN geofences g ON g.id = tg.geofence_id
                    WHERE tg.trip_id = %s 
                      AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
                    LIMIT 1
                    """,
                    trip_id,
                    event.geofence_id,
                    event.geofence_id,
                )
                if geofence_info:
                    geofence_role = geofence_info.get("visit_type") or "unknown"
                    geofence_type = geofence_info.get("geofence_type") or "polygon"
            
            # Fallback: detección por nombre
            if geofence_role == "unknown":
                geofence_name_lower = (event.geofence_name or "").lower()
                if "ruta" in geofence_name_lower or "route" in geofence_name_lower:
                    geofence_role = "route"
            
            # NUEVO: Lógica especial para geocercas de ruta
            if geofence_role == "route":
                # Para geocercas de ruta, NO enviar geofence_transition
                # Solo enviar route_deviation (salida) o route_return (entrada)
                
                if transition_type == "exit":
                    # Salida de geocerca de ruta = Desviación
                    try:
                        deviation_data = {
                            "distance_meters": 0,  # No se calcula distancia
                            "max_allowed": 100,  # Valor por defecto
                            "duration_seconds": 0,  # No se calcula duración
                            "notification_id": event.notification_id,
                            "external_id": f"wialon_route_dev_{event.unit_id}_{event.event_time}",
                            "current_location": {
                                "latitude": event.latitude,
                                "longitude": event.longitude,
                                "address": event.address,
                            },
                            "nearest_point": {},  # Vacío porque no se calcula
                        }
                        
                        await self.webhook_service.send_route_deviation(
                            event_id=event_id,
                            trip_id=trip_id,
                            deviation_data=deviation_data,
                        )
                        logger.info(
                            "route_deviation_webhook_sent",
                            event_id=event_id,
                            trip_id=trip_id,
                            geofence_name=event.geofence_name,
                        )
                    except Exception as e:
                        logger.error(
                            "route_deviation_webhook_failed",
                            event_id=event_id,
                            trip_id=trip_id,
                            error=str(e)
                        )
                
                elif transition_type == "entry":
                    # Entrada a geocerca de ruta = Regreso a ruta
                    # Verificar si hubo una desviación previa
                    try:
                        # Buscar el último evento route_deviation del viaje (desviación previa)
                        previous_deviation = await self.db.fetchrow(
                            """
                            SELECT id, event_time, created_at
                            FROM events
                            WHERE trip_id = %s
                              AND event_type = %s
                              AND processed = TRUE
                            ORDER BY created_at DESC
                            LIMIT 1
                            """,
                            trip_id,
                            WIALON_EVENT_TYPES["ROUTE_DEVIATION"],
                        )
                        
                        if previous_deviation:
                            # Calcular duración de la desviación (tiempo desde la desviación hasta ahora)
                            # Obtener timestamp de la desviación previa
                            deviation_event_time = previous_deviation.get("event_time")
                            deviation_created_at = previous_deviation.get("created_at")
                            
                            # Preferir event_time (timestamp Unix) si existe
                            if deviation_event_time:
                                if isinstance(deviation_event_time, (int, float)):
                                    deviation_timestamp = float(deviation_event_time)
                                else:
                                    # Si es string, intentar convertir
                                    try:
                                        deviation_timestamp = float(deviation_event_time)
                                    except:
                                        deviation_timestamp = time.time()
                            elif deviation_created_at:
                                # Si no hay event_time, usar created_at
                                if isinstance(deviation_created_at, (int, float)):
                                    deviation_timestamp = float(deviation_created_at)
                                elif isinstance(deviation_created_at, str):
                                    try:
                                        # Intentar parsear datetime string
                                        dt = datetime.fromisoformat(deviation_created_at.replace('Z', '+00:00'))
                                        deviation_timestamp = dt.timestamp()
                                    except:
                                        deviation_timestamp = time.time()
                                else:
                                    deviation_timestamp = time.time()
                            else:
                                deviation_timestamp = time.time()
                            
                            # Obtener timestamp actual del evento
                            # event.event_time es un timestamp Unix (int o float)
                            current_timestamp = float(event.event_time) if event.event_time else time.time()
                            
                            # Calcular duración en segundos (diferencia entre timestamps)
                            deviation_duration = max(0, int(current_timestamp - deviation_timestamp))
                            
                            return_data = {
                                "distance_meters": 0,  # Ya está en ruta
                                "max_allowed": 100,  # Valor por defecto
                                "deviation_duration_seconds": deviation_duration,  # Duración de la desviación previa
                                "notification_id": event.notification_id,
                                "external_id": f"wialon_route_return_{event.unit_id}_{event.event_time}",
                                "previous_deviation_id": previous_deviation["id"],  # ID de la desviación previa
                                "current_location": {
                                    "latitude": event.latitude,
                                    "longitude": event.longitude,
                                    "address": event.address,
                                },
                                "nearest_point": {},  # Vacío porque ya está en ruta
                            }
                            
                            await self.webhook_service.send_route_return(
                                event_id=event_id,
                                trip_id=trip_id,
                                return_data=return_data,
                            )
                            logger.info(
                                "route_return_webhook_sent",
                                event_id=event_id,
                                trip_id=trip_id,
                                geofence_name=event.geofence_name,
                                previous_deviation_id=previous_deviation["id"],
                                deviation_duration=deviation_duration,
                            )
                        else:
                            # No hay desviación previa, es solo entrada normal (primera vez en ruta)
                            # No enviar webhook de regreso, solo loggear
                            logger.info(
                                "route_entry_no_previous_deviation",
                                event_id=event_id,
                                trip_id=trip_id,
                                geofence_name=event.geofence_name,
                            )
                    except Exception as e:
                        logger.error(
                            "route_return_webhook_failed",
                            event_id=event_id,
                            trip_id=trip_id,
                            error=str(e)
                        )
            else:
                # Para otras geocercas (loading, unloading, etc.), enviar geofence_transition normalmente
                geofence_data = {
                    "geofence_id": event.geofence_id,
                    "geofence_name": event.geofence_name,
                    "geofence_type": geofence_type,  # Obtenido desde BD
                    "role": geofence_role,
                    "notification_id": event.notification_id,
                    "external_id": f"wialon_geo_{event.unit_id}_{event.event_time}",
                    "location": {
                        "latitude": event.latitude,
                        "longitude": event.longitude,
                        "address": event.address,
                        "speed": event.speed,
                    },
                }
                
                await self.webhook_service.send_geofence_transition(
                    event_id=event_id,
                    trip_id=trip_id,
                    transition_type=transition_type,
                    geofence_data=geofence_data,
                )
                logger.info(
                    "geofence_transition_webhook_sent",
                    event_id=event_id,
                    trip_id=trip_id,
                    transition_type=transition_type,
                    geofence_role=geofence_role,
                )
        
        # Route Deviation
        elif event.notification_type == WIALON_EVENT_TYPES["ROUTE_DEVIATION"]:
            deviation_data = {
                "distance_meters": event.deviation_distance_km * 1000 if event.deviation_distance_km else 0,
                "max_allowed": 100,  # TODO: Hacer configurable
                "duration_seconds": 0,  # TODO: Calcular
                "notification_id": event.notification_id,
                "external_id": f"wialon_route_dev_{event.unit_id}_{event.event_time}",
                "current_location": {
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "address": event.address,
                },
                "nearest_point": {},  # TODO: Calcular punto más cercano
            }
            
            await self.webhook_service.send_route_deviation(
                event_id=event_id,
                trip_id=trip_id,
                deviation_data=deviation_data,
            )
            logger.info(
                "route_deviation_webhook_sent",
                event_id=event_id,
                trip_id=trip_id,
            )

    async def get_trip_events(
        self, trip_id: str, limit: int = 100, offset: int = 0
    ) -> list:
        """Obtener eventos de un viaje"""
        return await self.event_repo.find_by_trip(trip_id, limit, offset)

