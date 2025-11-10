"""
Servicio para procesamiento de mensajes de WhatsApp
"""
from typing import Dict, Any, Optional
import uuid
from app.core.logging import get_logger, log_context
from app.core.errors import BusinessLogicError
from app.core.database import Database
from app.core.constants import MESSAGE_INTENTS, MESSAGE_DIRECTIONS, SENDER_TYPES
from app.repositories.message_repository import (
    MessageRepository,
    ConversationRepository,
    AIInteractionRepository,
)
from app.repositories.trip_repository import TripRepository
from app.repositories.unit_repository import UnitRepository
from app.integrations.gemini.client import GeminiClient
from app.integrations.evolution.client import EvolutionClient
from app.models.message import WhatsAppMessage

logger = get_logger(__name__)


class MessageService:
    """Servicio para procesar mensajes de WhatsApp"""

    def __init__(self, db: Database, gemini_client: GeminiClient, evolution_client: EvolutionClient):
        self.db = db
        self.gemini_client = gemini_client
        self.evolution_client = evolution_client
        self.message_repo = MessageRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.ai_interaction_repo = AIInteractionRepository(db)
        self.trip_repo = TripRepository(db)
        self.unit_repo = UnitRepository(db)

    async def process_whatsapp_message(
        self, message: WhatsAppMessage
    ) -> Dict[str, Any]:
        """
        Procesar mensaje de WhatsApp

        Args:
            message: Mensaje de WhatsApp desde Evolution API

        Returns:
            Resultado del procesamiento con respuesta de IA
        """
        trace_id = str(uuid.uuid4())
        log_context(trace_id=trace_id, instance=message.instance)

        try:
            # Extraer datos del mensaje
            message_key = message.data.key
            group_id = message_key.get("remoteJid")
            
            # Evolution API puede enviar 'participant' o 'participantPn'
            sender_phone = message_key.get("participantPn") or message_key.get("participant", "")
            if sender_phone:
                sender_phone = sender_phone.replace("@s.whatsapp.net", "")
            
            message_content = message.data.message

            logger.info(
                "whatsapp_message_received",
                group_id=group_id,
                sender=sender_phone,
                message_type=message.data.messageType,
            )

            # Obtener texto del mensaje
            text = message_content.get("conversation", "")
            transcription = None

            # Si es audio, transcribirlo con Gemini
            if "audioMessage" in message_content:
                audio_message = message_content.get("audioMessage", {})
                audio_url = audio_message.get("url")
                raw_mime_type = audio_message.get("mimetype", "audio/ogg")
                
                # Normalizar mime_type (WhatsApp puede enviar "audio/ogg; codecs=opus")
                mime_type = raw_mime_type.split(";")[0].strip()
                
                logger.info(
                    "audio_message_received",
                    group_id=group_id,
                    audio_url=audio_url,
                    raw_mime_type=raw_mime_type,
                    normalized_mime_type=mime_type
                )
                
                if audio_url:
                    try:
                        # Descargar audio desde Evolution API
                        audio_bytes = await self.evolution_client.download_media(audio_url)
                        
                        logger.info(
                            "audio_downloaded",
                            group_id=group_id,
                            audio_size_bytes=len(audio_bytes)
                        )
                        
                        # Obtener contexto del viaje para la transcripción
                        conversation = await self.conversation_repo.find_by_group_id(group_id)
                        trip_context = None
                        if conversation:
                            trip = await self.trip_repo.find_by_id(conversation["trip_id"])
                            if trip:
                                trip_context = {
                                    "trip_status": trip.get("status"),
                                    "trip_substatus": trip.get("substatus")
                                }
                        
                        # Transcribir audio con Gemini
                        logger.info(
                            "starting_gemini_transcription",
                            group_id=group_id,
                            mime_type=mime_type,
                            audio_size=len(audio_bytes)
                        )
                        
                        transcription = await self.gemini_client.transcribe_audio(
                            audio_bytes,
                            mime_type=mime_type,
                            context=trip_context
                        )
                        
                        text = transcription
                        logger.info(
                            "audio_transcribed_successfully",
                            group_id=group_id,
                            transcription_length=len(transcription),
                            transcription_preview=transcription[:100]
                        )
                        
                    except Exception as e:
                        import traceback
                        error_traceback = traceback.format_exc()
                        
                        logger.error(
                            "audio_transcription_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            group_id=group_id,
                            mime_type=mime_type,
                            audio_url=audio_url,
                            traceback=error_traceback
                        )
                        
                        # Mensaje de error contextual para el usuario
                        text = f"[Error al transcribir audio: {type(e).__name__}]"
                else:
                    logger.warning("audio_message_without_url", group_id=group_id)
                    text = "[Audio sin URL de descarga]"

            if not text or not group_id:
                logger.warning("invalid_message_data", text=bool(text), group_id=bool(group_id))
                return {"success": False, "message": "Invalid message"}

            # Buscar conversación y viaje con lógica de fallback
            logger.info("looking_for_conversation", group_id=group_id)
            conversation = await self.conversation_repo.find_by_group_id(group_id)
            
            # LOG ADICIONAL CRÍTICO
            logger.info("conversation_lookup_result", conversation_found=bool(conversation), conversation_id=conversation.get("id") if conversation else None)

            trip = None
            conversation_auto_created = False

            if not conversation:
                # ========================================
                # FALLBACK: Buscar unidad por grupo de WhatsApp
                # ========================================
                logger.warning(
                    "conversation_not_found_trying_fallback",
                    group_id=group_id,
                    fallback_strategy="search_unit_by_group_id"
                )
                
                # 1. Buscar la unidad por su grupo de WhatsApp
                unit = await self.unit_repo.find_by_whatsapp_group_id(group_id)
                
                if unit:
                    logger.info(
                        "unit_found_by_group_id",
                        unit_id=unit["id"],
                        unit_name=unit.get("name"),
                        group_id=group_id
                    )
                    
                    # 2. Buscar viaje activo de esa unidad
                    trip = await self.trip_repo.find_active_by_unit(unit["id"])
                    
                    if trip:
                        logger.info(
                            "active_trip_found_for_unit",
                            trip_id=trip["id"],
                            trip_code=trip.get("floatify_trip_id"),
                            trip_status=trip.get("status"),
                            unit_id=unit["id"]
                        )
                        
                        # 3. Recrear la conversación automáticamente
                        try:
                            conversation_data = {
                                "trip_id": trip["id"],
                                "whatsapp_group_id": group_id,
                                "driver_id": trip.get("driver_id"),
                                "status": "active",
                                "metadata": {
                                    "auto_created": True,
                                    "created_from": "fallback_recovery",
                                    "unit_id": unit["id"],
                                    "reason": "conversation_missing_after_data_cleanup"
                                }
                            }
                            conversation = await self.conversation_repo.create_conversation(conversation_data)
                            conversation_auto_created = True
                            
                            logger.info(
                                "conversation_auto_created_successfully",
                                conversation_id=conversation.get("id"),
                                trip_id=trip["id"],
                                group_id=group_id,
                                fallback_recovery="success"
                            )
                        except Exception as conv_error:
                            logger.error(
                                "conversation_auto_creation_failed",
                                error=str(conv_error),
                                trip_id=trip["id"],
                                group_id=group_id
                            )
                            # Continuar sin conversación, al menos tenemos el trip
                    else:
                        logger.warning(
                            "no_active_trip_for_unit",
                            unit_id=unit["id"],
                            unit_name=unit.get("name"),
                            group_id=group_id
                        )
                        return {
                            "success": True,
                            "message": "No active trip found for this unit",
                            "fallback_attempted": True,
                            "unit_found": True,
                            "trip_found": False
                        }
                else:
                    logger.warning(
                        "fallback_failed_unit_not_found",
                        group_id=group_id,
                        reason="No unit associated with this WhatsApp group"
                    )
                    return {
                        "success": True,
                        "message": "No trip or unit found for this group",
                        "fallback_attempted": True,
                        "unit_found": False
                    }
            else:
                # Conversación encontrada, obtener el trip normalmente
                trip = await self.trip_repo.find_by_id(conversation["trip_id"])

            # Verificar que tenemos un trip válido
            if not trip:
                logger.error(
                    "trip_not_found_after_conversation_lookup",
                    conversation_id=conversation.get("id") if conversation else None,
                    group_id=group_id
                )
                return {
                    "success": False,
                    "message": "Trip not found",
                    "conversation_found": bool(conversation)
                }
            
            # LOG ADICIONAL
            logger.info("associated_trip_found", trip_id=trip["id"], trip_status=trip.get("status"))

            # Guardar mensaje (solo si tenemos conversación)
            saved_message = None
            if conversation:
                message_data = {
                    "conversation_id": conversation["id"],
                    "trip_id": trip["id"],
                    "whatsapp_message_id": message_key.get("id"),
                    "sender_type": SENDER_TYPES["DRIVER"],
                    "sender_phone": sender_phone,
                    "direction": MESSAGE_DIRECTIONS["INBOUND"],
                    "content": text,
                    "transcription": transcription,  # Guardar transcripción si hay
                    "ai_result": None,
                }
                saved_message = await self.message_repo.create_message(message_data)
                logger.info(
                    "message_saved",
                    message_id=saved_message["id"],
                    conversation_auto_created=conversation_auto_created
                )
            else:
                logger.warning(
                    "message_not_saved_no_conversation",
                    trip_id=trip["id"],
                    group_id=group_id,
                    reason="Conversation could not be created during fallback"
                )

            # Procesar con IA - ENVUELTO CON INDICADORES DE PRESENCIA
            try:
                # 1. Enviar indicador "escribiendo..." antes de la operación larga
                logger.debug("sending_typing_indicator", group_id=group_id)
                await self.evolution_client.start_typing(group_id)
                
                # 2. Operación larga: Llamada a Gemini
                logger.info("calling_gemini_for_classification", text_length=len(text))
                ai_result = await self.gemini_client.classify_message(
                    text,
                    {
                        "status": trip["status"],
                        "substatus": trip["substatus"],
                        "location": None,
                    },
                )
                
                # LOG ADICIONAL
                logger.info("gemini_ai_result", intent=ai_result.get("intent"), confidence=ai_result.get("confidence"), has_response=bool(ai_result.get("response")))
            
            finally:
                # 3. SIEMPRE limpiar el indicador "escribiendo...", incluso si Gemini falló
                logger.debug("stopping_typing_indicator", group_id=group_id)
                await self.evolution_client.stop_typing(group_id)

            # Guardar interacción de IA (solo si guardamos el mensaje)
            if saved_message:
                interaction_data = {
                    "message_id": saved_message["id"],
                    "trip_id": trip["id"],
                    "input_text": text,
                    "response_text": ai_result.get("response"),
                    "intent": ai_result.get("intent"),
                    "confidence": ai_result.get("confidence"),
                    "entities": ai_result.get("entities", {}),
                    "response_metadata": ai_result,
                }
                
                # LOG ADICIONAL
                logger.info("saving_ai_interaction", message_id=saved_message["id"], trip_id=trip["id"])
                await self.ai_interaction_repo.create_interaction(interaction_data)
                logger.info("ai_interaction_saved", message_id=saved_message["id"])
            else:
                logger.warning(
                    "ai_interaction_not_saved",
                    trip_id=trip["id"],
                    reason="No message record to associate with"
                )

            # Actualizar estado si es necesario
            if ai_result.get("action") == "update_substatus" and ai_result.get(
                "new_substatus"
            ):
                new_substatus = ai_result.get("new_substatus")
                await self.trip_repo.update_status(
                    trip["id"], trip["status"], new_substatus
                )
                logger.info(
                    "trip_substatus_updated_by_message",
                    trip_id=trip["id"],
                    new_substatus=new_substatus,
                    intent=ai_result.get("intent"),
                )
            
            # Finalizar viaje si se completó la descarga
            intent = ai_result.get("intent")
            if intent == "unloading_complete":
                logger.info(
                    "trip_completion_detected",
                    trip_id=trip["id"],
                    intent=intent,
                    message=text
                )
                # Actualizar a estado finalizado
                await self.trip_repo.update_status(
                    trip["id"], 
                    "finalizado", 
                    "descarga_completada"
                )
                logger.info(
                    "trip_completed_by_message",
                    trip_id=trip["id"],
                    final_status="finalizado",
                    final_substatus="descarga_completada"
                )

            return {
                "success": True,
                "message_id": saved_message["id"] if saved_message else None,
                "ai_result": ai_result,
                "should_respond": True,
                "message": "Message processed successfully",
                "fallback_recovery": conversation_auto_created,
                "conversation_id": conversation["id"] if conversation else None,
            }

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error("message_processing_failed", error=str(e), error_type=type(e).__name__, traceback=error_traceback)
            raise BusinessLogicError(f"Error procesando mensaje: {str(e)}")

    async def get_conversation_messages(
        self, conversation_id: int, limit: int = 100, offset: int = 0
    ) -> list:
        """Obtener mensajes de una conversación"""
        return await self.message_repo.find_by_conversation(
            conversation_id, limit, offset
        )

    async def get_trip_messages(
        self, trip_id: str, limit: int = 100, offset: int = 0
    ) -> list:
        """Obtener mensajes de un viaje"""
        return await self.message_repo.find_by_trip(trip_id, limit, offset)

