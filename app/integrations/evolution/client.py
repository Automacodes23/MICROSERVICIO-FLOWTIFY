"""
Cliente para Evolution API (WhatsApp)
"""
import httpx
from typing import Dict, Any, List, Optional
from app.core.logging import get_logger
from app.core.errors import EvolutionAPIError
from app.integrations.evolution.schemas import (
    SendTextRequest,
    CreateGroupRequest,
    AddParticipantsRequest,
    EvolutionAPIResponse,
)

logger = get_logger(__name__)

# Configuración para resolver problemas de DNS en Windows
HTTPX_LIMITS = httpx.Limits(max_keepalive_connections=5, max_connections=10)
HTTPX_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class EvolutionClient:
    """Cliente para interactuar con Evolution API"""

    def __init__(self, api_url: str, api_key: str, instance: str, timeout: int = 30):
        """
        Inicializar cliente de Evolution API

        Args:
            api_url: URL base de la API
            api_key: API key para autenticación
            instance: Nombre de la instancia
            timeout: Timeout para las peticiones (segundos)
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance
        self.timeout = timeout
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def send_text(self, number: str, text: str) -> Dict[str, Any]:
        """
        Enviar mensaje de texto

        Args:
            number: Número o ID del grupo (formato: 5214771234567@g.us para grupos)
            text: Texto del mensaje

        Returns:
            Respuesta de la API
        """
        try:
            url = f"{self.api_url}/message/sendText/{self.instance}"
            payload = SendTextRequest(number=number, text=text).model_dump()

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                logger.info(
                    "whatsapp_message_sent",
                    number=number,
                    text_length=len(text),
                    status_code=response.status_code,
                )

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "evolution_api_error",
                error=str(e),
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise EvolutionAPIError(
                f"Error al enviar mensaje: {e.response.status_code}",
                context={"response": e.response.text},
            )
        except Exception as e:
            logger.error("evolution_api_error", error=str(e))
            raise EvolutionAPIError(f"Error al enviar mensaje: {str(e)}")

    async def send_audio(self, number: str, audio_url: str) -> Dict[str, Any]:
        """
        Enviar mensaje de audio

        Args:
            number: Número o ID del grupo
            audio_url: URL del audio

        Returns:
            Respuesta de la API
        """
        try:
            url = f"{self.api_url}/message/sendWhatsAppAudio/{self.instance}"
            payload = {"number": number, "audioMessage": {"audio": audio_url}}

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                logger.info("whatsapp_audio_sent", number=number)
                return response.json()

        except Exception as e:
            logger.error("evolution_api_error", error=str(e))
            raise EvolutionAPIError(f"Error al enviar audio: {str(e)}")

    async def create_group(
        self, subject: str, participants: List[str]
    ) -> Dict[str, Any]:
        """
        Crear grupo de WhatsApp

        Args:
            subject: Nombre del grupo
            participants: Lista de participantes (formato: 5214771234567@s.whatsapp.net)

        Returns:
            Respuesta de la API con información del grupo
        """
        try:
            url = f"{self.api_url}/group/create/{self.instance}"
            payload = CreateGroupRequest(
                subject=subject, participants=participants
            ).model_dump()
            
            logger.info(
                "evolution_create_group_attempt",
                url=url,
                api_url=self.api_url,
                instance=self.instance,
                participants_count=len(participants)
            )

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                data = response.json()
                
                # Normalizar la respuesta: agregar 'id' si solo existe 'groupId'
                if "groupId" in data and "id" not in data:
                    data["id"] = data["groupId"]
                
                logger.info(
                    "whatsapp_group_created",
                    subject=subject,
                    participants_count=len(participants),
                    group_id=data.get("groupId") or data.get("id"),
                )

                return data

        except Exception as e:
            logger.error("evolution_api_error", error=str(e))
            raise EvolutionAPIError(f"Error al crear grupo: {str(e)}")

    async def add_participants(
        self, group_jid: str, participants: List[str]
    ) -> Dict[str, Any]:
        """
        Agregar participantes a un grupo

        Args:
            group_jid: ID del grupo (formato: 120363405870310803@g.us)
            participants: Lista de participantes a agregar

        Returns:
            Respuesta de la API
        """
        try:
            url = f"{self.api_url}/group/updateParticipant/{self.instance}"
            payload = {
                "groupJid": group_jid,
                "action": "add",
                "participants": participants,
            }

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                logger.info(
                    "whatsapp_participants_added",
                    group_jid=group_jid,
                    participants_count=len(participants),
                )

                return response.json()

        except Exception as e:
            logger.error("evolution_api_error", error=str(e))
            raise EvolutionAPIError(f"Error al agregar participantes: {str(e)}")

    async def get_group_info(self, group_jid: str) -> Dict[str, Any]:
        """
        Obtener información de un grupo

        Args:
            group_jid: ID del grupo

        Returns:
            Información del grupo
        """
        try:
            url = f"{self.api_url}/group/fetchAllGroups/{self.instance}"

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error("evolution_api_error", error=str(e))
            raise EvolutionAPIError(f"Error al obtener info del grupo: {str(e)}")

    async def download_media(self, media_url: str) -> bytes:
        """
        Descargar media de WhatsApp

        Args:
            media_url: URL del media

        Returns:
            Bytes del archivo
        """
        try:
            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.get(media_url)
                response.raise_for_status()

                logger.info("whatsapp_media_downloaded", url=media_url)
                return response.content

        except Exception as e:
            logger.error("evolution_api_error", error=str(e))
            raise EvolutionAPIError(f"Error al descargar media: {str(e)}")

    async def leave_group(self, group_jid: str) -> Dict[str, Any]:
        """
        Hacer que el bot abandone un grupo de WhatsApp.

        Args:
            group_jid: ID del grupo (ej: 120363405870310803@g.us)

        Returns:
            Respuesta de la API

        Note:
            Este método asume que Evolution API soporta DELETE /group/leaveGroup/{instance}
            con el parámetro groupJid. Verificar la documentación de Evolution API antes de usar.
        """
        try:
            url = f"{self.api_url}/group/leaveGroup/{self.instance}"
            params = {"groupJid": group_jid}

            logger.info(
                "whatsapp_group_leaving_attempt",
                group_jid=group_jid,
                url=url
            )

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                # Usando DELETE según especificación típica de Evolution API
                response = await client.delete(url, headers=self.headers, params=params)
                response.raise_for_status()

                logger.info(
                    "whatsapp_group_left",
                    group_jid=group_jid,
                    status_code=response.status_code,
                )
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "evolution_api_error_leave_group",
                error=str(e),
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise EvolutionAPIError(
                f"Error al salir del grupo: {e.response.status_code}",
                context={"response": e.response.text},
            )
        except Exception as e:
            logger.error("evolution_api_error_leave_group", error=str(e))
            raise EvolutionAPIError(f"Error al salir del grupo: {str(e)}")

    async def start_typing(self, number: str) -> None:
        """
        Enviar indicador de "escribiendo..." a un chat o grupo.
        
        Args:
            number: Número de teléfono o ID de grupo (ej: 120363405870310803@g.us)
        
        Note:
            Evolution API puede no soportar este endpoint en todas las versiones.
            Si falla, el error se registra pero no se propaga.
            Endpoint esperado: POST /chat/presence/{instance} o similar
        """
        try:
            # Intentar diferentes posibles endpoints según versión de Evolution API
            possible_endpoints = [
                f"{self.api_url}/chat/presence/{self.instance}",  # Versión más común
                f"{self.api_url}/chat/setPresence/{self.instance}",  # Alternativa
            ]
            
            payload = {
                "number": number,
                "presence": "composing",
                "delay": 3000  # 3 segundos de duración del indicador
            }
            
            # Intentar el primer endpoint
            url = possible_endpoints[0]

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                logger.debug(
                    "typing_indicator_started",
                    number=number,
                    status_code=response.status_code
                )

        except httpx.HTTPStatusError as e:
            logger.warning(
                "typing_indicator_start_failed",
                error=str(e),
                status_code=e.response.status_code,
                number=number,
                response_text=e.response.text
            )
            # No lanzar excepción - el indicador de typing es opcional
        except Exception as e:
            logger.warning(
                "typing_indicator_start_error",
                error=str(e),
                number=number
            )
            # No lanzar excepción - el indicador de typing es opcional

    async def stop_typing(self, number: str) -> None:
        """
        Detener el indicador de "escribiendo..." y volver a estado normal.
        
        Args:
            number: Número de teléfono o ID de grupo (ej: 120363405870310803@g.us)
        
        Note:
            Evolution API puede no soportar este endpoint en todas las versiones.
            Si falla, el error se registra pero no se propaga.
        """
        try:
            # Intentar diferentes posibles endpoints según versión de Evolution API
            possible_endpoints = [
                f"{self.api_url}/chat/presence/{self.instance}",
                f"{self.api_url}/chat/setPresence/{self.instance}",
            ]
            
            payload = {
                "number": number,
                "presence": "paused",  # "paused" limpia el estado de typing
                "delay": 0
            }
            
            url = possible_endpoints[0]

            async with httpx.AsyncClient(
                timeout=HTTPX_TIMEOUT,
                limits=HTTPX_LIMITS,
                trust_env=False,
                http2=False,
                verify=True
            ) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                logger.debug(
                    "typing_indicator_stopped",
                    number=number,
                    status_code=response.status_code
                )

        except httpx.HTTPStatusError as e:
            logger.warning(
                "typing_indicator_stop_failed",
                error=str(e),
                status_code=e.response.status_code,
                number=number,
                response_text=e.response.text
            )
            # No lanzar excepción - la limpieza del indicador no debe romper el flujo
        except Exception as e:
            logger.warning(
                "typing_indicator_stop_error",
                error=str(e),
                number=number
            )
            # No lanzar excepción - la limpieza del indicador no debe romper el flujo

