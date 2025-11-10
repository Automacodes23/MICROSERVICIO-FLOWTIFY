#!/usr/bin/env python3
"""
Evolution API - Ejemplo Práctico de Verificación de Mensajes
============================================================

Este ejemplo muestra una implementación completa usando la librería 
cliente-evolution-api para verificar si los mensajes se entregan correctamente.
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from cliente_evolution_api import ClientEvolutionAPI
from flask import Flask, request, jsonify

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MessageDeliveryTracker:
    """Tracker completo para verificar entrega de mensajes"""
    
    def __init__(self, api_url: str, api_key: str, instance_name: str):
        """
        Inicializar el tracker de entrega
        
        Args:
            api_url: URL de tu Evolution API
            api_key: Tu API key
            instance_name: Nombre de la instancia
        """
        self.api_url = api_url
        self.api_key = api_key
        self.instance_name = instance_name
        
        # Inicializar cliente Evolution API
        self.client = ClientEvolutionAPI(
            base_url=api_url,
            api_key=api_key
        )
        
        # Almacenamiento de mensajes enviados
        self.sent_messages: Dict[str, dict] = {}
        
        # Estado de callbacks registrados
        self.callbacks_registered = False
    
    async def send_text_message_with_tracking(self, phone_number: str, content: str) -> Optional[str]:
        """
        Envía un mensaje de texto y configura el tracking
        
        Args:
            phone_number: Número de teléfono
            content: Contenido del mensaje
            
        Returns:
            ID del mensaje para tracking
        """
        try:
            # Enviar mensaje usando el cliente Evolution API
            response = await self.client.message.send_text(
                instance_name=self.instance_name,
                number=phone_number,
                text=content
            )
            
            # Extraer ID del mensaje
            message_id = response.get('key', {}).get('id')
            if not message_id:
                logger.error("No se pudo obtener el ID del mensaje")
                return None
            
            # Guardar información del mensaje
            self.sent_messages[message_id] = {
                'phone_number': phone_number,
                'content': content,
                'sent_time': datetime.now().isoformat(),
                'status': 'PENDING',
                'delivery_time': None,
                'read_time': None,
                'failed_time': None
            }
            
            logger.info(f"Mensaje enviado - ID: {message_id}, Destino: {phone_number}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return None
    
    async def check_whatsapp_number(self, phone_number: str) -> bool:
        """
        Verifica si un número tiene WhatsApp activo
        
        Args:
            phone_number: Número a verificar
            
        Returns:
            True si el número tiene WhatsApp
        """
        try:
            response = await self.client.chat.check_is_whatsapp(
                instance_name=self.instance_name,
                number=phone_number
            )
            return response.get('existsWhatsApp', False)
        except Exception as e:
            logger.error(f"Error verificando número: {e}")
            return False
    
    async def configure_webhooks(self, webhook_url: str) -> bool:
        """
        Configura webhooks para recibir actualizaciones de estado
        
        Args:
            webhook_url: URL donde recibir webhooks
            
        Returns:
            True si se configuró correctamente
        """
        try:
            # Configurar webhook en la instancia
            await self.client.webhook.set_webhook(
                instance_name=self.instance_name,
                webhook={
                    'url': webhook_url,
                    'webhook_by_events': True,
                    'events': [
                        'MESSAGES_UPSERT',      # Mensajes recibidos
                        'MESSAGES_UPDATE',      # Actualizaciones de mensajes (estados)
                        'SEND_MESSAGE',         # Mensajes enviados
                        'MESSAGES_DELETE'       # Mensajes eliminados
                    ]
                }
            )
            
            self.callbacks_registered = True
            logger.info(f"Webhooks configurados en: {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error configurando webhooks: {e}")
            return False
    
    def update_message_status(self, message_id: str, new_status: str, event_data: dict):
        """
        Actualiza el estado de un mensaje desde webhook/WebSocket
        
        Args:
            message_id: ID del mensaje
            new_status: Nuevo estado (PENDING, SENT, DELIVERED, READ, FAILED)
            event_data: Datos completos del evento
        """
        if message_id not in self.sent_messages:
            logger.warning(f"Mensaje {message_id} no encontrado en tracking")
            return
        
        message_info = self.sent_messages[message_id]
        old_status = message_info['status']
        message_info['status'] = new_status
        message_info['last_update'] = datetime.now().isoformat()
        
        # Registrar timestamps específicos
        if new_status == 'DELIVERED' and not message_info['delivery_time']:
            message_info['delivery_time'] = datetime.now().isoformat()
            logger.info(f"📨 MENSAJE ENTREGADO - ID: {message_id} - Destino: {message_info['phone_number']}")
            
        elif new_status == 'READ' and not message_info['read_time']:
            message_info['read_time'] = datetime.now().isoformat()
            logger.info(f"👁️ MENSAJE LEÍDO - ID: {message_id} - Destino: {message_info['phone_number']}")
            
        elif new_status == 'FAILED':
            message_info['failed_time'] = datetime.now().isoformat()
            logger.error(f"❌ MENSAJE FALLÓ - ID: {message_id} - Destino: {message_info['phone_number']}")
        
        logger.info(f"Estado actualizado: {message_id} - {old_status} → {new_status}")
    
    def get_message_status(self, message_id: str) -> Optional[dict]:
        """Obtiene el estado actual de un mensaje"""
        return self.sent_messages.get(message_id)
    
    def get_delivery_statistics(self) -> dict:
        """Obtiene estadísticas de entrega de todos los mensajes"""
        stats = {'PENDING': 0, 'SENT': 0, 'DELIVERED': 0, 'READ': 0, 'FAILED': 0}
        
        for message in self.sent_messages.values():
            status = message['status']
            if status in stats:
                stats[status] += 1
        
        return stats
    
    def get_delivery_summary(self) -> str:
        """Genera un resumen de entrega legible"""
        stats = self.get_delivery_statistics()
        total = sum(stats.values())
        
        if total == 0:
            return "No hay mensajes para mostrar estadísticas."
        
        summary = f"📊 RESUMEN DE ENTREGA (Total: {total} mensajes)\n"
        summary += f"  ⏳ Pendientes: {stats['PENDING']}\n"
        summary += f"  📤 Enviados: {stats['SENT']}\n"
        summary += f"  📨 Entregados: {stats['DELIVERED']}\n"
        summary += f"  👁️ Leídos: {stats['READ']}\n"
        summary += f"  ❌ Fallidos: {stats['FAILED']}\n"
        
        # Calcular porcentaje de entrega exitosa
        successful = stats['DELIVERED'] + stats['READ']
        if total > 0:
            percentage = (successful / total) * 100
            summary += f"\n🎯 Tasa de entrega exitosa: {percentage:.1f}%"
        
        return summary

# Servidor Webhook Flask
def create_webhook_app(tracker: MessageDeliveryTracker) -> Flask:
    """Crea una aplicación Flask para recibir webhooks"""
    app = Flask(__name__)
    
    @app.route('/webhook/messages-update', methods=['POST'])
    def webhook_messages_update():
        """Webhook para actualizaciones de estado de mensajes"""
        try:
            data = request.get_json()
            logger.info(f"Webhook recibido: {json.dumps(data, indent=2)}")
            
            # Procesar actualización de mensaje
            if 'messages' in data and data['messages']:
                for message in data['messages']:
                    message_id = message.get('key', {}).get('id')
                    status = message.get('status', 'PENDING')
                    
                    if message_id:
                        tracker.update_message_status(message_id, status, message)
            
            return jsonify({'status': 'ok'}), 200
            
        except Exception as e:
            logger.error(f"Error procesando webhook: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/webhook/status', methods=['GET'])
    def webhook_status():
        """Endpoint para verificar estado del webhook"""
        return jsonify({
            'status': 'active',
            'messages_tracked': len(tracker.sent_messages),
            'timestamp': datetime.now().isoformat()
        })
    
    return app

async def ejemplo_completo():
    """Ejemplo completo de uso del sistema de tracking"""
    
    # Configuración
    EVOLUTION_API_URL = "http://localhost:8080"
    API_KEY = "tu_api_key_aqui"
    INSTANCE_NAME = "mi_instancia"
    WEBHOOK_URL = "http://localhost:5000"
    
    # Inicializar tracker
    tracker = MessageDeliveryTracker(EVOLUTION_API_URL, API_KEY, INSTANCE_NAME)
    
    print("🚀 EVOLUTION API - VERIFICACIÓN DE ENTREGA DE MENSAJES")
    print("=" * 60)
    
    # Verificar número antes de enviar
    phone_number = "5212345678900"  # Reemplaza con un número real
    print(f"🔍 Verificando si el número {phone_number} tiene WhatsApp...")
    
    is_valid = await tracker.check_whatsapp_number(phone_number)
    if not is_valid:
        print(f"❌ El número {phone_number} no tiene WhatsApp activo")
        return
    
    print(f"✅ El número {phone_number} tiene WhatsApp activo")
    
    # Configurar webhooks
    print(f"🔗 Configurando webhooks en {WEBHOOK_URL}...")
    webhook_configured = await tracker.configure_webhooks(WEBHOOK_URL)
    if not webhook_configured:
        print("❌ Error configurando webhooks")
        return
    
    print("✅ Webhooks configurados correctamente")
    
    # Enviar mensajes de prueba
    test_messages = [
        "Hola, este es un mensaje de prueba 📱",
        "Este mensaje verificará la entrega ✅",
        "¿Recibiste este mensaje? 🤔"
    ]
    
    sent_message_ids = []
    
    for i, message_content in enumerate(test_messages, 1):
        print(f"\n📤 Enviando mensaje {i}/3...")
        
        message_id = await tracker.send_text_message_with_tracking(phone_number, message_content)
        if message_id:
            sent_message_ids.append(message_id)
            print(f"✅ Mensaje enviado - ID: {message_id}")
        else:
            print("❌ Error enviando mensaje")
        
        # Pequeña pausa entre mensajes
        await asyncio.sleep(1)
    
    print(f"\n📊 {len(sent_message_ids)} mensajes enviados con tracking activo")
    print("⏳ Monitoreando estados de mensajes...")
    
    # Simular monitoreo por 30 segundos
    for second in range(30, 0, -5):
        await asyncio.sleep(5)
        
        # Mostrar estadísticas actuales
        print(f"\n⏰ Tiempo restante: {second} segundos")
        print(tracker.get_delivery_summary())
    
    # Resumen final
    print("\n" + "=" * 60)
    print("🎯 RESUMEN FINAL")
    print("=" * 60)
    print(tracker.get_delivery_summary())
    
    # Mostrar detalles de cada mensaje
    print("\n📋 DETALLES DE MENSAJES:")
    for message_id in sent_message_ids:
        message_info = tracker.get_message_status(message_id)
        if message_info:
            print(f"\n  ID: {message_id}")
            print(f"  Destino: {message_info['phone_number']}")
            print(f"  Estado: {message_info['status']}")
            print(f"  Enviado: {message_info['sent_time']}")
            if message_info['delivery_time']:
                print(f"  Entregado: {message_info['delivery_time']}")
            if message_info['read_time']:
                print(f"  Leído: {message_info['read_time']}")
            if message_info['failed_time']:
                print(f"  Falló: {message_info['failed_time']}")

# Función para iniciar el servidor webhook en un hilo separado
def start_webhook_server(tracker: MessageDeliveryTracker, port: int = 5000):
    """Inicia el servidor webhook en un hilo separado"""
    app = create_webhook_app(tracker)
    logger.info(f"Iniciando servidor webhook en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    import threading
    
    # Crear tracker
    tracker = MessageDeliveryTracker("http://localhost:8080", "tu_api_key", "mi_instancia")
    
    # Iniciar servidor webhook en hilo separado
    webhook_thread = threading.Thread(
        target=start_webhook_server, 
        args=(tracker, 5000)
    )
    webhook_thread.daemon = True
    webhook_thread.start()
    
    print("Servidor webhook iniciado en http://localhost:5000")
    print("Ejecutando ejemplo de tracking...")
    
    # Ejecutar ejemplo
    asyncio.run(ejemplo_completo())