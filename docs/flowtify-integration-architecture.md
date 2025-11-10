# Arquitectura de Integración: SHOW-SERVICE ↔ Flowtify

**Session Date:** 2025-01-10
**Facilitator:** Business Analyst Mary
**Participant:** SHOW-SERVICE Development Team
**Project:** Microservicio de Logística Inteligente

---

## Executive Summary

**Topic:** Diseño completo de payloads JSON para integración bidireccional entre SHOW-SERVICE y Flowtify

**Session Goals:**
- Definir estructura completa de payloads para comunicación microservicio → Flowtify
- Identificar todos los datos disponibles en SHOW-SERVICE para enriquecer notificaciones
- Diseñar flujos de datos para actualización de estado, alertas y comunicaciones
- Documentar endpoints y formatos esperados por Flowtify

**Techniques Used:** Análisis de códigobase existente, diseño progresivo de payloads, validación de casos de uso

**Total Ideas Generated:** 5 payloads completos con más de 50 campos de datos enriquecidos

**Key Themes Identified:**
- Comunicación en tiempo real basada en eventos
- Datos enriquecidos desde múltiples fuentes (Wialon, WhatsApp, AI)
- Flujos automatizados de actualización de estados
- Sistema de alertas críticas con contexto completo

---

## System Architecture Overview

### Data Flow Diagram

```
FLOWTIFY (UI Interactive) ←→ SHOW-SERVICE (Backend Intelligence)
     ↓                                ↓
Trip Creation ←→ Status Updates ←→ WhatsApp Integration
     ↓                                ↓
Geofence Config ←→ Route Monitoring ←→ AI Processing
     ↓                                ↓
Alert Management ←→ Communication ←→ Wialon Events
```

### Available Data Inventory

Based on comprehensive codebase analysis, SHOW-SERVICE has access to:

**Trip Data Fields:**
- Trip IDs (internal + Floatify), status/substatus, timeline data
- Origin/destination with coordinates and metadata
- QR codes, cargo descriptions, tenant information

**Driver Information:**
- Complete profile (name, phone, Wialon codes)
- Communication history and metadata

**Vehicle/Unit Data:**
- Unit identification (plates, IMEI, Wialon IDs)
- WhatsApp group integration
- Provider information and tracking data

**Location & Tracking:**
- Real-time GPS coordinates (lat, lng, altitude, speed, course)
- Geocoded addresses and timestamps
- Geofence information (ID, name, type, role)

**Communication Data:**
- WhatsApp messages with transcription
- AI-processed intents and confidence scores
- Message metadata and conversation history

**Alert & Event Data:**
- Wialon notifications (speed violations, geofence events)
- Event classification and processing status
- Raw payload data for audit trails

---

## Payload Design: SHOW-SERVICE → Flowtify

### Payload #1: Status Notification

**Purpose:** Actualización de estados del viaje en tiempo real
**Trigger:** Cambio de estado/substatus del viaje
**Endpoint:** POST /flowtify/webhook/status-update

```json
{
  "event": "status_update",
  "timestamp": "2025-01-10T15:30:45-06:00",
  "tenant_id": 24,
  "trip": {
    "id": "uuid-12345",
    "floatify_trip_id": "45",
    "code": "TEST_FLOW_20241006123456",
    "status": "en_ruta_carga",
    "substatus": "rumbo_a_zona_carga",
    "status_change_reason": "driver_message_carga_completada",
    "previous_status": "en_zona_carga",
    "previous_substatus": "carga_completada",
    "timeline": {
      "created_at": "2025-01-10T14:00:00-06:00",
      "started_at": "2025-01-10T14:15:00-06:00",
      "updated_at": "2025-01-10T15:30:45-06:00"
    }
  },
  "driver": {
    "id": "uuid-driver-33",
    "name": "PRUEBA FLOWTIFY",
    "phone": "+5214775589835",
    "wialon_driver_code": "29"
  },
  "unit": {
    "id": "uuid-unit-18",
    "code": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728",
    "imei": "863719067169228",
    "name": "Torton 309 41BB3T"
  },
  "location": {
    "latitude": 21.0505,
    "longitude": -101.7995,
    "altitude": 1796,
    "speed": 45.2,
    "course": 270,
    "address": "Carretera León-Salamanca Km 8, León, Gto., México",
    "last_update": "2025-01-10T15:30:40-06:00"
  },
  "customer": {
    "id": "uuid-customer-6",
    "name": "Pañales Aurora"
  },
  "metadata": {
    "status_change_source": "whatsapp_driver_message",
    "trigger_message": "Ya cargué y me voy",
    "ai_processed": true,
    "ai_confidence": 0.95,
    "geofence_related": true,
    "priority": "medium"
  }
}
```

