# Plan de Implementación: Detección de Desviación de Ruta mediante Geocercas

## Resumen

Este plan describe los cambios necesarios para implementar la detección automática de desviación de ruta cuando un vehículo sale de una geocerca con role "route".

## Archivos a Modificar

### 1. `app/core/constants.py`
- **Cambio**: Agregar "route" a `GEOFENCE_ROLES`
- **Cambio**: Agregar constante `ROUTE_DEVIATION_GRACE_PERIOD = 300`
- **Impacto**: Bajo - Solo agregar constantes

### 2. `app/config.py`
- **Cambio**: Agregar `route_deviation_grace_period: int = 300` a la clase `Settings`
- **Impacto**: Bajo - Solo agregar configuración

### 3. `app/services/event_service.py`
- **Cambio**: Agregar detección de salida de geocerca de ruta en `_determine_action()`
- **Cambio**: Agregar período de gracia para notificaciones
- **Cambio**: Agregar envío de webhook `route_deviation` en `_send_webhooks_for_event()`
- **Impacto**: Medio - Modificar lógica existente

## Secuencia de Implementación

### Fase 1: Preparación (10 minutos)

1. **Actualizar Constantes**
   - Agregar "route" a `GEOFENCE_ROLES` en `constants.py`
   - Agregar `ROUTE_DEVIATION_GRACE_PERIOD = 300` en `constants.py`

2. **Actualizar Configuración**
   - Agregar `route_deviation_grace_period: int = 300` a `Settings` en `config.py`

### Fase 2: Implementación de Detección (45 minutos)

3. **Actualizar EventService - Detección**
   - Agregar atributo `_route_deviation_notifications = {}` en `__init__`
   - Agregar método `_check_grace_period()`
   - Agregar método `_cleanup_old_notifications()`
   - Actualizar `_determine_action()` para detectar salida de geocerca de ruta
   - Agregar lógica de período de gracia en `_determine_action()`

### Fase 3: Implementación de Webhooks (25 minutos)

4. **Actualizar EventService - Webhooks**
   - Actualizar consulta para obtener `geofence_type` desde BD (usar `fetchrow` en lugar de `fetchval`)
   - Actualizar `_send_webhooks_for_event()` para enviar webhook `route_deviation`
   - Agregar lógica para detectar geocerca de ruta en `_send_webhooks_for_event()`
   - Agregar manejo de errores para no afectar envío de `geofence_transition`

### Fase 4: Testing (45 minutos)

5. **Tests Unitarios**
   - Test de detección de desviación de ruta
   - Test de período de gracia
   - Test de envío de webhook `route_deviation`

6. **Tests de Integración**
   - Test de flujo completo desde evento Wialon hasta webhook
   - Test de período de gracia con múltiples eventos
   - Test de fallback a detección por nombre

### Fase 5: Verificación (20 minutos)

7. **Verificación Manual**
   - Crear viaje de prueba con geocerca de ruta
   - Simular evento `geofence_exit` para geocerca de ruta
   - Verificar que se envía notificación WhatsApp
   - Verificar que se envían ambos webhooks
   - Verificar que NO se cambia el estado del viaje
   - Verificar que el período de gracia funciona correctamente
   - Verificar que `geofence_type` se obtiene correctamente desde BD
   - Verificar criterios de éxito medibles (100% detección, <2s procesamiento)
   - Verificar criterios cualitativos (claridad de notificaciones, integración consistente)

## Cambios Detallados

### Cambio 1: Actualizar Constantes

**Archivo**: `app/core/constants.py`

**Línea**: ~40-47

**Cambio**:
```python
# Roles de geocercas
GEOFENCE_ROLES = {
    "ORIGIN": "origin",
    "LOADING": "loading",
    "UNLOADING": "unloading",
    "WAYPOINT": "waypoint",
    "DEPOT": "depot",
    "ROUTE": "route",  # NUEVO
}

# Período de gracia para notificaciones de desviación de ruta (en segundos)
ROUTE_DEVIATION_GRACE_PERIOD = 300  # 5 minutos
```

---

### Cambio 2: Actualizar Configuración

**Archivo**: `app/config.py`

**Línea**: ~86 (después de `webhooks_enabled_tenants`)

**Cambio**:
```python
# Período de gracia para notificaciones de desviación de ruta (en segundos)
route_deviation_grace_period: int = 300  # 5 minutos por defecto
```

