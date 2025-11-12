# Plan de Implementación: Detección de Desviación de Ruta mediante Geocercas

## Resumen

Este directorio contiene el plan de implementación completo para la funcionalidad de detección de desviación de ruta mediante geocercas.

## Archivos del Plan

### 1. `research.md`
**Descripción**: Decisiones técnicas y justificaciones para la implementación.
**Contenido**:
- Decisiones técnicas sobre detección de role
- Período de gracia para notificaciones
- Estructura del webhook route_deviation
- Formato del mensaje WhatsApp
- Manejo de errores
- Consideraciones de performance y seguridad

### 2. `data-model.md`
**Descripción**: Modelo de datos y entidades relacionadas con la funcionalidad.
**Contenido**:
- Entidades principales (Geocerca de Ruta, Evento de Desviación, Notificación, Webhook)
- Relaciones entre entidades
- Estados y transiciones
- Validaciones y reglas de negocio
- Índices y optimizaciones
- Modelos Pydantic

### 3. `implementation-plan.md`
**Descripción**: Plan detallado de implementación con cambios específicos por archivo.
**Contenido**:
- Archivos a modificar
- Secuencia de implementación
- Cambios detallados con código
- Tests requeridos
- Verificación y monitoreo
- Riesgos y mitigaciones

### 4. `quickstart.md`
**Descripción**: Guía rápida de implementación paso a paso.
**Contenido**:
- Cambios requeridos por archivo
- Código a agregar/modificar
- Pasos de implementación
- Testing
- Troubleshooting
- Referencias

## Flujo de Implementación

1. **Revisar Research** (`research.md`)
   - Entender las decisiones técnicas
   - Revisar alternativas consideradas
   - Verificar que las decisiones son correctas

2. **Revisar Data Model** (`data-model.md`)
   - Entender las entidades y relaciones
   - Verificar que no se requieren cambios en BD
   - Revisar validaciones y reglas de negocio

3. **Seguir Implementation Plan** (`implementation-plan.md`)
   - Implementar cambios en orden
   - Seguir la secuencia de implementación
   - Verificar cada paso antes de continuar

4. **Usar Quickstart** (`quickstart.md`)
   - Referencia rápida durante implementación
   - Troubleshooting de problemas comunes
   - Verificación de cambios

## Cambios Requeridos

### Archivos a Modificar

1. **`app/core/constants.py`**
   - Agregar "route" a `GEOFENCE_ROLES`
   - Agregar `ROUTE_DEVIATION_GRACE_PERIOD = 300`

2. **`app/config.py`**
   - Agregar `route_deviation_grace_period: int = 300`

3. **`app/services/event_service.py`**
   - Agregar atributo `_route_deviation_notifications = {}`
   - Agregar método `_check_grace_period()`
   - Agregar método `_cleanup_old_notifications()`
   - Actualizar `_determine_action()` para detectar desviación de ruta
   - Actualizar `_send_webhooks_for_event()` para enviar webhook `route_deviation`

### Archivos NO Requeridos para Modificar

- **Base de datos**: No se requieren migraciones
- **Modelos**: No se requieren cambios en modelos existentes
- **APIs**: No se requieren cambios en endpoints
- **Tests**: Se requieren nuevos tests, no modificar tests existentes

## Testing

### Tests Unitarios Requeridos

1. Test de detección de desviación de ruta
2. Test de período de gracia
3. Test de envío de webhook route_deviation
4. Test de fallback a detección por nombre

### Tests de Integración Requeridos

1. Test de flujo completo desde evento Wialon hasta webhook
2. Test de período de gracia con múltiples eventos
3. Test de comportamiento con geocercas de carga/descarga (retrocompatibilidad)

### E2E Tests

1. Usar script `e2e_test_flow.py` con geocerca de ruta
2. Simular salida de geocerca de ruta
3. Verificar notificación WhatsApp
4. Verificar webhooks enviados
5. Verificar que NO se cambia estado del viaje

## Verificación

### Checklist de Verificación

- [ ] Constantes actualizadas
- [ ] Configuración actualizada
- [ ] Detección de desviación implementada
- [ ] Período de gracia implementado
- [ ] Webhook route_deviation enviado
- [ ] Estado del viaje NO cambia
- [ ] Notificación WhatsApp enviada
- [ ] Período de gracia previene duplicados
- [ ] Webhooks siempre se envían
- [ ] Fallback a detección por nombre funciona
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] E2E test funciona correctamente

## Tiempo Estimado

- **Preparación**: 5 minutos
- **Implementación de Detección**: 30 minutos
- **Implementación de Webhooks**: 20 minutos
- **Testing**: 30 minutos
- **Verificación**: 15 minutos
- **Total**: ~100 minutos (1 hora 40 minutos)

## Referencias

- **Especificación**: `../spec.md`
- **Research**: `research.md`
- **Data Model**: `data-model.md`
- **Implementation Plan**: `implementation-plan.md`
- **Quickstart**: `quickstart.md`

## Próximos Pasos

1. Revisar todos los archivos del plan
2. Implementar cambios según `implementation-plan.md`
3. Ejecutar tests unitarios e integración
4. Ejecutar E2E test con `e2e_test_flow.py`
5. Verificar que todo funciona correctamente
6. Desplegar a entorno de desarrollo
7. Desplegar a producción

## Notas

- Todos los cambios son retrocompatibles
- No se requieren migraciones de BD
- No se rompe funcionalidad existente
- La implementación se integra de manera consistente con el sistema actual

