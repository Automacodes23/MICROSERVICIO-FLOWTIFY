"""
Servicio para procesamiento de eventos de Wialon
"""
from typing import Dict, Any, Optional
import uuid
from app.core.logging import get_logger, log_context
from app.core.errors import BusinessLogicError
from app.core.database import Database
from app.core.constants import WIALON_EVENT_TYPES
from app.repositories.event_repository import EventRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.unit_repository import UnitRepository
from app.models.event import WialonEvent
from app.integrations.evolution.client import EvolutionClient

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
            
            # 9. Marcar evento como procesado
            await self.event_repo.mark_as_processed(created_event["id"])

            return {
                "success": True,
                "event_id": created_event["id"],
                "trip_id": trip["id"],
                "action": action_result,
                "message": "Event processed successfully",
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
            geofence_name_lower = (event.geofence_name or "").lower()

            if "carga" in geofence_name_lower:
                action["update_status"] = True
                action["new_status"] = "en_ruta_destino"
                action["new_substatus"] = "rumbo_a_descarga"

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
            
            # Obtener role de la geocerca
            geofence_role = "unknown"
            if event.geofence_id:
                geofence_role = await self.db.fetchval(
                    """
                    SELECT tg.visit_type 
                    FROM trip_geofences tg
                    JOIN geofences g ON g.id = tg.geofence_id
                    WHERE tg.trip_id = %s 
                      AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
                    LIMIT 1
                    """,
                    trip_id,
                    event.geofence_id,
                    event.geofence_id,
                ) or "unknown"
            
            geofence_data = {
                "geofence_id": event.geofence_id,
                "geofence_name": event.geofence_name,
                "geofence_type": "polygon",  # TODO: Obtener tipo real
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