---

### Cambio 3: Actualizar EventService - __init__

**Archivo**: `app/services/event_service.py`

**Línea**: ~33 (después de `self.webhook_service = webhook_service`)

**Cambio**:
```python
self.webhook_service = webhook_service

# Tracking de notificaciones de desviación de ruta para período de gracia
self._route_deviation_notifications = {}  # {trip_id: {"last_notification_time": timestamp}}
```

---

### Cambio 4: Agregar Método _check_grace_period

**Archivo**: `app/services/event_service.py`

**Ubicación**: Después de `__init__` (antes de `process_wialon_event`)

**Cambio**:
```python
def _check_grace_period(self, trip_id: str, grace_period_seconds: int = 300) -> bool:
    """
    Verificar si han pasado suficientes segundos desde la última notificación de desviación
    
    Args:
        trip_id: ID del viaje
        grace_period_seconds: Período de gracia en segundos (default: 5 minutos)
    
    Returns:
        True si se puede enviar notificación, False si está en período de gracia
    """
    import time
    
    # Limpiar entradas antiguas (cada hora)
    self._cleanup_old_notifications(max_age_seconds=3600)
    
    current_time = time.time()
    
    if trip_id not in self._route_deviation_notifications:
        # Primera notificación para este viaje
        self._route_deviation_notifications[trip_id] = {
            "last_notification_time": current_time
        }
        logger.info(
            "route_deviation_notification_allowed",
            trip_id=trip_id,
            reason="first_notification"
        )
        return True
    
    last_notification_time = self._route_deviation_notifications[trip_id]["last_notification_time"]
    time_since_last = current_time - last_notification_time
    
    if time_since_last >= grace_period_seconds:
        # Período de gracia expirado, actualizar timestamp
        self._route_deviation_notifications[trip_id]["last_notification_time"] = current_time
        logger.info(
            "route_deviation_notification_allowed",
            trip_id=trip_id,
            reason="grace_period_expired",
            time_since_last=time_since_last
        )
        return True
    else:
        # Período de gracia activo
        logger.info(
            "route_deviation_notification_blocked",
            trip_id=trip_id,
            reason="grace_period_active",
            time_since_last=time_since_last,
            grace_period_seconds=grace_period_seconds
        )
        return False

def _cleanup_old_notifications(self, max_age_seconds: int = 3600):
    """
    Limpiar entradas antiguas del tracking de notificaciones
    
    Args:
        max_age_seconds: Edad máxima en segundos (default: 1 hora)
    """
    import time
    
    current_time = time.time()
    trips_to_remove = []
    
    for trip_id, data in self._route_deviation_notifications.items():
        age = current_time - data["last_notification_time"]
        if age > max_age_seconds:
            trips_to_remove.append(trip_id)
    
    for trip_id in trips_to_remove:
        del self._route_deviation_notifications[trip_id]
    
    if trips_to_remove:
        logger.info(
            "route_deviation_notifications_cleaned",
            count=len(trips_to_remove)
        )
```

---

### Cambio 5: Actualizar _determine_action - Detección de Desviación

**Archivo**: `app/services/event_service.py`

**Línea**: ~374 (en el bloque `elif event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:`)