**Key Features:**
- Estado actual y anterior para animaciones de transición
- Timeline completo para progress bars
- Contexto del cambio (mensaje del conductor, AI, etc.)
- Metadatos para auditoría y debugging

---

### Payload #2: Speed Violation Alert

**Purpose:** Notificación de excesos de velocidad detectados
**Trigger:** Detección de velocidad sobre límite permitido
**Endpoint:** POST /flowtify/webhook/speed-violation

```json
{
  "event": "speed_violation",
  "timestamp": "2025-01-10T16:45:22-06:00",
  "tenant_id": 24,
  "violation": {
    "type": "excessive_speed",
    "severity": "high",
    "detected_speed": 105.8,
    "max_allowed_speed": 80.0,
    "speed_difference": 25.8,
    "percentage_over_limit": 32.25,
    "duration_seconds": 45,
    "distance_covered_km": 1.2,
    "violation_id": "speed_viol_20250110_164522",
    "is_ongoing": false
  },
  "trip": {
    "id": "uuid-12345",
    "floatify_trip_id": "45",
    "code": "TEST_FLOW_20241006123456",
    "status": "en_ruta_destino",
    "substatus": "rumbo_a_descarga",
    "origin": "León",
    "destination": "Jalisco"
  },
  "driver": {
    "id": "uuid-driver-33",
    "name": "PRUEBA FLOWTIFY",
    "phone": "+5214775589835",
    "wialon_driver_code": "29"
  },
  "unit": {
    "id": "uuid-unit-18",
    "code": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728",
    "imei": "863719067169228",
    "name": "Torton 309 41BB3T"
  },
  "location": {
    "latitude": 21.1502,
    "longitude": -101.8503,
    "altitude": 1810,
    "current_speed": 105.8,
    "course": 285,
    "address": "Autopista León-Guadalajara Km 45, Irapuato, Gto., México",
    "last_update": "2025-01-10T16:45:20-06:00"
  },
  "violation_history": {
    "total_violations_today": 3,
    "total_violations_trip": 5,
    "previous_violation": {
      "timestamp": "2025-01-10T14:20:15-06:00",
      "speed": 98.5,
      "location": "Carretera León-Silao Km 12"
    },
    "violation_streak": 2,
    "time_since_last_violation_minutes": 125
  },
  "customer": {
    "id": "uuid-customer-6",
    "name": "Pañales Aurora",
    "requires_speed_monitoring": true
  },
  "wialon_source": {
    "notification_id": "NOTIF_1728280100_7890",
    "notification_type": "speed_violation",
    "external_id": "wialon_speed_27538728_164522"
  }
}
```

**Key Features:**
- Datos completos de la violación (velocidad, duración, distancia)
- Historial de violaciones para patrones
- Contexto completo del viaje y conductor
- Referencia exacta a fuente Wialon

---

### Payload #3: Geofence Entry/Exit

**Purpose:** Notificación de entrada/salida a zonas geográficas definidas
**Trigger:** Eventos de geocerca desde Wialon
**Endpoint:** POST /flowtify/webhook/geofence-transition

