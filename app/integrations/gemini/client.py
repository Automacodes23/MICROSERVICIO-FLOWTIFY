"""
Cliente para Gemini AI
"""
import google.generativeai as genai
from typing import Dict, Any, Optional
import json
from app.core.logging import get_logger
from app.core.errors import GeminiAPIError
from app.integrations.gemini.prompts import (
    get_message_classification_prompt,
    SYSTEM_PROMPT,
)

logger = get_logger(__name__)


class GeminiClient:
    """Cliente para interactuar con Gemini AI"""

    def __init__(self, api_key: str, model: str = "gemini-flash-latest", timeout: int = 60):
        """
        Inicializar cliente de Gemini AI

        Args:
            api_key: API key de Google
        """
        self.api_key = api_key
        self.model_name = model
        self.timeout = timeout

        # Configurar Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)

    async def classify_message(
        self, text: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Clasificar mensaje del conductor usando Gemini

        Args:
            text: Mensaje del conductor
            context: Contexto del viaje (status, substatus, etc.)

        Returns:
            Diccionario con intención, confianza, respuesta y acción
        """
        try:
            prompt = get_message_classification_prompt(text, context)

            # Generar respuesta
            response = await self._generate_content(prompt)
            text_response = response.text.strip()

            # Limpiar markdown si existe
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]

            # Parsear JSON
            try:
                result = json.loads(text_response.strip())
                logger.info(
                    "gemini_message_classified",
                    intent=result.get("intent"),
                    confidence=result.get("confidence"),
                )
                return result
            except json.JSONDecodeError as e:
                logger.error(
                    "gemini_json_parse_error",
                    error=str(e),
                    response=text_response[:200],
                )
                # Retornar respuesta por defecto
                return {
                    "intent": "other",
                    "confidence": 0.5,
                    "entities": {},
                    "response": "Entendido. ¿Puedes darme más detalles?",
                    "action": "no_action",
                    "new_substatus": None,
                }

        except Exception as e:
            logger.error("gemini_classification_error", error=str(e))
            raise GeminiAPIError(f"Error al clasificar mensaje: {str(e)}")

    async def transcribe_audio(
        self, audio_data: bytes, mime_type: str = "audio/ogg", context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Transcribir audio usando Gemini 1.5
        
        Gemini 1.5 Flash y Pro soportan procesamiento de audio multimodal.
        Soporta formatos: WAV, MP3, AIFF, AAC, OGG, FLAC

        Args:
            audio_data: Bytes del archivo de audio
            mime_type: Tipo MIME del audio (ej: "audio/ogg", "audio/mp3", "audio/wav")
            context: Contexto adicional (información del viaje)

        Returns:
            Texto transcrito del audio
        """
        try:
            logger.info(
                "audio_transcription_started",
                audio_size_bytes=len(audio_data),
                mime_type=mime_type,
                context=context
            )
            
            # Crear modelo específico para transcripción
            # Usamos el modelo base sin system_instruction para transcripción
            transcription_model = genai.GenerativeModel(self.model_name)
            
            # Preparar el audio como parte del contenido
            # Gemini acepta audio inline con base64
            import base64
            
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Crear prompt contextual para transcripción
            transcription_prompt = self._build_transcription_prompt(context)
            
            # Preparar el contenido multimodal
            # Gemini 1.5 soporta audio inline con base64
            logger.info("preparing_audio_for_gemini", audio_size=len(audio_data), mime_type=mime_type)
            
            try:
                # Usar API inline_data que funciona con todas las versiones
                audio_part = {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_base64
                    }
                }
                
                # Generar transcripción con configuración optimizada
                logger.info("generating_transcription_with_inline_audio", 
                           prompt=transcription_prompt,
                           prompt_length=len(transcription_prompt),
                           model=self.model_name)
                response = transcription_model.generate_content(
                    [transcription_prompt, audio_part],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,  # Temperatura muy baja para transcripción más literal
                        max_output_tokens=512,
                        top_p=0.95,
                        top_k=40,
                    ),
                )
                
                transcription = response.text.strip()
                
                logger.info(
                    "audio_transcription_completed",
                    transcription_length=len(transcription),
                    transcription=transcription[:200]
                )
                
                return transcription
                
            except Exception as e:
                # Log detallado del error específico
                import traceback
                logger.error(
                    "gemini_audio_processing_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    mime_type=mime_type,
                    audio_size=len(audio_data),
                    traceback=traceback.format_exc()
                )
                raise
                
        except Exception as e:
            import traceback
            logger.error(
                "gemini_transcription_error",
                error=str(e),
                error_type=type(e).__name__,
                mime_type=mime_type,
                audio_size=len(audio_data),
                traceback=traceback.format_exc()
            )
            raise GeminiAPIError(f"Error al transcribir audio: {str(e)}")
    
    def _build_transcription_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Construir prompt contextual para transcripción de audio
        
        Args:
            context: Contexto del viaje/conversación
            
        Returns:
            Prompt para transcripción
        """
        # Prompt más directo y simple para mejor transcripción
        base_prompt = """Transcribe este audio en español. Devuelve SOLO el texto exacto que se dice, sin añadir ninguna explicación, comentario o formato adicional."""

        # El contexto puede confundir al modelo, solo agregarlo si es muy relevante
        if context and context.get("trip_status") and context.get("trip_status") != "desconocido":
            # Contexto mínimo para ayudar con terminología específica
            base_prompt = f"""
Transcribe el audio en español. Devuelve SOLO el texto exacto que se dice."""
        
        return base_prompt

    async def generate_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generar respuesta usando Gemini

        Args:
            prompt: Prompt para Gemini
            context: Contexto adicional

        Returns:
            Respuesta generada
        """
        try:
            response = await self._generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error("gemini_generation_error", error=str(e))
            raise GeminiAPIError(f"Error al generar respuesta: {str(e)}")

    async def _generate_content(self, prompt: str) -> Any:
        """
        Generar contenido usando el modelo

        Args:
            prompt: Prompt para el modelo

        Returns:
            Respuesta del modelo
        """
        try:
            # Gemini no tiene async nativo, usamos sync
            # En producción, considera usar un executor para no bloquear
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )
            return response

        except Exception as e:
            logger.error("gemini_api_error", error=str(e))
            raise GeminiAPIError(f"Error en API de Gemini: {str(e)}")

    def extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extraer entidades del texto según la intención

        Args:
            text: Texto del mensaje
            intent: Intención detectada

        Returns:
            Diccionario con entidades extraídas
        """
        entities = {}

        # Lógica básica de extracción de entidades
        text_lower = text.lower()

        # Ubicaciones comunes
        if "patio" in text_lower:
            entities["next_destination"] = "patio"
        elif "taller" in text_lower:
            entities["next_destination"] = "taller"
        elif "base" in text_lower:
            entities["next_destination"] = "base"

        # Problemas
        if "problema" in text_lower or "falla" in text_lower:
            entities["has_issue"] = True

        return entities