**Cambio**:
```python
# Salida de geocerca
elif event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:
    # Primero intentar determinar el rol desde la BD (más confiable)
    geofence_role = None
    if event.geofence_id:
        try:
            geofence_role = await self.db.fetchval(
                """
                SELECT tg.visit_type 
                FROM trip_geofences tg
                JOIN geofences g ON g.id = tg.geofence_id
                WHERE tg.trip_id = %s 
                  AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
                LIMIT 1
                """,
                trip["id"],
                event.geofence_id,
                event.geofence_id
            )
            logger.info(
                "geofence_role_detected",
                geofence_id=event.geofence_id,
                geofence_name=event.geofence_name,
                role=geofence_role,
                trip_id=trip["id"]
            )
        except Exception as e:
            logger.warning("geofence_role_lookup_failed", error=str(e), geofence_id=event.geofence_id)
    
    # Si encontramos el rol en BD, usarlo
    if geofence_role == "loading":
        action["update_status"] = True
        action["new_status"] = "en_ruta_destino"
        action["new_substatus"] = "rumbo_a_descarga"
    
    # NUEVO: Detección de desviación de ruta
    elif geofence_role == "route":
        # Verificar período de gracia antes de enviar notificación
        from app.config import settings
        grace_period = getattr(settings, 'route_deviation_grace_period', 300)
        
        if self._check_grace_period(trip["id"], grace_period):
            action["send_notification"] = True
            action["notification_message"] = (
                f"⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. "
                f"Ubicación actual: {event.address or 'No disponible'}"
            )
            logger.info(
                "route_deviation_detected",
                trip_id=trip["id"],
                geofence_name=event.geofence_name,
                geofence_id=event.geofence_id
            )
        else:
            # Período de gracia activo, no enviar notificación pero sí webhook
            action["send_notification"] = False
            logger.info(
                "route_deviation_notification_blocked_by_grace_period",
                trip_id=trip["id"],
                geofence_name=event.geofence_name
            )
        # NO cambiar el estado del viaje (solo notificaciones y webhooks)
    
    # Fallback: si no hay rol en BD, usar detección por nombre (compatibilidad)
    elif not geofence_role:
        geofence_name_lower = (event.geofence_name or "").lower()
        
        if "carga" in geofence_name_lower or "loading" in geofence_name_lower:
            action["update_status"] = True
            action["new_status"] = "en_ruta_destino"
            action["new_substatus"] = "rumbo_a_descarga"
        
        # NUEVO: Detección por nombre para geocercas de ruta
        elif "ruta" in geofence_name_lower or "route" in geofence_name_lower:
            # Verificar período de gracia antes de enviar notificación
            from app.config import settings
            grace_period = getattr(settings, 'route_deviation_grace_period', 300)
            
            if self._check_grace_period(trip["id"], grace_period):
                action["send_notification"] = True
                action["notification_message"] = (
                    f"⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. "
                    f"Ubicación actual: {event.address or 'No disponible'}"
                )
                logger.info(
                    "route_deviation_detected_by_name_fallback",
                    trip_id=trip["id"],
                    geofence_name=event.geofence_name
                )
            else:
                # Período de gracia activo, no enviar notificación pero sí webhook
                action["send_notification"] = False
                logger.info(
                    "route_deviation_notification_blocked_by_grace_period",
                    trip_id=trip["id"],
                    geofence_name=event.geofence_name
                )
```

---

### Cambio 6: Actualizar _send_webhooks_for_event - Webhook route_deviation

**Archivo**: `app/services/event_service.py`

**Línea**: ~505 (después de enviar `geofence_transition`)

**Cambio**:
```python
# Geofence Entry/Exit
elif event.notification_type in [
    WIALON_EVENT_TYPES["GEOFENCE_ENTRY"],
    WIALON_EVENT_TYPES["GEOFENCE_EXIT"],
]:
    transition_type = (
        "entry"
        if event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_ENTRY"]
        else "exit"
    )
    
    # Obtener role y tipo de la geocerca desde BD (MySQL)
    geofence_role = "unknown"
    geofence_type = "polygon"  # Default
    if event.geofence_id:
        geofence_info = await self.db.fetchrow(
            """
            SELECT tg.visit_type, g.geofence_type
            FROM trip_geofences tg
            JOIN geofences g ON g.id = tg.geofence_id
            WHERE tg.trip_id = %s 
              AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
            LIMIT 1
            """,
            trip_id,
            event.geofence_id,
            event.geofence_id,
        )
        if geofence_info:
            geofence_role = geofence_info.get("visit_type") or "unknown"
            geofence_type = geofence_info.get("geofence_type") or "polygon"
    
    # Fallback: detección por nombre
    if geofence_role == "unknown":
        geofence_name_lower = (event.geofence_name or "").lower()
        if "ruta" in geofence_name_lower or "route" in geofence_name_lower:
            geofence_role = "route"
    
    geofence_data = {
        "geofence_id": event.geofence_id,
        "geofence_name": event.geofence_name,
        "geofence_type": geofence_type,  # Obtenido desde BD
        "role": geofence_role,
        "notification_id": event.notification_id,
        "external_id": f"wialon_geo_{event.unit_id}_{event.event_time}",
        "location": {
            "latitude": event.latitude,
            "longitude": event.longitude,
            "address": event.address,
            "speed": event.speed,
        },
    }
    
    # Siempre enviar webhook geofence_transition
    await self.webhook_service.send_geofence_transition(
        event_id=event_id,
        trip_id=trip_id,
        transition_type=transition_type,
        geofence_data=geofence_data,
    )
    logger.info(
        "geofence_transition_webhook_sent",
        event_id=event_id,
        trip_id=trip_id,
        transition_type=transition_type,
    )
    
    # NUEVO: Si es salida de geocerca de ruta, también enviar webhook route_deviation
    if transition_type == "exit" and geofence_role == "route":
        try:
            deviation_data = {
                "distance_meters": 0,  # No se calcula distancia
                "max_allowed": 100,  # Valor por defecto
                "duration_seconds": 0,  # No se calcula duración
                "notification_id": event.notification_id,
                "external_id": f"wialon_route_dev_{event.unit_id}_{event.event_time}",
                "current_location": {
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "address": event.address,
                },
                "nearest_point": {},  # Vacío porque no se calcula
            }
            
            await self.webhook_service.send_route_deviation(
                event_id=event_id,
                trip_id=trip_id,
                deviation_data=deviation_data,
            )
            logger.info(
                "route_deviation_webhook_sent",
                event_id=event_id,
                trip_id=trip_id,
            )
        except Exception as e:
            # Si falla el envío de route_deviation, loggear pero no afectar el flujo
            logger.error(
                "route_deviation_webhook_failed",
                event_id=event_id,
                trip_id=trip_id,
                error=str(e)
            )
            # NO lanzar excepción para no afectar el envío de geofence_transition
```

