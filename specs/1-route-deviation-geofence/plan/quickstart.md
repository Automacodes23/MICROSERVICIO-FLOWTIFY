# Quickstart: Implementación de Detección de Desviación de Ruta mediante Geocercas

## Resumen de la Implementación

Esta guía rápida describe los pasos necesarios para implementar la detección automática de desviación de ruta cuando un vehículo sale de una geocerca con role "route".

## Cambios Requeridos

### 1. Actualizar Constantes

**Archivo**: `app/core/constants.py`

**Cambio**: Agregar "route" a `GEOFENCE_ROLES` y agregar constante para período de gracia.

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

### 2. Actualizar Configuración

**Archivo**: `app/config.py`

**Cambio**: Agregar configuración para período de gracia.

```python
# Período de gracia para notificaciones de desviación de ruta (en segundos)
route_deviation_grace_period: int = 300  # 5 minutos por defecto
```

---

### 3. Actualizar EventService - Detección de Desviación

**Archivo**: `app/services/event_service.py`

**Cambio**: Agregar lógica para detectar salida de geocerca de ruta en `_determine_action()`.

**Ubicación**: En el bloque `elif event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:` (línea 374)

**Código a agregar**:
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
        action["send_notification"] = True
        action["notification_message"] = (
            f"⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. "
            f"Ubicación actual: {event.address or 'No disponible'}"
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
            action["send_notification"] = True
            action["notification_message"] = (
                f"⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. "
                f"Ubicación actual: {event.address or 'No disponible'}"
            )
            logger.info("geofence_detected_by_name_fallback", type="route", geofence_name=event.geofence_name)
```

---

### 4. Actualizar EventService - Período de Gracia

**Archivo**: `app/services/event_service.py`

**Cambio**: Agregar lógica de período de gracia para notificaciones de desviación de ruta.

**Ubicación**: Agregar método privado en `EventService` y actualizar `_determine_action()`.

**Código a agregar**:
```python
# Al inicio de la clase EventService, agregar atributo para tracking
def __init__(self, ...):
    # ... código existente ...
    self._route_deviation_notifications = {}  # {trip_id: {"last_notification_time": timestamp}}

# Agregar método para verificar período de gracia
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
    
    current_time = time.time()
    
    if trip_id not in self._route_deviation_notifications:
        # Primera notificación para este viaje
        self._route_deviation_notifications[trip_id] = {
            "last_notification_time": current_time
        }
        return True
    
    last_notification_time = self._route_deviation_notifications[trip_id]["last_notification_time"]
    time_since_last = current_time - last_notification_time
    
    if time_since_last >= grace_period_seconds:
        # Período de gracia expirado, actualizar timestamp
        self._route_deviation_notifications[trip_id]["last_notification_time"] = current_time
        return True
    else:
        # Período de gracia activo
        return False

# Actualizar _determine_action() para usar período de gracia
# En el bloque de detección de desviación de ruta:
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
    else:
        # Período de gracia activo, no enviar notificación pero sí webhook
        action["send_notification"] = False
        logger.info(
            "route_deviation_notification_blocked",
            trip_id=trip["id"],
            grace_period_seconds=grace_period
        )
```

---

### 5. Actualizar EventService - Envío de Webhook route_deviation

**Archivo**: `app/services/event_service.py`

**Cambio**: Agregar lógica para enviar webhook `route_deviation` cuando se detecta salida de geocerca de ruta.

**Ubicación**: En `_send_webhooks_for_event()` en el bloque de `GEOFENCE_EXIT` (línea 462)

**Código a agregar**:
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
    
    # Obtener role de la geocerca
    geofence_role = "unknown"
    if event.geofence_id:
        geofence_role = await self.db.fetchval(
            """
            SELECT tg.visit_type 
            FROM trip_geofences tg
            JOIN geofences g ON g.id = tg.geofence_id
            WHERE tg.trip_id = %s 
              AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
            LIMIT 1
            """,
            trip_id,
            event.geofence_id,
            event.geofence_id,
        ) or "unknown"
    
    # Fallback: detección por nombre
    if geofence_role == "unknown":
        geofence_name_lower = (event.geofence_name or "").lower()
        if "ruta" in geofence_name_lower or "route" in geofence_name_lower:
            geofence_role = "route"
    
    geofence_data = {
        "geofence_id": event.geofence_id,
        "geofence_name": event.geofence_name,
        "geofence_type": "polygon",  # TODO: Obtener tipo real
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
```

---

### 6. Limpieza de Memoria (Opcional pero Recomendado)

**Archivo**: `app/services/event_service.py`

**Cambio**: Agregar limpieza periódica de entradas antiguas en `_route_deviation_notifications`.

**Código a agregar**:
```python
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

**Llamar limpieza**: Agregar llamada periódica (cada hora) o al inicio de `_check_grace_period()`.

---

## Pasos de Implementación

### Paso 1: Actualizar Constantes

1. Abrir `app/core/constants.py`
2. Agregar "route" a `GEOFENCE_ROLES`
3. Agregar constante `ROUTE_DEVIATION_GRACE_PERIOD = 300`

### Paso 2: Actualizar Configuración

1. Abrir `app/config.py`
2. Agregar `route_deviation_grace_period: int = 300` a la clase `Settings`

### Paso 3: Actualizar EventService - Detección

1. Abrir `app/services/event_service.py`
2. Agregar atributo `_route_deviation_notifications = {}` en `__init__`
3. Agregar método `_check_grace_period()`
4. Agregar método `_cleanup_old_notifications()`
5. Actualizar `_determine_action()` para detectar salida de geocerca de ruta
6. Actualizar `_send_webhooks_for_event()` para enviar webhook `route_deviation`

### Paso 4: Probar Implementación

1. Crear viaje de prueba con geocerca de ruta (role="route")
2. Simular evento `geofence_exit` para la geocerca de ruta
3. Verificar que se envía notificación WhatsApp
4. Verificar que se envían ambos webhooks (`geofence_transition` y `route_deviation`)
5. Verificar que NO se cambia el estado del viaje
6. Simular segunda salida dentro del período de gracia
7. Verificar que NO se envía segunda notificación (período de gracia activo)
8. Verificar que SÍ se envían webhooks (período de gracia no afecta webhooks)

---

## Testing

### Test Unitario: Detección de Desviación

```python
def test_route_deviation_detection():
    # Test que se detecta desviación cuando sale de geocerca de ruta
    event = WialonEvent(
        notification_type="geofence_exit",
        geofence_id="1003",
        geofence_name="RUTA",
        # ... otros campos ...
    )
    trip = {"id": "trip_123", "status": "en_ruta_destino"}
    
    action = await event_service._determine_action(event, trip)
    
    assert action["send_notification"] == True
    assert "Desviación de ruta detectada" in action["notification_message"]
    assert action["update_status"] == False  # No cambiar estado
```

### Test Unitario: Período de Gracia

```python
def test_grace_period():
    # Test que no se envía notificación dentro del período de gracia
    trip_id = "trip_123"
    
    # Primera notificación
    can_send = event_service._check_grace_period(trip_id, grace_period_seconds=300)
    assert can_send == True
    
    # Segunda notificación inmediatamente (dentro del período de gracia)
    can_send = event_service._check_grace_period(trip_id, grace_period_seconds=300)
    assert can_send == False  # Bloqueada por período de gracia
```

### Test Integración: Webhook route_deviation

```python
def test_route_deviation_webhook():
    # Test que se envía webhook route_deviation cuando sale de geocerca de ruta
    event = WialonEvent(
        notification_type="geofence_exit",
        geofence_id="1003",
        geofence_name="RUTA",
        # ... otros campos ...
    )
    
    await event_service.process_event(event)
    
    # Verificar que se envió webhook route_deviation
    # (mockear webhook_service y verificar llamada)
```

---

## Verificación

### Checklist de Verificación

- [ ] Constantes actualizadas (`GEOFENCE_ROLES` incluye "route")
- [ ] Configuración actualizada (`route_deviation_grace_period` agregado)
- [ ] Detección de desviación implementada en `_determine_action()`
- [ ] Período de gracia implementado
- [ ] Webhook `route_deviation` enviado en `_send_webhooks_for_event()`
- [ ] Estado del viaje NO cambia cuando se detecta desviación
- [ ] Notificación WhatsApp enviada con formato correcto
- [ ] Período de gracia previene notificaciones duplicadas
- [ ] Webhooks siempre se envían (no afectados por período de gracia)
- [ ] Fallback a detección por nombre funciona
- [ ] Limpieza de memoria implementada
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] E2E test funciona correctamente

---

## Configuración

### Variable de Entorno (Opcional)

```bash
# .env
ROUTE_DEVIATION_GRACE_PERIOD=300  # 5 minutos en segundos
```

### Configuración por Defecto

```python
# app/config.py
route_deviation_grace_period: int = 300  # 5 minutos por defecto
```

---

## Monitoreo

### Logs a Monitorear

- `route_deviation_detected`: Cuando se detecta desviación de ruta
- `route_deviation_notification_sent`: Cuando se envía notificación WhatsApp
- `route_deviation_notification_blocked`: Cuando se bloquea notificación por período de gracia
- `route_deviation_webhook_sent`: Cuando se envía webhook `route_deviation`
- `route_deviation_webhook_failed`: Cuando falla el envío de webhook
- `geofence_detected_by_name_fallback`: Cuando se usa detección por nombre

### Métricas a Recolectar

- Número de desviaciones de ruta detectadas
- Número de notificaciones enviadas
- Número de notificaciones bloqueadas por período de gracia
- Número de webhooks `route_deviation` enviados
- Tiempo de procesamiento de eventos de desviación
- Tasa de error en envío de webhooks

---

## Troubleshooting

### Problema: No se detecta desviación de ruta

**Solución**:
1. Verificar que `visit_type` = "route" en `trip_geofences`
2. Verificar que `geofence_id` está presente en el evento Wialon
3. Verificar logs para ver si se usa detección por nombre (fallback)
4. Verificar que la consulta a BD funciona correctamente

### Problema: Notificaciones duplicadas

**Solución**:
1. Verificar que el período de gracia está funcionando
2. Verificar que `_check_grace_period()` se llama correctamente
3. Verificar que el timestamp se actualiza correctamente
4. Verificar logs para ver si se bloquean notificaciones

### Problema: Webhook route_deviation no se envía

**Solución**:
1. Verificar que `geofence_role` = "route" después de consultar BD
2. Verificar que `transition_type` = "exit"
3. Verificar logs para ver si hay errores en el envío
4. Verificar que `WebhookService.send_route_deviation()` está disponible
5. Verificar que no hay excepciones silenciadas

---

## Próximos Pasos

Después de implementar esta funcionalidad:

1. **Testing**: Ejecutar tests unitarios e integración
2. **E2E Testing**: Probar con el script `e2e_test_flow.py`
3. **Monitoreo**: Configurar alertas para errores en envío de webhooks
4. **Documentación**: Actualizar documentación de API si es necesario
5. **Despliegue**: Desplegar a entorno de desarrollo y luego a producción

---

## Referencias

- **Especificación**: `specs/1-route-deviation-geofence/spec.md`
- **Research**: `specs/1-route-deviation-geofence/plan/research.md`
- **Data Model**: `specs/1-route-deviation-geofence/plan/data-model.md`
- **Código Existente**: `app/services/event_service.py`
- **Webhook Service**: `app/services/webhook_service.py`
- **Notification Service**: `app/services/notification_service.py`