```json
{
  "event": "geofence_transition",
  "timestamp": "2025-01-10T17:20:15-06:00",
  "tenant_id": 24,
  "transition": {
    "type": "entry",
    "previous_type": "exit",
    "transition_id": "geo_trans_20250110_172015",
    "direction": "entering"
  },
  "trip": {
    "id": "uuid-12345",
    "floatify_trip_id": "45",
    "code": "TEST_FLOW_20241006123456",
    "status": "en_zona_carga",
    "substatus": "esperando_inicio_carga",
    "origin": "León",
    "destination": "Jalisco"
  },
  "driver": {
    "id": "uuid-driver-33",
    "name": "PRUEBA FLOWTIFY",
    "phone": "+5214775589835",
    "wialon_driver_code": "29"
  },
  "unit": {
    "id": "uuid-unit-18",
    "code": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728",
    "imei": "863719067169228",
    "name": "Torton 309 41BB3T"
  },
  "geofence": {
    "id": "9001",
    "name": "CEDIS COPPEL LEON",
    "role": "loading",
    "type": "polygon",
    "order": 1,
    "is_critical_zone": true,
    "requires_confirmation": true
  },
  "location": {
    "latitude": 21.1458,
    "longitude": -101.6789,
    "altitude": 1795,
    "speed": 15.2,
    "course": 180,
    "address": "BLVD. JUAN ALONSO DE TORRES #1005, CEDIS COPPEL LEON, León, Gto.",
    "distance_from_geofence_center_m": 50,
    "time_inside_geofence_seconds": 0,
    "last_update": "2025-01-10T17:20:13-06:00"
  },
  "timing": {
    "trip_elapsed_time_minutes": 195,
    "time_since_previous_geofence_minutes": 25,
    "estimated_wait_time_minutes": 45,
    "scheduled_departure_time": "2025-01-10T18:00:00-06:00",
    "on_time_status": "early"
  },
  "customer": {
    "id": "uuid-customer-6",
    "name": "Pañales Aurora"
  },
  "wialon_source": {
    "notification_id": "NOTIF_1728280200_4567",
    "notification_type": "geofence_entry",
    "external_id": "wialon_geo_27538728_172015",
    "raw_geofence_id": "9001"
  },
  "workflow_triggers": {
    "auto_status_update": true,
    "whatsapp_notification_enabled": true,
    "supervisor_alert": false,
    "requires_driver_action": true,
    "expected_next_status": "cargando"
  }
}
```

**Geofence Role Types:**
- `origin`: Punto de partida del viaje
- `loading`: Zona de carga
- `unloading`: Zona de descarga
- `route`: Corredor/ruta autorizada
- `waypoint`: Puntos intermedios
- `depot`: Base/depósito

---

### Payload #4: Route Deviation

**Purpose:** Alerta crítica por salida de ruta autorizada
**Trigger:** Salida de geocerca con `role: "route"`
**Endpoint:** POST /flowtify/webhook/route-deviation

```json
{
  "event": "route_deviation",
  "timestamp": "2025-01-10T18:45:30-06:00",
  "tenant_id": 24,
  "deviation": {
    "type": "route_deviation",
    "severity": "critical",
    "deviation_id": "route_dev_20250110_184530",
    "distance_from_route_meters": 350,
    "max_allowed_deviation": 100,
    "excess_deviation_meters": 250,
    "deviation_duration_seconds": 120,
    "current_location": {
      "latitude": 21.1802,
      "longitude": -101.6234,
      "address": "Carretera a Dolores Hidalgo Km 8, Guanajuato, Gto."
    },
    "nearest_point_on_route": {
      "latitude": 21.1567,
      "longitude": -101.6789,
      "distance_meters": 350
    }
  },
  "trip": {
    "id": "uuid-12345",
    "floatify_trip_id": "45",
    "code": "TEST_FLOW_20241006123456",
    "status": "en_ruta_destino",
    "substatus": "desvio_ruta_detectado",
    "origin": "León",
    "destination": "Jalisco"
  },
  "driver": {
    "id": "uuid-driver-33",
    "name": "PRUEBA FLOWTIFY",
    "phone": "+5214775589835",
    "wialon_driver_code": "29"
  },
  "unit": {
    "id": "uuid-unit-18",
    "code": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728",
    "imei": "863719067169228"
  },
  "route_info": {
    "current_leg": "leon_to_silao",
    "progress_percentage": 25,
    "estimated_time_to_destination_hours": 3.5,
    "last_known_route_position": {
      "timestamp": "2025-01-10T18:41:00-06:00",
      "latitude": 21.1567,
      "longitude": -101.6789,
      "was_on_route": true
    }
  },
  "immediate_actions": {
    "supervisor_notified": true,
    "driver_contact_attempted": true,
    "whatsapp_alert_sent": true,
    "flowtify_critical_alert": true
  },
  "wialon_source": {
    "notification_id": "NOTIF_1728280300_9999",
    "notification_type": "position_update",
    "external_id": "wialon_pos_27538728_184530"
  }
}
```