---

## Testing

### Tests Unitarios Requeridos

1. **Test de Detección de Desviación**
   - Test que se detecta desviación cuando `visit_type` = "route"
   - Test que se detecta desviación por nombre (fallback)
   - Test que NO se cambia el estado del viaje
   - Test que se envía notificación WhatsApp

2. **Test de Período de Gracia**
   - Test que se envía primera notificación
   - Test que NO se envía segunda notificación dentro del período de gracia
   - Test que SÍ se envía notificación después del período de gracia
   - Test que los webhooks siempre se envían (no afectados por período de gracia)

3. **Test de Webhook route_deviation**
   - Test que se envía webhook `route_deviation` cuando sale de geocerca de ruta
   - Test que se envía webhook `geofence_transition` también
   - Test que si falla `route_deviation`, no afecta `geofence_transition`
   - Test que `distance_meters` = 0 cuando es salida de geocerca
   - Test que `geofence_type` se obtiene correctamente desde BD

### Tests de Integración Requeridos

1. **Test de Flujo Completo**
   - Test que procesa evento Wialon de salida de geocerca de ruta
   - Test que envía notificación WhatsApp
   - Test que envía ambos webhooks
   - Test que registra evento en BD
   - Test que NO cambia estado del viaje

2. **Test de Período de Gracia**
   - Test que envía notificación en primera salida
   - Test que NO envía notificación en segunda salida (dentro de período de gracia)
   - Test que SÍ envía notificación después del período de gracia
   - Test que webhooks siempre se envían

3. **Test de Fallback**
   - Test que usa detección por nombre cuando no se encuentra role en BD
   - Test que busca palabras clave "ruta" o "route" en nombre
   - Test que funciona correctamente con detección por nombre

---

## Verificación

### Checklist de Verificación

- [ ] Constantes actualizadas (`GEOFENCE_ROLES` incluye "route")
- [ ] Configuración actualizada (`route_deviation_grace_period` agregado)
- [ ] Detección de desviación implementada en `_determine_action()`
- [ ] Período de gracia implementado (`_check_grace_period()`)
- [ ] Limpieza de memoria implementada (`_cleanup_old_notifications()`)
- [ ] Webhook `route_deviation` enviado en `_send_webhooks_for_event()`
- [ ] Estado del viaje NO cambia cuando se detecta desviación
- [ ] Notificación WhatsApp enviada con formato correcto
- [ ] Período de gracia previene notificaciones duplicadas
- [ ] Webhooks siempre se envían (no afectados por período de gracia)
- [ ] Fallback a detección por nombre funciona
- [ ] Manejo de errores implementado (no afecta envío de `geofence_transition`)
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] E2E test funciona correctamente

---

## Monitoreo

### Logs a Monitorear

