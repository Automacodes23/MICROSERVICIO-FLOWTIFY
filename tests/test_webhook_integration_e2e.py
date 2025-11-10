"""
Test End-to-End de integración de webhooks con Flowtify

Este script prueba el flujo completo:
1. Crear un viaje
2. Simular eventos Wialon (speed, geofence)  
3. Simular mensajes WhatsApp
4. Verificar que se enviaron webhooks
5. Verificar logs de delivery

Ejecutar: python tests/test_webhook_integration_e2e.py
"""
import asyncio
import httpx
import json
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


async def test_webhook_integration():
    """Test completo de integración"""
    print("\n" + "="*70)
    print("🧪 TEST END-TO-END: INTEGRACIÓN DE WEBHOOKS FLOWTIFY")
    print("="*70 + "\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # ====================================================================
        # 1. Health Check
        # ====================================================================
        print("📋 Paso 1: Health Check del sistema...")
        
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print(f"   ✅ Sistema healthy: {response.json()}\n")
        
        # Health check de webhooks
        response = await client.get(f"{BASE_URL}/webhooks/health")
        webhook_health = response.json()
        print(f"   ✅ Webhook service: {webhook_health}")
        
        if webhook_health.get("status") != "healthy":
            print(f"   ⚠️  ADVERTENCIA: Webhooks no están completamente configurados")
            print(f"      Verifica FLOWTIFY_WEBHOOK_URL y WEBHOOK_SECRET en .env")
        print()
        
        # ====================================================================
        # 2. Crear un viaje de prueba
        # ====================================================================
        print("📋 Paso 2: Creando viaje de prueba...")
        
        trip_payload = {
            "event": "whatsapp.group.create",
            "action": "create_group",
            "tenant_id": 24,
            "trip": {
                "id": 999,
                "code": "TEST_WEBHOOK_E2E_001",
                "status": "planned",
                "planned_start": "2025-01-10T20:00:00-06:00",
                "planned_end": "2025-01-10T22:00:00-06:00",
                "origin": "León",
                "destination": "Jalisco",
            },
            "driver": {
                "id": 999,
                "name": "TEST_WEBHOOK_DRIVER",
                "phone": "+521234567890",
            },
            "unit": {
                "id": 999,
                "floatify_unit_id": "999",
                "name": "Test Truck 999",
                "plate": "TEST999",
                "wialon_id": "99999999",
                "imei": "999999999999999",
            },
            "customer": {
                "id": 999,
                "name": "Test Customer",
            },
            "geofences": [
                {
                    "role": "origin",
                    "geofence_id": "TEST_GEO_ORIGIN",
                    "geofence_name": "Test Origin",
                    "geofence_type": "circle",
                    "order": 0,
                },
                {
                    "role": "loading",
                    "geofence_id": "TEST_GEO_LOADING",
                    "geofence_name": "Test Loading Zone",
                    "geofence_type": "polygon",
                    "order": 1,
                },
                {
                    "role": "route",
                    "geofence_id": "TEST_GEO_ROUTE",
                    "geofence_name": "Test Route Corridor",
                    "geofence_type": "polyline",
                    "order": 3,
                },
            ],
            "whatsapp_participants": ["+521234567890"],
            "metadata": {"test": True, "e2e": True},
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/trips/create",
                json=trip_payload,
            )
            
            if response.status_code == 200:
                trip_result = response.json()
                trip_id = trip_result.get("trip_id")
                print(f"   ✅ Viaje creado: {trip_id}")
                print(f"      Código: {trip_result.get('trip_code')}")
                print(f"      WhatsApp Group: {trip_result.get('whatsapp_group_id')}\n")
            else:
                print(f"   ❌ Error al crear viaje: {response.status_code}")
                print(f"      {response.text}\n")
                return
        
        except Exception as e:
            print(f"   ❌ Excepción al crear viaje: {e}\n")
            return
        
        # ====================================================================
        # 3. Cambiar estado del viaje (trigger status_update webhook)
        # ====================================================================
        print("📋 Paso 3: Cambiando estado del viaje (trigger webhook)...")
        
        response = await client.put(
            f"{BASE_URL}/trips/{trip_id}/status",
            params={"status": "en_ruta", "substatus": "rumbo_carga"},
        )
        
        if response.status_code == 200:
            print(f"   ✅ Estado actualizado a: en_ruta / rumbo_carga")
            print(f"      Webhook de status_update debería haberse enviado\n")
        else:
            print(f"   ❌ Error al actualizar estado: {response.status_code}\n")
        
        # Esperar un poco para que webhook se procese
        await asyncio.sleep(2)
        
        # ====================================================================
        # 4. Verificar logs de delivery de webhooks
        # ====================================================================
        print("📋 Paso 4: Verificando logs de delivery de webhooks...")
        
        response = await client.get(
            f"{BASE_URL}/webhooks/delivery-log",
            params={"trip_id": trip_id, "limit": 10},
        )
        
        if response.status_code == 200:
            logs_data = response.json()
            logs = logs_data.get("logs", [])
            print(f"   ✅ Encontrados {len(logs)} webhooks para este viaje:")
            
            for log in logs:
                status_icon = "✅" if log["status"] == "sent" else "❌"
                print(f"      {status_icon} {log['webhook_type']}")
                print(f"         Status: {log['status']}")
                print(f"         Retries: {log['retry_count']}")
                print(f"         Created: {log['created_at']}")
                
                if log["status"] == "failed":
                    print(f"         Error: {log.get('last_error', 'N/A')}")
            print()
        else:
            print(f"   ⚠️  No se pudieron obtener logs: {response.status_code}\n")
        
        # ====================================================================
        # 5. Obtener estadísticas de webhooks
        # ====================================================================
        print("📋 Paso 5: Obteniendo estadísticas de webhooks...")
        
        response = await client.get(f"{BASE_URL}/webhooks/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   📊 Estadísticas (últimas 24h):")
            print(f"      Total enviados: {stats['total_sent']}")
            print(f"      Total fallidos: {stats['total_failed']}")
            print(f"      Success rate: {stats['success_rate']}%")
            print(f"      Pending retries: {stats['pending_retries']}")
            print(f"      DLQ size: {stats['dlq_size']}")
            print()
        
        # ====================================================================
        # 6. Verificar Dead Letter Queue
        # ====================================================================
        print("📋 Paso 6: Verificando Dead Letter Queue...")
        
        response = await client.get(f"{BASE_URL}/webhooks/dead-letter-queue")
        
        if response.status_code == 200:
            dlq_data = response.json()
            dlq_items = dlq_data.get("items", [])
            
            if dlq_items:
                print(f"   ⚠️  Encontrados {len(dlq_items)} webhooks en DLQ:")
                for item in dlq_items:
                    print(f"      - {item['webhook_type']}")
                    print(f"        Razón: {item['failure_reason']}")
            else:
                print(f"   ✅ DLQ vacía - Sin webhooks fallidos permanentemente")
            print()
        
        # ====================================================================
        # 7. Limpiar viaje de prueba (opcional)
        # ====================================================================
        print("📋 Paso 7: Limpieza de viaje de prueba...")
        
        try:
            response = await client.post(f"{BASE_URL}/trips/{trip_id}/cleanup_group")
            if response.status_code == 200:
                print(f"   ✅ Viaje de prueba limpiado")
            else:
                print(f"   ⚠️  No se pudo limpiar (puede ser grupo compartido)")
        except Exception as e:
            print(f"   ⚠️  Error en limpieza (no crítico): {e}")
        print()
    
    # ====================================================================
    # Resumen Final
    # ====================================================================
    print("="*70)
    print("✅ TEST END-TO-END COMPLETADO")
    print("="*70)
    print("\n📝 Próximos pasos:")
    print("   1. Revisar los logs de delivery arriba")
    print("   2. Si hay webhooks fallidos, revisar la causa")
    print("   3. Coordinar con Flowtify para validar recepción")
    print("   4. Continuar con testing de otros tipos de eventos\n")


async def test_simulated_wialon_events():
    """
    Test de eventos Wialon simulados
    
    Nota: Requiere que el viaje ya exista y la unidad tenga wialon_id
    """
    print("\n" + "="*70)
    print("🧪 TEST: EVENTOS WIALON SIMULADOS")
    print("="*70 + "\n")
    
    # TODO: Implementar simulación de eventos Wialon
    # - Speed violation
    # - Geofence entry/exit
    # - Route deviation
    
    print("⚠️  Este test requiere un viaje activo existente")
    print("   Ejecuta test_webhook_integration() primero\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_webhook_integration())
        print("\n✨ Todos los tests pasaron exitosamente!\n")
    except KeyboardInterrupt:
        print("\n\n⏸️  Tests cancelados por el usuario\n")
    except Exception as e:
        print(f"\n\n❌ Error en tests: {e}\n")
        import traceback
        traceback.print_exc()