**Critical Actions Triggered:**
- Notificación inmediata a supervisor
- Contacto automático con conductor via WhatsApp
- Alerta crítica en UI de Flowtify
- Creación de caso de seguimiento

---

### Payload #5: Bot/Operator Response

**Purpose:** Envío de respuestas generadas por AI u operadores hacia Flowtify
**Trigger:** Respuesta del bot o intervención de operador
**Endpoint:** POST /flowtify/webhook/communication-response

```json
{
  "event": "communication_response",
  "timestamp": "2025-01-10T19:15:45-06:00",
  "tenant_id": 24,
  "communication": {
    "type": "bot_response",
    "direction": "outbound",
    "message_id": "bot_msg_20250110_191545",
    "original_message_id": "whatsapp_1234567890",
    "conversation_id": "conv_uuid_trip_12345",
    "response_content": "Confirmado. He recibido que has completado la carga. Por favor confirma cuando estés en ruta hacia la zona de descarga.",
    "response_type": "confirmation_status_request",
    "language": "es",
    "character_count": 145,
    "estimated_read_time_seconds": 8
  },
  "trip": {
    "id": "uuid-12345",
    "floatify_trip_id": "45",
    "code": "TEST_FLOW_20241006123456",
    "status": "en_zona_carga",
    "substatus": "carga_completada",
    "origin": "León",
    "destination": "Jalisco"
  },
  "sender": {
    "type": "bot",
    "name": "AI Assistant",
    "model_used": "gemini-pro",
    "confidence_score": 0.92,
    "processing_time_ms": 1250,
    "is_automated": true
  },
  "recipient": {
    "type": "driver",
    "id": "uuid-driver-33",
    "name": "PRUEBA FLOWTIFY",
    "phone": "+5214775589835",
    "whatsapp_group_id": "120363186235823658@g.us"
  },
  "ai_analysis": {
    "original_message": "ya termine de cargar me voy",
    "detected_intent": "loading_complete",
    "intent_confidence": 0.95,
    "extracted_entities": {
      "action": "carga",
      "status": "completada",
      "next_action": "salida"
    },
    "response_strategy": "confirm_status_update",
    "suggested_action": "update_trip_status",
    "new_recommended_status": "rumbo_a_descarga"
  },
  "whatsapp_delivery": {
    "message_sent": true,
    "delivery_timestamp": "2025-01-10T19:15:48-06:00",
    "delivery_status": "delivered",
    "read_timestamp": "2025-01-10T19:16:15-06:00",
    "read_status": "read"
  },
  "context": {
    "message_sequence_number": 15,
    "total_messages_in_conversation": 30,
    "time_since_last_message_minutes": 3,
    "current_geofence": "loading_zone",
    "trip_phase": "post_carga"
  },
  "metadata": {
    "auto_status_update_triggered": true,
    "supervisor_notification_required": false,
    "priority": "normal",
    "requires_follow_up": true,
    "escalation_threshold_exceeded": false
  }
}
```

**Response Types:**
- `bot_response`: Respuesta automática del AI
- `operator_response`: Intervión manual de operador
- `system_notification`: Notificaciones automáticas del sistema

---

## Integration Requirements: Flowtify → SHOW-SERVICE

### Updated Trip Creation Payload

**Purpose:** Creación de nuevos viajes con soporte para geocerca de ruta
**Endpoint:** POST /api/v1/trips/create

