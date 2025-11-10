"""
Router para webhooks de WhatsApp (Evolution API)
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.logging import get_logger
from app.core.errors import BaseServiceError
from app.services.message_service import MessageService
from app.services.notification_service import NotificationService
from app.api.dependencies import get_message_service, get_notification_service
from app.models.message import WhatsAppMessage
from app.models.responses import MessageProcessedResponse

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
logger = get_logger(__name__)


@router.post("/messages", response_model=MessageProcessedResponse)
async def receive_whatsapp_message(
    message: WhatsAppMessage,
    message_service: MessageService = Depends(get_message_service),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Recibir mensajes de WhatsApp desde Evolution API

    Procesa mensajes de conductores, los analiza con IA y genera respuestas.
    """
    print(f"\n=== WEBHOOK RECEIVED ===")
    print(f"Event: {message.event}")
    print(f"Instance: {message.instance}")
    print(f"Group ID: {message.data.key.get('remoteJid')}")
    print(f"========================\n")
    
    try:
        logger.info(
            "whatsapp_webhook_received",
            webhook_event=message.event,
            instance=message.instance,
            group_id=message.data.key.get("remoteJid"),
        )

        # Procesar mensaje
        result = await message_service.process_whatsapp_message(message)
        
        # LOG ADICIONAL: Ver qué decidió el servicio
        logger.info("message_service_result", success=result.get("success"), should_respond=result.get("should_respond"), has_ai_result=bool(result.get("ai_result")))

        # Si hay respuesta de IA, enviarla
        if result.get("should_respond") and result.get("ai_result"):
            ai_result = result["ai_result"]
            response_text = ai_result.get("response")

            if response_text:
                # Obtener group_id del mensaje original
                group_id = message.data.key.get("remoteJid")
                if group_id:
                    await notification_service.send_notification_to_group(
                        group_id, response_text
                    )

        return MessageProcessedResponse(
            success=result.get("success", True),
            message_id=result.get("message_id", ""),
            ai_result=result.get("ai_result"),
            message=result.get("message", "Message processed"),
        )

    except BaseServiceError as e:
        logger.error("whatsapp_message_processing_error", error=str(e), code=e.code)
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "success": False,
                "error": {
                    "code": e.code,
                    "message": e.message,
                },
            },
        )
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error("whatsapp_unexpected_error", error=str(e), error_type=type(e).__name__, traceback=error_traceback)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "type": type(e).__name__,
                    "traceback": error_traceback if True else None,  # Cambiar a False en producción
                },
            },
        )

