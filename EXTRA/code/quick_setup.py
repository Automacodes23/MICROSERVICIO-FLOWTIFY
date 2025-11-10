#!/usr/bin/env python3
"""
Evolution API - Configuración Rápida y Ejemplo de Uso
====================================================

Este archivo proporciona una configuración rápida para empezar
a verificar la entrega de mensajes con Evolution API.
"""

import asyncio
import logging
from typing import Optional

# Importar las clases de nuestros archivos anteriores
from evolution_api_complete_tracking import MessageDeliveryTracker, create_webhook_app
from flask import Flask
import threading

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuickSetup:
    """Configuración rápida para Evolution API"""
    
    def __init__(self, config: dict):
        """
        Inicializar configuración rápida
        
        Args:
            config: Diccionario con configuración
        """
        self.config = config
        self.tracker = None
        self.webhook_app = None
        self.webhook_thread = None
    
    def setup(self) -> bool:
        """
        Configurar todo el sistema de tracking
        
        Returns:
            True si la configuración fue exitosa
        """
        try:
            # Crear tracker
            self.tracker = MessageDeliveryTracker(
                api_url=self.config['evolution_api_url'],
                api_key=self.config['api_key'],
                instance_name=self.config['instance_name']
            )
            
            logger.info("✅ Tracker inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en configuración: {e}")
            return False
    
    async def start_webhook_server(self) -> bool:
        """
        Iniciar servidor webhook en hilo separado
        
        Returns:
            True si se inició correctamente
        """
        try:
            if not self.tracker:
                logger.error("❌ No se puede iniciar webhook sin tracker")
                return False
            
            # Crear aplicación Flask
            self.webhook_app = create_webhook_app(self.tracker)
            
            # Iniciar en hilo separado
            self.webhook_thread = threading.Thread(
                target=lambda: self.webhook_app.run(
                    host='0.0.0.0',
                    port=self.config.get('webhook_port', 5000),
                    debug=False
                ),
                daemon=True
            )
            
            self.webhook_thread.start()
            
            logger.info(f"✅ Servidor webhook iniciado en puerto {self.config.get('webhook_port', 5000)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando webhook: {e}")
            return False
    
    async def configure_webhooks(self) -> bool:
        """
        Configurar webhooks en Evolution API
        
        Returns:
            True si se configuró correctamente
        """
        try:
            webhook_url = f"{self.config.get('webhook_base_url', 'http://localhost:5000')}"
            
            success = await self.tracker.configure_webhooks(webhook_url)
            
            if success:
                logger.info("✅ Webhooks configurados correctamente")
                return True
            else:
                logger.error("❌ Error configurando webhooks")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en configuración de webhooks: {e}")
            return False
    
    async def send_test_messages(self) -> list:
        """
        Enviar mensajes de prueba
        
        Returns:
            Lista de IDs de mensajes enviados
        """
        test_messages = [
            "🧪 Mensaje de prueba 1 - Verificando entrega",
            "🧪 Mensaje de prueba 2 - ¿Recibido?",
            "🧪 Mensaje de prueba 3 - Tracking activo"
        ]
        
        sent_ids = []
        
        for i, message in enumerate(test_messages, 1):
            try:
                message_id = await self.tracker.send_text_message_with_tracking(
                    self.config['test_phone_number'],
                    message
                )
                
                if message_id:
                    sent_ids.append(message_id)
                    logger.info(f"✅ Mensaje {i}/3 enviado - ID: {message_id}")
                else:
                    logger.error(f"❌ Error enviando mensaje {i}")
                
                # Pausa entre mensajes
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error enviando mensaje {i}: {e}")
        
        return sent_ids
    
    async def monitor_messages(self, duration_seconds: int = 30) -> None:
        """
        Monitorear mensajes enviados
        
        Args:
            duration_seconds: Duración del monitoreo en segundos
        """
        logger.info(f"⏳ Monitoreando mensajes por {duration_seconds} segundos...")
        
        check_interval = 5  # Verificar cada 5 segundos
        checks = duration_seconds // check_interval
        
        for i in range(checks):
            await asyncio.sleep(check_interval)
            
            # Mostrar estadísticas actuales
            stats = self.tracker.get_delivery_statistics()
            
            print(f"\n📊 Verificación {i+1}/{checks}")
            print(f"   ⏳ Pendientes: {stats['PENDING']}")
            print(f"   📤 Enviados: {stats['SENT']}")
            print(f"   📨 Entregados: {stats['DELIVERED']}")
            print(f"   👁️ Leídos: {stats['READ']}")
            print(f"   ❌ Fallidos: {stats['FAILED']}")
            
            # Si no hay mensajes pendientes, terminar
            total_pending = stats['PENDING'] + stats['SENT']
            if total_pending == 0:
                logger.info("✅ Todos los mensajes han recibido confirmación de estado")
                break
    
    def show_final_summary(self) -> None:
        """Mostrar resumen final de la sesión"""
        if not self.tracker:
            return
        
        print("\n" + "="*60)
        print("🎯 RESUMEN FINAL DE LA SESIÓN")
        print("="*60)
        
        # Estadísticas generales
        print(self.tracker.get_delivery_summary())
        
        # Información de la sesión
        total_messages = len(self.tracker.sent_messages)
        print(f"\n📋 Total de mensajes monitoreados: {total_messages}")
        
        # URLs de webhook activas
        webhook_url = f"{self.config.get('webhook_base_url', 'http://localhost:5000')}"
        print(f"🔗 Webhooks configurados en: {webhook_url}")
        print(f"📡 Servidor webhook activo en: http://localhost:{self.config.get('webhook_port', 5000)}")
        
        # Instrucciones para continuar
        print("\n💡 INSTRUCCIONES:")
        print("  1. Los webhooks están configurados y activos")
        print("  2. Envía más mensajes usando: await tracker.send_text_message_with_tracking()")
        print("  3. Monitorea estados con: tracker.get_message_status()")
        print("  4. Revisa logs para debug: cat /tmp/evolution_tracking.log")

