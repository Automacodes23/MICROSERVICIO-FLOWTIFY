"""
Servicio para gestión de viajes
"""
from typing import Dict, Any, Optional
import uuid
import json
from app.core.logging import get_logger, log_context
from app.core.errors import TripNotFoundError, BusinessLogicError
from app.core.database import Database
from app.repositories.trip_repository import TripRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.driver_repository import DriverRepository
from app.repositories.message_repository import ConversationRepository
from app.integrations.evolution.client import EvolutionClient
from app.models.trip import TripCreate
from app.utils.helpers import format_whatsapp_jid

logger = get_logger(__name__)


class TripService:
    """Servicio para operaciones de viajes"""

    def __init__(
        self,
        db: Database,
        evolution_client: EvolutionClient,
    ):
        self.db = db
        self.evolution_client = evolution_client
        self.trip_repo = TripRepository(db)
        self.unit_repo = UnitRepository(db)
        self.driver_repo = DriverRepository(db)
        self.conversation_repo = ConversationRepository(db)

    async def create_trip_from_floatify(
        self, payload: TripCreate
    ) -> Dict[str, Any]:
        """
        Crear viaje completo desde Floatify

        Este método orquesta:
        1. Crear/actualizar unidad
        2. Crear/actualizar conductor
        3. Crear viaje
        4. Crear geocercas y asociaciones
        5. Crear grupo de WhatsApp
        6. Guardar conversación
        7. Enviar mensaje de bienvenida

        Args:
            payload: Datos del viaje desde Floatify

        Returns:
            Diccionario con información del viaje creado
        """
        trace_id = str(uuid.uuid4())
        log_context(trace_id=trace_id, trip_code=payload.trip.get("code"))

        try:
            logger.info("trip_creation_started", payload=payload.model_dump())

            # 1. Crear/actualizar unidad
            unit_data = {
                "floatify_unit_id": payload.unit.get("floatify_unit_id") or f"UNIT-{payload.trip.get('code')}",
                "wialon_id": payload.unit.get("wialon_id"),
                "name": payload.unit.get("name"),
                "plate": payload.unit.get("plate"),
                "metadata": payload.unit,
            }
            unit = await self.unit_repo.upsert(unit_data)
            logger.info("unit_upserted", unit_id=unit["id"], name=unit.get("name"))

            # 2. Crear/actualizar conductor
            driver_data = {
                "name": payload.driver.get("name"),
                "phone": payload.driver.get("phone"),
                "wialon_driver_code": str(payload.driver.get("id")) if payload.driver.get("id") else payload.driver.get("wialon_code"),
                "metadata": payload.driver,
            }
            driver = await self.driver_repo.upsert(driver_data)
            if not driver:
                raise BusinessLogicError("Failed to create/update driver")
            logger.info("driver_upserted", driver_id=driver["id"], phone=driver["phone"])

            # 3. Crear viaje
            trip_data = {
                "floatify_trip_id": payload.trip.get("code"),
                "unit_id": unit["id"],
                "driver_id": driver["id"],
                "status": "pending",
                "cargo_description": payload.trip.get("cargo_description"),
                "tenant_id": payload.tenant_id,
                "origin": payload.trip.get("origin"),
                "destination": payload.trip.get("destination"),
                "planned_start": payload.trip.get("planned_start"),
                "planned_end": payload.trip.get("planned_end"),
                "metadata": payload.metadata or {},
            }
            trip = await self.trip_repo.create_full_trip(trip_data)
            logger.info("trip_created", trip_id=trip["id"], floatify_trip_id=trip.get("floatify_trip_id"))

            # 4. Crear geocercas y asociaciones
            if payload.geofences:
                await self._create_trip_geofences(trip["id"], payload.geofences)

            # 5. Obtener o crear grupo de WhatsApp para la UNIDAD
            whatsapp_group_id = None
            group_name = None
            welcome_message_sent = False
            group_was_created = False  # Para tracking
            
            if payload.whatsapp_participants:
                try:
                    # 5.1 Verificar si la unidad YA tiene un grupo asignado
                    existing_group_id = unit.get("whatsapp_group_id")
                    existing_group_name = unit.get("whatsapp_group_name")
                    
                    if not existing_group_id:
                        # CASO A: NO HAY GRUPO - CREAR UNO NUEVO
                        logger.info(
                            "no_existing_group_creating_new",
                            unit_id=unit["id"],
                            unit_name=unit.get("name")
                        )
                        
                        # Nombre descriptivo basado en la unidad (no en el viaje)
                        group_name = f"Unidad {unit.get('name')}"
                        if unit.get('plate'):
                            group_name += f" - {unit.get('plate')}"
                        
                        # Convertir números a formato WhatsApp
                        participants = [
                            format_whatsapp_jid(p, is_group=False)
                            for p in payload.whatsapp_participants
                        ]
                        
                        logger.info(
                            "creating_whatsapp_group_for_unit",
                            group_name=group_name,
                            participants=participants,
                            raw_participants=payload.whatsapp_participants,
                            unit_id=unit["id"]
                        )

                        # Crear el grupo
                        group_result = await self.evolution_client.create_group(
                            subject=group_name, 
                            participants=participants
                        )
                        whatsapp_group_id = group_result.get("id")
                        group_was_created = True
                        
                        logger.info(
                            "whatsapp_group_created_for_unit",
                            group_id=whatsapp_group_id,
                            unit_id=unit["id"]
                        )

                        # Guardar el grupo en la UNIDAD (no solo en el trip)
                        try:
                            await self.unit_repo.update(
                                unit["id"],
                                {
                                    "whatsapp_group_id": whatsapp_group_id,
                                    "whatsapp_group_name": group_name
                                }
                            )
                            logger.info(
                                "unit_updated_with_whatsapp_group",
                                unit_id=unit["id"],
                                group_id=whatsapp_group_id
                            )
                        except Exception as update_error:
                            logger.error(
                                "failed_to_update_unit_with_group",
                                error=str(update_error),
                                unit_id=unit["id"],
                                group_id=whatsapp_group_id
                            )
                            # Continuar aunque falle la actualización de la unidad
                        
                    else:
                        # CASO B: HAY GRUPO - REUTILIZARLO
                        whatsapp_group_id = existing_group_id
                        group_name = existing_group_name or f"Unidad {unit.get('name')}"
                        
                        logger.info(
                            "reusing_existing_unit_group",
                            unit_id=unit["id"],
                            group_id=whatsapp_group_id,
                            group_name=group_name
                        )
                        
                        # Agregar nuevos participantes al grupo existente (si hay)
                        if payload.whatsapp_participants:
                            participants_to_add = [
                                format_whatsapp_jid(p, is_group=False)
                                for p in payload.whatsapp_participants
                            ]
                            
                            try:
                                logger.info(
                                    "adding_participants_to_existing_group",
                                    group_id=whatsapp_group_id,
                                    participants_count=len(participants_to_add),
                                    participants=participants_to_add
                                )
                                
                                # Evolution API manejará la deduplicación automáticamente
                                await self.evolution_client.add_participants(
                                    whatsapp_group_id,
                                    participants_to_add
                                )
                                
                                logger.info(
                                    "participants_added_successfully",
                                    group_id=whatsapp_group_id
                                )
                            except Exception as add_error:
                                logger.warning(
                                    "failed_to_add_participants_continuing",
                                    error=str(add_error),
                                    group_id=whatsapp_group_id
                                )
                                # No fallar el viaje si no se pueden agregar participantes
                    
                    # Actualizar el TRIP con el grupo (nuevo o reutilizado)
                    # Esto mantiene compatibilidad con event_service y notification_service
                    update_query = """
                        UPDATE trips
                        SET whatsapp_group_id = %s, whatsapp_group_name = %s, updated_at = NOW()
                        WHERE id = %s
                    """
                    await self.db.execute(update_query, whatsapp_group_id, group_name, trip["id"])
                    
                    logger.info(
                        "trip_updated_with_whatsapp_group_reference",
                        trip_id=trip["id"],
                        group_id=whatsapp_group_id,
                        group_was_created=group_was_created,
                        group_was_reused=not group_was_created
                    )

                    # 6. Guardar conversación
                    try:
                        conversation_data = {
                            "trip_id": trip["id"],
                            "whatsapp_group_id": whatsapp_group_id,
                            "group_name": group_name,
                            "participants": payload.whatsapp_participants,
                        }
                        conversation = await self.conversation_repo.create_conversation(conversation_data)
                        logger.info("conversation_created", conversation_id=conversation.get("id") if conversation else None)
                    except Exception as conv_error:
                        logger.error("conversation_creation_failed", error=str(conv_error), trip_id=trip["id"])
                        # Continuamos aunque falle la conversación

                    # 7. Enviar mensaje de inicio de viaje
                    try:
                        logger.info("sending_trip_start_message", group_id=whatsapp_group_id)
                        trip_start_message = self._generate_trip_start_message(payload, unit, group_was_created)
                        await self.evolution_client.send_text(
                            whatsapp_group_id, trip_start_message
                        )
                        welcome_message_sent = True
                        logger.info("trip_start_message_sent", group_id=whatsapp_group_id, trip_id=trip["id"])
                    except Exception as msg_error:
                        logger.error(
                            "trip_start_message_send_failed", 
                            error=str(msg_error), 
                            group_id=whatsapp_group_id,
                            trip_id=trip["id"]
                        )
                        # Continuamos aunque falle el mensaje

                except Exception as e:
                    logger.error("whatsapp_group_creation_failed", error=str(e))
                    # No fallamos el viaje si falla el grupo de WhatsApp

            logger.info("trip_creation_completed", trip_id=trip["id"])

            return {
                "success": True,
                "trip_id": trip["id"],
                "trip_code": trip.get("floatify_trip_id"),
                "whatsapp_group_id": whatsapp_group_id,
                "welcome_message_sent": welcome_message_sent,
                "message": "Viaje creado exitosamente",
            }

        except Exception as e:
            logger.error("trip_creation_failed", error=str(e))
            raise BusinessLogicError(f"Error al crear viaje: {str(e)}")

    async def _create_trip_geofences(
        self, trip_id: str, geofences: list
    ) -> None:
        """Crear geocercas y asociarlas al viaje"""
        for idx, gf in enumerate(geofences, 1):
            # Usar la misma conexión para todas las operaciones de esta geocerca
            async with self.db.acquire() as (cursor, conn):
                # Crear o actualizar geocerca
                floatify_geofence_id = f"GEO-{idx}-{trip_id}"
                gf_query = """
                    INSERT INTO geofences (floatify_geofence_id, wialon_geofence_id, name, geofence_type, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        wialon_geofence_id = VALUES(wialon_geofence_id),
                        name = VALUES(name),
                        geofence_type = VALUES(geofence_type),
                        metadata = VALUES(metadata)
                """
                await cursor.execute(
                    gf_query,
                    (floatify_geofence_id, gf.geofence_id, gf.geofence_name, gf.geofence_type or gf.role, json.dumps(gf.model_dump()))
                )
                await conn.commit()
                
                # Obtener el ID de la geocerca en la misma conexión
                gf_id_query = "SELECT id FROM geofences WHERE floatify_geofence_id = %s"
                await cursor.execute(gf_id_query, (floatify_geofence_id,))
                gf_row = await cursor.fetchone()
                gf_id = gf_row['id'] if gf_row else None
                
                if not gf_id:
                    logger.error("geofence_not_found", floatify_geofence_id=floatify_geofence_id)
                    continue

                # Asociar al viaje
                assoc_query = """
                    INSERT INTO trip_geofences (trip_id, geofence_id, sequence_order, visit_type)
                    VALUES (%s, %s, %s, %s)
                """
                await cursor.execute(
                    assoc_query, (trip_id, gf_id, gf.order, gf.role)
                )
                await conn.commit()
                logger.info("geofence_associated", trip_id=trip_id, geofence_id=gf_id, role=gf.role)

    def _generate_trip_start_message(self, payload: TripCreate, unit: Dict[str, Any], is_new_group: bool) -> str:
        """
        Generar mensaje de inicio de viaje para el grupo
        
        Args:
            payload: Datos del viaje desde Floatify
            unit: Datos de la unidad
            is_new_group: True si es un grupo recién creado, False si es reutilizado
        
        Returns:
            Mensaje formateado para WhatsApp
        """
        # Si es un grupo nuevo, agregar contexto de bienvenida
        if is_new_group:
            header = f"🚛 *Grupo de la Unidad {unit.get('name')}*\n\n"
            header += "Este grupo se usará para todos los viajes de esta unidad.\n\n"
            header += "─────────────────────────\n\n"
        else:
            header = ""
        
        # Mensaje del nuevo viaje con contexto claro
        message = f"{header}📋 *NUEVO VIAJE ASIGNADO*\n\n"
        message += f"🆔 Código: *{payload.trip.get('code')}*\n"
        message += f"👤 Operador: {payload.driver.get('name')}\n"
        message += f"🚚 Unidad: {unit.get('name')}"
        
        if unit.get('plate'):
            message += f" ({unit.get('plate')})\n"
        else:
            message += "\n"
        
        message += f"📍 Origen: {payload.trip.get('origin')}\n"
        message += f"📍 Destino: {payload.trip.get('destination')}\n"
        
        if payload.trip.get('planned_start'):
            message += f"🕐 Inicio planificado: {payload.trip.get('planned_start')}\n"
        
        if payload.trip.get('cargo_description'):
            message += f"📦 Carga: {payload.trip.get('cargo_description')}\n"
        
        message += "\n🔔 *Instrucciones:*\n"
        message += "1. Escanea el código QR de la unidad para iniciar el viaje\n"
        message += "2. Mantén este chat activo para recibir notificaciones\n"
        message += "3. Responde a las actualizaciones cuando sea necesario"
        
        return message

    async def get_trip_by_id(self, trip_id: str) -> Dict[str, Any]:
        """Obtener viaje por ID (UUID o int)"""
        trip = await self.trip_repo.find_by_id(trip_id)
        if not trip:
            raise TripNotFoundError(trip_id)
        return trip

    async def get_trip_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Obtener viaje por código"""
        return await self.trip_repo.find_by_code(code)

    async def update_trip_status(
        self, trip_id: str, status: str, substatus: str
    ) -> Dict[str, Any]:
        """Actualizar estado del viaje"""
        trip = await self.trip_repo.update_status(trip_id, status, substatus)
        if not trip:
            raise TripNotFoundError(trip_id)

        logger.info(
            "trip_status_updated",
            trip_id=trip_id,
            status=status,
            substatus=substatus,
        )
        return trip

    async def complete_trip(
        self, trip_id: str, final_substatus: str
    ) -> Dict[str, Any]:
        """Completar un viaje"""
        trip = await self.trip_repo.complete_trip(
            trip_id, status="finalizado", substatus=final_substatus
        )
        if not trip:
            raise TripNotFoundError(trip_id)

        logger.info(
            "trip_completed",
            trip_id=trip_id,
            final_substatus=final_substatus,
        )
        return trip

    async def cleanup_trip_group(self, trip_id: str) -> Dict[str, Any]:
        """
        Hace que el bot abandone el grupo de WhatsApp asociado a un viaje
        y desactiva la conversación.

        IMPORTANTE: Si el grupo está vinculado a una unidad (grupo compartido),
        NO se puede abandonar porque afectaría a otros viajes.

        Este método es útil para pruebas y limpieza de grupos de test.

        Args:
            trip_id: ID del viaje

        Returns:
            Diccionario con resultado de la operación

        Raises:
            BusinessLogicError: Si hay un error en la lógica de negocio
        """
        logger.info("trip_group_cleanup_started", trip_id=trip_id)
        
        # 1. Buscar el viaje
        trip = await self.trip_repo.find_by_id(trip_id)
        if not trip:
            raise BusinessLogicError(f"Trip not found: {trip_id}")
        
        # 2. Buscar la unidad asociada
        unit = await self.unit_repo.find_by_id(trip["unit_id"])
        
        # 3. VERIFICAR SI EL GRUPO ESTÁ EN LA UNIDAD (GRUPO COMPARTIDO)
        if unit and unit.get("whatsapp_group_id") == trip.get("whatsapp_group_id"):
            logger.warning(
                "cleanup_blocked_shared_group",
                trip_id=trip_id,
                unit_id=unit["id"],
                group_id=unit.get("whatsapp_group_id"),
                reason="Group is shared across multiple trips for this unit"
            )
            return {
                "success": False,
                "message": (
                    "No se puede abandonar este grupo de WhatsApp porque está "
                    "vinculado a la unidad y es compartido por múltiples viajes. "
                    "Para abandonar el grupo, debe eliminarse primero de la tabla units."
                ),
                "shared_group": True,
                "unit_id": unit["id"]
            }
        
        # 4. Si llegamos aquí, es seguro continuar con la limpieza original
        conversation = await self.conversation_repo.find_by_trip(trip_id)
        
        if not conversation:
            logger.warning("no_conversation_found_for_cleanup", trip_id=trip_id)
            return {
                "success": False, 
                "message": "No se encontró conversación para este viaje."
            }

        whatsapp_group_id = conversation.get("whatsapp_group_id")
        conversation_id = conversation.get("id")

        if not whatsapp_group_id:
            logger.warning(
                "conversation_has_no_group_id", 
                trip_id=trip_id, 
                conversation_id=conversation_id
            )
            return {
                "success": False, 
                "message": "La conversación no tiene un ID de grupo de WhatsApp."
            }

        try:
            # 2. Llamar a la API para salir del grupo
            await self.evolution_client.leave_group(whatsapp_group_id)
            logger.info(
                "trip_group_left_api_success", 
                trip_id=trip_id, 
                group_id=whatsapp_group_id
            )
            
            # 3. Desactivar la conversación en la BD
            if conversation_id:
                await self.conversation_repo.deactivate_conversation(conversation_id)
                logger.info(
                    "conversation_deactivated_in_db", 
                    trip_id=trip_id, 
                    conversation_id=conversation_id
                )

            return {
                "success": True, 
                "message": f"Bot ha salido del grupo {whatsapp_group_id} y la conversación ha sido desactivada."
            }

        except Exception as e:
            logger.error(
                "trip_group_cleanup_failed", 
                trip_id=trip_id, 
                group_id=whatsapp_group_id, 
                error=str(e)
            )
            # Lanzar BusinessLogicError para que el endpoint la maneje
            raise BusinessLogicError(f"Error al limpiar el grupo: {str(e)}")