- `route_deviation_detected`: Cuando se detecta desviación de ruta
- `route_deviation_notification_allowed`: Cuando se permite enviar notificación
- `route_deviation_notification_blocked`: Cuando se bloquea notificación por período de gracia
- `route_deviation_webhook_sent`: Cuando se envía webhook `route_deviation`
- `route_deviation_webhook_failed`: Cuando falla el envío de webhook
- `route_deviation_detected_by_name_fallback`: Cuando se usa detección por nombre
- `route_deviation_notifications_cleaned`: Cuando se limpian entradas antiguas

### Métricas a Recolectar

- Número de desviaciones de ruta detectadas
- Número de notificaciones enviadas
- Número de notificaciones bloqueadas por período de gracia
- Número de webhooks `route_deviation` enviados
- Tiempo de procesamiento de eventos de desviación
- Tasa de error en envío de webhooks

---

## Rollback Plan

### Si algo sale mal

1. **Revertir Cambios**
   - Revertir cambios en `event_service.py`
   - Revertir cambios en `constants.py`
   - Revertir cambios en `config.py`

2. **Verificar Funcionalidad Existente**
   - Verificar que geocercas de carga/descarga siguen funcionando
   - Verificar que webhooks `geofence_transition` se envían correctamente
   - Verificar que no se rompió funcionalidad existente

3. **Investigar Problema**
   - Revisar logs para identificar el problema
   - Revisar tests para ver qué falló
   - Corregir problema y reintentar

---

## Tiempo Estimado

- **Preparación**: 10 minutos
- **Implementación de Detección**: 45 minutos
- **Implementación de Webhooks**: 25 minutos
- **Testing**: 45 minutos
- **Verificación**: 20 minutos
- **Total**: ~145 minutos (2 horas 25 minutos)

**Nota**: Estos tiempos son más detallados y realistas que la estimación inicial. Reflejan mejor el trabajo real necesario para implementar todas las tareas.

---

## Dependencias

### Dependencias Externas

- **Wialon**: Debe enviar eventos `geofence_exit` con `geofence_id`
- **WebhookService**: Debe tener método `send_route_deviation()` (ya existe)
- **NotificationService**: Debe tener método `send_trip_notification()` (ya existe)
- **Base de Datos MySQL**: Debe tener tabla `trip_geofences` con campo `visit_type` y tabla `geofences` con campo `geofence_type`

### Dependencias Internas

- **EventService**: Debe procesar eventos de `geofence_exit`
- **TripRepository**: Debe buscar viajes activos por `wialon_id`
- **UnitRepository**: Debe buscar unidades por `wialon_id`
- **EventRepository**: Debe guardar eventos en BD

---

## Riesgos

### Riesgos Identificados

1. **Riesgo**: Cambios en `event_service.py` pueden romper funcionalidad existente
   - **Mitigación**: Mantener lógica existente intacta, solo agregar nueva lógica
   - **Verificación**: Ejecutar tests existentes para verificar que no se rompió nada

2. **Riesgo**: Período de gracia puede causar pérdida de notificaciones importantes
   - **Mitigación**: Período de gracia solo aplica a notificaciones, no a webhooks
   - **Verificación**: Verificar que webhooks siempre se envían

3. **Riesgo**: Almacenamiento en memoria puede causar memory leak
   - **Mitigación**: Implementar limpieza periódica de entradas antiguas
   - **Verificación**: Verificar que se limpian entradas después de 1 hora

4. **Riesgo**: Fallo en envío de webhook `route_deviation` puede afectar flujo
   - **Mitigación**: Envolver en try-except para no afectar envío de `geofence_transition`
   - **Verificación**: Verificar que `geofence_transition` siempre se envía

---

## Conclusión

Este plan de implementación describe todos los cambios necesarios para implementar la detección de desviación de ruta mediante geocercas. Los cambios son mínimos y no rompen funcionalidad existente. La implementación se integra de manera consistente con el sistema actual.

---

## Referencias

- **Especificación**: `specs/1-route-deviation-geofence/spec.md`
- **Research**: `specs/1-route-deviation-geofence/plan/research.md`
- **Data Model**: `specs/1-route-deviation-geofence/plan/data-model.md`
- **Quickstart**: `specs/1-route-deviation-geofence/plan/quickstart.md`
- **Código Existente**: `app/services/event_service.py`