```json
{
  "event": "whatsapp.group.create",
  "action": "create_group",
  "tenant_id": 24,
  "trip": {
    "id": 45,
    "code": "TEST_FLOW_20241006123456",
    "status": "asignado",
    "planned_start": "2025-10-06T20:00:00-06:00",
    "planned_end": "2025-10-06T22:00:00-06:00",
    "origin": "León",
    "destination": "Jalisco"
  },
  "driver": {
    "id": 33,
    "name": "PRUEBA_FLOWTIFY",
    "phone": "+5214775589835"
  },
  "unit": {
    "id": 18,
    "floatify_unit_id": "18",
    "name": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728",
    "imei": "863719067169228"
  },
  "customer": {
    "id": 6,
    "name": "Pañales Aurora"
  },
  "geofences": [
    {
      "role": "origin",
      "geofence_id": "685",
      "geofence_name": "PATIO TTU",
      "geofence_type": "circle",
      "order": 0
    },
    {
      "role": "loading",
      "geofence_id": "9001",
      "geofence_name": "CEDIS COPPEL LEON",
      "geofence_type": "polygon",
      "order": 1
    },
    {
      "role": "route",
      "geofence_id": "ROUTE_001",
      "geofence_name": "RUTA LEON-JALISCO",
      "geofence_type": "polyline",
      "order": 3
    },
    {
      "role": "unloading",
      "geofence_id": "9002",
      "geofence_name": "BODEGA COPPEL JALISCO",
      "geofence_type": "polygon",
      "order": 2
    }
  ],
  "whatsapp_participants": [
    "+5214771817823",
    "+5214775589835"
  ],
  "metadata": {
    "tipo": "Cliente",
    "modalidad": "Renta",
    "priority": "medium"
  }
}
```

**Key Addition:** Geofence con `role: "route"` para detección de desvíos

---

## Data Flow Architecture

### Event Processing Flow

```
1. EXTERNAL TRIGGERS
   ├─ Wialon Events (position, speed, geofence)
   ├─ WhatsApp Messages (driver communications)
   └─ Flowtify Actions (trip creation, updates)

2. SHOW-SERVICE PROCESSING
   ├─ Event Normalization & Validation
   ├─ AI Analysis (Gemini for messages)
   ├─ Business Logic Application
   └─ Database Updates

3. FLOWTIFY NOTIFICATIONS
   ├─ Status Updates (real-time)
   ├─ Critical Alerts (speed, route deviation)
   ├─ Communication Responses (AI/operator)
   └─ Geofence Transitions
```

### Status Mapping

| Current Status | Next Status | Trigger | Payload Type |
|---------------|-------------|---------|--------------|
| planned | asignado | Manual assignment | status_update |
| asignado | en_ruta_carga | Driver departure | status_update |
| en_ruta_carga | en_zona_carga | Geofence entry | geofence_transition |
| en_zona_carga | cargando | WhatsApp message | communication_response |
| cargando | carga_completada | WhatsApp message | communication_response |
| carga_completada | en_ruta_destino | Geofence exit | geofence_transition |
| en_ruta_destino | en_zona_descarga | Geofence entry | geofence_transition |
| en_zona_descarga | descargando | WhatsApp message | communication_response |
| descargando | finalizado | WhatsApp message | communication_response |

---

## Implementation Guidelines

### Error Handling