async def main():
    """Función principal - Configuración y prueba rápida"""
    
    # 🔧 CONFIGURACIÓN - MODIFICA ESTOS VALORES
    config = {
        'evolution_api_url': 'http://localhost:8080',
        'api_key': 'TU_API_KEY_AQUI',  # 🔴 CAMBIAR
        'instance_name': 'mi_instancia',  # 🔴 CAMBIAR
        'test_phone_number': '5212345678900',  # 🔴 CAMBIAR al número real
        'webhook_base_url': 'http://localhost:5000',
        'webhook_port': 5000
    }
    
    print("🚀 EVOLUTION API - CONFIGURACIÓN RÁPIDA")
    print("="*50)
    print("📋 Configuración:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    print("\n⚠️  IMPORTANTE: Modifica los valores marcados con 🔴")
    
    # Crear configuración rápida
    quick_setup = QuickSetup(config)
    
    # Paso 1: Configurar sistema
    print("\n🔧 Paso 1: Configurando sistema...")
    if not quick_setup.setup():
        print("❌ Error en configuración. Revisa la configuración.")
        return
    
    # Paso 2: Iniciar servidor webhook
    print("\n🌐 Paso 2: Iniciando servidor webhook...")
    if not await quick_setup.start_webhook_server():
        print("❌ Error iniciando webhook. Revisa la configuración.")
        return
    
    await asyncio.sleep(2)  # Esperar que el servidor se inicie
    
    # Paso 3: Configurar webhooks en Evolution API
    print("\n🔗 Paso 3: Configurando webhooks en Evolution API...")
    if not await quick_setup.configure_webhooks():
        print("❌ Error configurando webhooks. Verifica la API de Evolution.")
        return
    
    # Paso 4: Verificar número de WhatsApp
    print(f"\n🔍 Paso 4: Verificando número {config['test_phone_number']}...")
    try:
        is_valid = await quick_setup.tracker.check_whatsapp_number(config['test_phone_number'])
        if not is_valid:
            print(f"❌ El número {config['test_phone_number']} no tiene WhatsApp activo")
            print("💡 Cambia el número en la configuración y vuelve a intentar")
            return
        
        print("✅ Número válido con WhatsApp activo")
        
    except Exception as e:
        print(f"❌ Error verificando número: {e}")
        print("💡 Verifica que Evolution API esté ejecutándose correctamente")
        return
    
    # Paso 5: Enviar mensajes de prueba
    print("\n📤 Paso 5: Enviando mensajes de prueba...")
    sent_message_ids = await quick_setup.send_test_messages()
    
    if not sent_message_ids:
        print("❌ No se enviaron mensajes correctamente")
        return
    
    print(f"✅ {len(sent_message_ids)} mensajes enviados con tracking activo")
    
    # Paso 6: Monitorear estados
    print("\n📊 Paso 6: Monitoreando estados de mensajes...")
    await quick_setup.monitor_messages(duration_seconds=30)
    
    # Paso 7: Resumen final
    print("\n🎉 Paso 7: Resumen final")
    quick_setup.show_final_summary()
    
    # Mantener servidor activo
    print("\n🔄 Servidor webhook seguirá activo. Presiona Ctrl+C para salir.")
    try:
        while True:
            await asyncio.sleep(10)
            # Mostrar estadísticas cada 10 segundos
            quick_setup.show_final_summary()
    except KeyboardInterrupt:
        print("\n👋 Saliendo... ¡Gracias por usar Evolution API Tracking!")

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import cliente_evolution_api
        import flask
        print("✅ Dependencias verificadas")
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        exit(1)
    
    # Ejecutar configuración rápida
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print("💡 Revisa la configuración y los logs para más detalles")