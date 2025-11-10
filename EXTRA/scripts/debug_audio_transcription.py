#!/usr/bin/env python3
"""
Script para debuggear problemas de transcripción de audio
"""
import asyncio
import sys
import os
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.integrations.gemini.client import GeminiClient
from app.integrations.evolution.client import EvolutionClient
from app.config import settings

setup_logging(log_level="DEBUG", json_logs=False)
logger = get_logger(__name__)


async def test_audio_download(audio_url: str):
    """Probar descarga de audio desde Evolution API"""
    print("\n" + "="*60)
    print("🎵 TEST 1: DESCARGAR AUDIO DESDE EVOLUTION API")
    print("="*60)
    
    try:
        evolution_client = EvolutionClient(
            api_url=settings.EVOLUTION_API_URL,
            api_key=settings.EVOLUTION_API_KEY,
            instance=settings.EVOLUTION_INSTANCE,
        )
        
        print(f"📥 Descargando audio desde: {audio_url}")
        audio_bytes = await evolution_client.download_media(audio_url)
        
        print(f"✅ Audio descargado exitosamente")
        print(f"   Tamaño: {len(audio_bytes)} bytes ({len(audio_bytes)/1024:.2f} KB)")
        print(f"   Primeros 20 bytes: {audio_bytes[:20].hex()}")
        
        # Verificar si es audio válido
        is_ogg = audio_bytes[:4] == b'OggS'
        is_mp3 = audio_bytes[:2] == b'\xff\xfb' or audio_bytes[:2] == b'\xff\xf3'
        is_wav = audio_bytes[:4] == b'RIFF'
        
        print(f"\n📊 Formato detectado:")
        print(f"   Es OGG: {is_ogg}")
        print(f"   Es MP3: {is_mp3}")
        print(f"   Es WAV: {is_wav}")
        
        if not (is_ogg or is_mp3 or is_wav):
            print("⚠️  ADVERTENCIA: El archivo no parece ser un formato de audio válido")
        
        # Guardar archivo temporalmente
        temp_file = "/tmp/test_audio.ogg"
        with open(temp_file, "wb") as f:
            f.write(audio_bytes)
        print(f"\n💾 Audio guardado temporalmente en: {temp_file}")
        
        return audio_bytes
        
    except Exception as e:
        print(f"❌ Error al descargar audio: {e}")
        import traceback
        print(traceback.format_exc())
        return None


async def test_audio_transcription(audio_bytes: bytes, mime_type: str = "audio/ogg"):
    """Probar transcripción con Gemini"""
    print("\n" + "="*60)
    print("🤖 TEST 2: TRANSCRIBIR AUDIO CON GEMINI")
    print("="*60)
    
    try:
        gemini_client = GeminiClient(
            api_key=settings.GEMINI_API_KEY,
            model="gemini-1.5-flash",  # Modelo completo, no lite
        )
        
        print(f"📝 Transcribiendo con:")
        print(f"   Modelo: gemini-1.5-flash")
        print(f"   Mime type: {mime_type}")
        print(f"   Tamaño audio: {len(audio_bytes)} bytes")
        
        # Probar con diferentes prompts
        prompts_to_test = [
            # Prompt actual
            {
                "name": "Prompt Original",
                "context": {"trip_status": "en_transito"}
            },
            # Prompt simplificado
            {
                "name": "Prompt Simplificado",
                "context": None
            },
        ]
        
        for i, prompt_config in enumerate(prompts_to_test, 1):
            print(f"\n--- Test {i}: {prompt_config['name']} ---")
            try:
                transcription = await gemini_client.transcribe_audio(
                    audio_bytes,
                    mime_type=mime_type,
                    context=prompt_config["context"]
                )
                print(f"✅ Transcripción exitosa:")
                print(f"   Longitud: {len(transcription)} caracteres")
                print(f"   Texto: {transcription}")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                print(traceback.format_exc())
        
    except Exception as e:
        print(f"❌ Error general en transcripción: {e}")
        import traceback
        print(traceback.format_exc())


async def test_with_simple_audio():
    """Test con un audio simple de prueba"""
    print("\n" + "="*60)
    print("🎤 TEST 3: TRANSCRIPCIÓN DIRECTA CON GEMINI")
    print("="*60)
    
    try:
        gemini_client = GeminiClient(
            api_key=settings.GEMINI_API_KEY,
            model="gemini-1.5-flash",
        )
        
        # Crear un prompt más directo
        import google.generativeai as genai
        import base64
        
        # Intentar con el audio descargado
        temp_file = "/tmp/test_audio.ogg"
        if os.path.exists(temp_file):
            with open(temp_file, "rb") as f:
                audio_bytes = f.read()
            
            print(f"📝 Probando transcripción directa...")
            print(f"   Usando prompt super simplificado")
            
            # Probar con diferentes prompts
            test_prompts = [
                "Transcribe este audio en español.",
                "¿Qué dice este audio? Transcríbelo exactamente.",
                "Transcribe el siguiente mensaje de voz de un conductor de camión en español. Solo devuelve el texto transcrito.",
            ]
            
            for i, prompt_text in enumerate(test_prompts, 1):
                print(f"\n--- Prompt {i}: {prompt_text[:50]}... ---")
                try:
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    audio_part = {
                        "inline_data": {
                            "mime_type": "audio/ogg",
                            "data": audio_base64
                        }
                    }
                    
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    response = model.generate_content(
                        [prompt_text, audio_part],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=512,
                        ),
                    )
                    
                    transcription = response.text.strip()
                    print(f"✅ Transcripción: {transcription}")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
        else:
            print("⚠️  No se encontró archivo de audio de prueba")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())


async def main():
    """Función principal"""
    print("\n" + "🔍 "*20)
    print("DIAGNÓSTICO DE TRANSCRIPCIÓN DE AUDIO")
    print("🔍 "*20)
    
    # Obtener URL de audio de argumento o usar una de prueba
    if len(sys.argv) > 1:
        audio_url = sys.argv[1]
        print(f"\n📍 Usando URL de audio proporcionada: {audio_url}")
    else:
        print("\n⚠️  No se proporcionó URL de audio")
        print("Uso: python scripts/debug_audio_transcription.py <audio_url>")
        print("\nPuedes obtener la URL del audio desde los logs del servidor.")
        return
    
    # Test 1: Descargar audio
    audio_bytes = await test_audio_download(audio_url)
    
    if audio_bytes:
        # Test 2: Transcribir con diferentes configuraciones
        await test_audio_transcription(audio_bytes)
        
        # Test 3: Transcripción directa
        await test_with_simple_audio()
    
    print("\n" + "="*60)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("="*60)
    print("\nRevisa los resultados arriba para identificar el problema.")
    print("Si todas las transcripciones están incorrectas, el problema puede ser:")
    print("  1. El audio está corrupto o en formato incompatible")
    print("  2. El modelo Gemini no puede procesar este tipo de audio")
    print("  3. Hay un problema con la configuración de la API Key")


if __name__ == "__main__":
    asyncio.run(main())

