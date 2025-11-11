"""
Servicio para envío de notificaciones
"""
from typing import Optional, Dict, Any
from app.core.logging import get_logger
from app.core.database import Database
from app.repositories.message_repository import ConversationRepository
from app.integrations.evolution.client import EvolutionClient

logger = get_logger(__name__)


class NotificationService:
    """Servicio para enviar notificaciones via WhatsApp"""

    def __init__(
        self,
        db: Database,
        evolution_client: EvolutionClient,
        webhook_service=None,  # Inyección opcional de WebhookService
    ):
        self.db = db
        self.evolution_client = evolution_client
        self.webhook_service = webhook_service
        self.conversation_repo = ConversationRepository(db)

    async def send_trip_notification(
        self, trip_id: str, message: str
    ) -> bool:
        """
        Enviar notificación a un viaje específico

        Args:
            trip_id: ID del viaje
            message: Mensaje a enviar

        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        try:
            # Buscar conversación del viaje
            conversation = await self.conversation_repo.find_by_trip(trip_id)

            if not conversation:
                logger.warning(
                    "conversation_not_found_for_trip", trip_id=trip_id
                )
                return False

            if not conversation.get("is_active"):
                logger.warning(
                    "conversation_not_active", trip_id=trip_id
                )
                return False

            # Enviar mensaje
            await self.evolution_client.send_text(
                conversation["whatsapp_group_id"], message
            )

            logger.info(
                "notification_sent",
                trip_id=trip_id,
                group_id=conversation["whatsapp_group_id"],
            )
            return True

        except Exception as e:
            logger.error(
                "notification_send_failed",
                trip_id=trip_id,
                error=str(e),
            )
            return False

    async def send_notification_to_group(
        self,
        group_id: str,
        message: str,
        trip_id: Optional[str] = None,
        ai_result: Optional[Dict[str, Any]] = None,
        driver_message: Optional[str] = None,
        original_message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """
        Enviar notificación directamente a un grupo

        Args:
            group_id: ID del grupo de WhatsApp
            message: Mensaje a enviar (respuesta del bot)
            trip_id: ID del viaje (para webhook)
            ai_result: Resultado de análisis AI (para webhook)
            driver_message: Mensaje original del conductor
            original_message_id: ID del mensaje original del conductor
            conversation_id: ID de la conversación

        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        try:
            # Enviar mensaje
            await self.evolution_client.send_text(group_id, message)
            logger.info("notification_sent_to_group", group_id=group_id)
            
            # Guardar el mensaje OUTBOUND del bot en la BD
            if trip_id and conversation_id:
                try:
                    from app.repositories.message_repository import MessageRepository
                    from app.core.constants import MESSAGE_DIRECTIONS, SENDER_TYPES
                    
                    message_repo = MessageRepository(self.db)
                    
                    bot_message_data = {
                        "conversation_id": conversation_id,
                        "trip_id": trip_id,
                        "whatsapp_message_id": None,  # No tenemos ID de WhatsApp para mensajes salientes
                        "sender_type": SENDER_TYPES["BOT"],
                        "sender_phone": None,  # El bot no tiene teléfono
                        "direction": MESSAGE_DIRECTIONS["OUTBOUND"],
                        "content": message,
                        "transcription": None,
                        "ai_result": ai_result,
                    }
                    
                    saved_bot_message = await message_repo.create_message(bot_message_data)
                    logger.info(
                        "bot_message_saved_outbound",
                        message_id=saved_bot_message["id"],
                        conversation_id=conversation_id,
                        trip_id=trip_id,
                    )
                except Exception as save_error:
                    logger.error(
                        "failed_to_save_bot_message",
                        error=str(save_error),
                        trip_id=trip_id,
                    )
            
            # Enviar webhook de communication_response si tenemos webhook_service
            if self.webhook_service and trip_id:
                try:
                    import uuid
                    message_id = str(uuid.uuid4())
                    
                    response_data = {
                        "sender_type": "bot",
                        "content": message,
                        "conversation_id": conversation_id,
                        "response_type": "ai_response",
                        "ai_model": "gemini-pro",
                        "confidence": ai_result.get("confidence", 0) if ai_result else 0,
                        "ai_analysis": ai_result or {},
                        "delivery_status": {
                            "message_sent": True,
                            "delivery_status": "sent",
                        },
                        # ✅ NUEVO: Agregar mensaje original del conductor
                        "driver_message": driver_message,
                        "original_message_id": original_message_id,
                        "context": {},
                        "metadata": {},
                    }
                    
                    await self.webhook_service.send_communication_response(
                        trip_id=trip_id,
                        message_id=message_id,
                        response_data=response_data,
                    )
                    logger.info(
                        "communication_response_webhook_sent",
                        trip_id=trip_id,
                        message_id=message_id,
                    )
                except Exception as webhook_error:
                    # Log pero no fallar el envío del mensaje
                    logger.error(
                        "communication_webhook_failed",
                        error=str(webhook_error),
                        trip_id=trip_id,
                    )
            
            return True

        except Exception as e:
            logger.error(
                "notification_send_failed",
                group_id=group_id,
                error=str(e),
            )
            return False

    async def send_bulk_notification(
        self, trip_ids: list[str], message: str
    ) -> dict:
        """
        Enviar notificación a múltiples viajes

        Args:
            trip_ids: Lista de IDs de viajes (UUIDs como strings)
            message: Mensaje a enviar

        Returns:
            Diccionario con estadísticas de envío
        """
        sent = 0
        failed = 0

        for trip_id in trip_ids:
            success = await self.send_trip_notification(trip_id, message)
            if success:
                sent += 1
            else:
                failed += 1

        logger.info(
            "bulk_notification_completed",
            total=len(trip_ids),
            sent=sent,
            failed=failed,
        )

        return {
            "total": len(trip_ids),
            "sent": sent,
            "failed": failed,
        }