All payloads should include:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Detailed error description",
    "context": { ... }
  },
  "trace_id": "request_unique_identifier"
}
```

### Authentication & Security

- **Webhook Secrets:** Use shared secrets for payload validation
- **Rate Limiting:** Implement rate limiting for Flowtify endpoints
- **Data Encryption:** Encrypt sensitive data in transit (HTTPS)
- **Audit Logging:** Log all payload exchanges for debugging

### Performance Considerations

- **Batching:** Consider batching multiple updates in single payload
- **Compression:** Use gzip for large payloads
- **Retry Logic:** Implement exponential backoff for failed deliveries
- **Circuit Breaker:** Prevent cascade failures

### Testing Strategy

1. **Unit Tests:** Test individual payload generation
2. **Integration Tests:** Test end-to-end flow with mock Flowtify
3. **Load Tests:** Verify performance under high volume
4. **Validation Tests:** Ensure payload schema compliance

---

## Action Planning

### Top 3 Priority Ideas

**#1 Priority: Implement Status Update Payload**
- **Rationale:** Core functionality for real-time trip tracking
- **Next Steps:** Implement endpoint, test with Flowtify team
- **Resources needed:** Dev time (1-2 days), Flowtify webhook URL
- **Timeline:** Week 1

**#2 Priority: Add Route Geofence Support**
- **Rationale:** Critical for route deviation detection
- **Next steps:** Update trip creation endpoint, update Flowtify payload format
- **Resources needed:** Backend dev, Flowtify frontend updates
- **Timeline:** Week 2

**#3 Priority: Implement Communication Response Payload**
- **Rationale:** Complete the conversation loop with Flowtify UI
- **Next steps:** Generate payloads for bot responses, test delivery
- **Resources needed:** Integration with existing AI processing
- **Timeline:** Week 3

### Development Roadmap

**Phase 1 (Week 1-2): Core Payloads**
- Status update implementation
- Route geofence support
- Basic testing with Flowtify

**Phase 2 (Week 3-4): Enhanced Features**
- Speed violation alerts
- Geofence transition payloads
- Complete end-to-end testing

**Phase 3 (Week 5-6): Advanced Features**
- Route deviation detection
- Communication response system
- Performance optimization

---

## Reflection & Follow-up

### What Worked Well

- Progressive design approach built complexity gradually
- Analysis of existing codebase provided comprehensive data inventory
- Focus on practical, implementable solutions
- Clear separation between different payload types

### Areas for Further Exploration

- **Real-time dashboard integration** with Flowtify
- **Predictive analytics** for ETA calculations
- **Advanced AI models** for better message understanding
- **Mobile optimization** for driver experience

### Recommended Follow-up Techniques

- **API Design Workshop**: Review payload schemas with Flowtify team
- **User Journey Mapping**: Map complete trip lifecycle with integrations
- **Performance Testing**: Stress test payload delivery under load

### Questions That Emerged

- How does Flowtify handle missed/retry events?
- What SLA requirements exist for payload delivery?
- Are there additional data points Flowtify needs for enhanced features?
- How should we handle timezone differences across deployments?

### Next Session Planning

- **Suggested topics:** API contract finalization, error handling strategies, testing protocols
- **Recommended timeframe:** 1 week for initial implementation review
- **Preparation needed:** Coordinate with Flowtify technical team for webhook setup

---

## Technical Specifications

### Payload Schema Standards

**Required Fields for All Payloads:**
- `event`: Event type identifier
- `timestamp`: ISO 8601 timestamp with timezone
- `tenant_id`: Customer/organization identifier
- `trip`: Trip identification information

**Optional Fields:**
- `metadata`: Additional context information
- `wialon_source`: Source event reference
- `trace_id`: Request correlation identifier

### Data Types & Formats

- **Coordinates**: Decimal degrees (WGS84)
- **Speed**: km/h with decimal precision
- **Distances**: Meters for geofence, kilometers for route
- **Timestamps**: ISO 8601 with timezone offset
- **IDs**: UUID format for internal IDs, strings for external IDs

### Status Codes Reference

**Trip Status Values:**
- `planned`: Planificado
- `asignado`: Asignado
- `en_ruta_carga`: En ruta a carga
- `en_zona_carga`: En zona de carga
- `en_ruta_destino`: En ruta a destino
- `en_zona_descarga`: En zona de descarga
- `finalizado`: Finalizado
- `cancelado`: Cancelado

**Geofence Roles:**
- `origin`: Origen del viaje
- `loading`: Zona de carga
- `unloading`: Zona de descarga
- `route`: Corredor/ruta autorizada
- `waypoint`: Punto intermedio
- `depot`: Base/depósito

---

*Session facilitated using the BMAD-METHOD™ brainstorming framework*
*Document generated: 2025-01-10T15:30:45-06:00*