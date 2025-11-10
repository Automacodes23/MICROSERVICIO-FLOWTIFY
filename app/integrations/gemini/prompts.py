"""
Prompts para Gemini AI
"""
from typing import Dict, Any
import json


def get_message_classification_prompt(text: str, context: Dict[str, Any]) -> str:
    """
    Generar prompt para clasificar mensaje del conductor

    Args:
        text: Mensaje del conductor
        context: Contexto del viaje (status, substatus, etc.)

    Returns:
        Prompt formateado
    """
    return f"""Eres un asistente de logística que ayuda a gestionar flotas de transporte en México. 
Analiza el siguiente mensaje del conductor y clasifícalo según la intención.

Mensaje: "{text}"

Contexto del viaje:
- Estado actual: {context.get('status', 'desconocido')}
- Subestado: {context.get('substatus', 'desconocido')}
- Ubicación: {context.get('location', 'desconocida')}

Posibles intenciones con EJEMPLOS de lenguaje coloquial mexicano:

1. waiting_turn - El conductor está esperando turno para cargar/descargar
   Ejemplos: "esperando en el anden", "estoy esperando turno", "aquí formado", "esperando que me asignen anden"

2. loading_started - El conductor inició la carga
   Ejemplos: "ya empece a cargar", "ya empezamos a cargar", "iniciando carga", "ya estamos cargando"

3. loading_complete - El conductor terminó la carga
   Ejemplos: "ya termine la carga", "listo ya quedo", "carga completa", "ya terminamos de cargar", "ya está lista la carga"

4. unloading_started - El conductor inició la descarga
   Ejemplos: "ya empece a descargar", "iniciando descarga", "ya estamos descargando", "empezando a descargar"

5. unloading_complete - El conductor terminó la descarga y está listo para irse
   Ejemplos: "ya termine de descargar me voy", "YA Ternine ya me voy", "listo ya acabé aquí", 
   "descarga completa me retiro", "ya terminé todo me voy", "ya quedó todo listo me voy", 
   "ya terminamos aquí", "ya acabé ya me voy", "todo listo me retiro"
   IMPORTANTE: Si el mensaje indica que terminó de descargar Y menciona irse/retirarse, es unloading_complete

6. route_update - Actualización de la ruta o ubicación (sin haber terminado operación)
   Ejemplos: "voy en camino", "estoy llegando", "me dirijo a", "voy para allá"

7. issue_report - Reporte de problema o incidente
   Ejemplos: "hay un problema", "se descompuso", "tuve una falla", "no puedo avanzar"

8. other - Otra intención (conversación casual, preguntas generales)
   Ejemplos: "buenos días", "gracias", "ok", "entendido"

REGLAS CRÍTICAS DE CLASIFICACIÓN:
- Si el mensaje contiene palabras como "terminé/termine/acabé" + "descargar/descarga" + "voy/me voy/retiro/salgo" → ES unloading_complete
- Si dice "empecé/empece/inicio/iniciando" + "descargar/descarga" → ES unloading_started
- Si dice "terminé/termine" + "carga/cargar" → ES loading_complete
- Prioriza el contexto del subestado actual para desambiguar

Responde SOLO con un JSON válido con esta estructura exacta (sin markdown):
{{
  "intent": "una de las intenciones listadas arriba",
  "confidence": 0.95,
  "entities": {{}},
  "response": "respuesta natural y amigable para el conductor en español",
  "action": "update_substatus o send_alert o no_action",
  "new_substatus": "nuevo subestado si action es update_substatus, null si no"
}}

IMPORTANTE: 
- Solo responde con el JSON, sin texto adicional
- No uses markdown (```json)
- La respuesta debe ser en español
- Sé amigable y profesional
- Para unloading_complete, la respuesta debe confirmar que el viaje está finalizado"""


def get_audio_transcription_prompt(context: Dict[str, Any]) -> str:
    """
    Generar prompt para transcripción de audio

    Args:
        context: Contexto adicional

    Returns:
        Prompt para transcripción
    """
    return """Transcribe este audio de WhatsApp enviado por un conductor de transporte.
El audio puede contener ruido de fondo, lenguaje informal o coloquial mexicano.
Transcribe exactamente lo que escuches, manteniendo el lenguaje original."""


SYSTEM_PROMPT = """Eres un asistente de IA especializado en logística y gestión de flotas de transporte.
Tu trabajo es ayudar a los conductores y supervisores durante las operaciones de transporte.
Debes ser conciso, amigable y profesional en tus respuestas.
Siempre responde en español."""

