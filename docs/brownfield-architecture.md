# MICROSERVICIO-FLOWTIFY - Documentación Brownfield

## Introducción

Este documento captura el ESTADO ACTUAL del microservicio MICROSERVICIO-FLOWTIFY, incluyendo deuda técnica, workarounds, y patrones reales de implementación. Sirve como referencia para agentes de IA y desarrolladores trabajando en mejoras, correcciones de bugs, refactorización, e implementaciones nuevas.

### Propósito del Proyecto

Microservicio en Python (FastAPI) para automatizar operaciones logísticas en el transporte de 2,500 unidades. Integra múltiples sistemas externos:
- **Floatify**: Sistema de gestión de flotas (fuente de viajes)
- **Wialon**: Sistema de rastreo GPS (eventos de posición, geocercas, telemetría)
- **Evolution API**: Gateway de WhatsApp (comunicación con conductores)
- **Gemini AI**: Inteligencia artificial (transcripción de audio, clasificación de mensajes)

**Estado Actual**: En preparación para producción. Sistema funcional con pruebas E2E realizadas.

### Change Log

| Date       | Version | Description                | Author |
|------------|---------|----------------------------|--------|
| 2025-11-11 | 1.0     | Documentación brownfield inicial | AI Analyst |
| 2025-11-11 | 1.1     | Agregada documentación completa de detección de desvíos de ruta | AI PM |

---

## 🎯 Quick Reference - Archivos Clave y Puntos de Entrada

### Archivos Críticos para Entender el Sistema

- **Entry Point Principal**: `app/main.py` (líneas 1-167)
- **Configuración Centralizada**: `app/config.py` (líneas 1-149)
- **Modelo de Base de Datos**: `SCHEMA BD.sql` (esquema MySQL completo)
- **Constantes del Sistema**: `app/core/constants.py` (líneas 1-99)
- **Documentación de API**: `API_ROUTES.md` (referencia completa de endpoints)

### Servicios Principales (Lógica de Negocio)

| Servicio | Archivo | Responsabilidad |
|----------|---------|-----------------|
| **TripService** | `app/services/trip_service.py` (579 líneas) | Orquestación de viajes completos |
| **EventService** | `app/services/event_service.py` (551 líneas) | Procesamiento de eventos Wialon |
| **MessageService** | `app/services/message_service.py` (425 líneas) | Procesamiento de mensajes WhatsApp + IA |
| **WebhookService** | `app/services/webhook_service.py` (885 líneas) | Envío de webhooks a Flowtify (callbacks) |
| **NotificationService** | `app/services/notification_service.py` | Notificaciones WhatsApp |

### Integraciones Externas

| Sistema | Cliente | Archivo |
|---------|---------|---------|
| **WhatsApp** | EvolutionClient | `app/integrations/evolution/client.py` (458 líneas) |
| **Gemini AI** | GeminiClient | `app/integrations/gemini/client.py` (289 líneas) |
| **Floatify** | FloatifyClient | `app/integrations/floatify/client.py` |
| **Wialon** | Parser | `app/integrations/wialon/parser.py` |

### Rutas API (Endpoints)

| Router | Archivo | Endpoints |
|--------|---------|-----------|
| **Trips** | `app/api/routes/trips.py` | POST /create, GET /{id}, PUT /status, POST /complete |
| **WhatsApp** | `app/api/routes/whatsapp.py` | POST /messages (webhook Evolution API) |
| **Wialon** | `app/api/routes/wialon.py` | POST /events (webhook Wialon) |
| **Health** | `app/api/routes/health.py` | GET /health, /ready, /live |
| **Webhooks** | `app/api/routes/webhooks.py` | Endpoints admin de webhooks |

### Modelos de Datos (Pydantic)

- **Trip**: `app/models/trip.py` - Modelos de viajes (TripCreate, TripUpdate, TripStatusChange)
- **Event**: `app/models/event.py` - Eventos de Wialon (WialonEvent, EventCreate)
- **Message**: `app/models/message.py` - Mensajes WhatsApp (WhatsAppMessage, MessageCreate, GeminiResponse)
- **Unit**: `app/models/unit.py` - Unidades de transporte
- **Driver**: `app/models/driver.py` - Conductores/operadores

---

## 🏗️ Arquitectura de Alto Nivel

### Resumen Técnico

**Tipo**: Microservicio RESTful con webhooks bidireccionales
**Patrón**: Arquitectura en capas (API → Services → Repositories → Database)
**Framework**: FastAPI 0.109.0 (Python 3.11+)
**Base de Datos**: MySQL (XAMPP local para desarrollo, migración a producción pendiente)

### Stack Tecnológico Real

| Categoría | Tecnología | Versión | Notas Importantes |
|-----------|------------|---------|-------------------|
| **Runtime** | Python | 3.11+ | Requerido por tipo hints avanzados |
| **Framework** | FastAPI | 0.109.0 | Web framework asíncrono |
| **ASGI Server** | Uvicorn | 0.27.0 | Con soporte standard (uvloop, httptools) |
| **Base de Datos** | MySQL | 5.5.5-10.4.32-MariaDB | **CRÍTICO**: Debe ser MySQL, no PostgreSQL |
| **Driver MySQL** | aiomysql | 0.2.0 | Async MySQL driver (pool de conexiones) |
| **Driver MySQL (alt)** | PyMySQL | 1.1.0 | Alternativo, no async |
| **HTTP Client** | httpx | 0.26.0 | Para llamadas externas (Evolution, Flowtify) |
| **Logging** | structlog | 24.1.0 | Logs estructurados JSON |
| **Validación** | Pydantic | 2.5.3 | Models + settings |
| **IA** | google-generativeai | 0.3.2 | Gemini API |
| **Testing** | pytest | 7.4.4 | Con pytest-asyncio |
| **Containerización** | Docker | - | docker-compose.yml |

### Diagrama de Flujo de Datos

```
┌─────────────┐          ┌──────────────────────┐
│  Floatify   │─────────▶│   MICROSERVICIO      │
└─────────────┘ (POST)   │   Python (FastAPI)   │
                         │                       │
┌─────────────┐          │  - TripService       │◀──┐
│   Wialon    │─────────▶│  - EventService      │   │
│Notificaciones│ (POST)   │  - MessageService    │   │
└─────────────┘          │  - WebhookService    │   │
                         │  - Gemini AI         │   │
                         └───────┬──────┬───────┘   │
                                 │      │           │
              ┌──────────────────┘      └─────────────┐
              ▼                                        ▼
     ┌────────────────┐                      ┌──────────────┐
     │  Evolution API │                      │     MySQL    │
     │  (WhatsApp)    │                      │(XAMPP Local) │
     └────────┬───────┘                      └──────────────┘
              │
              │ (Transcripción + Clasificación)
              ▼
     ┌────────────────┐
     │   Gemini AI    │
     │  (Audio → Text)│
     │  (Clasificación)│
     └────────────────┘
```

### Estructura del Repositorio (Real)

```
MICROSERVICIO-FLOWTIFY/
├── app/                           # Código fuente principal
│   ├── api/                       # Capa de presentación (FastAPI)
│   │   ├── routes/               # Endpoints REST
│   │   │   ├── health.py         # Health checks
│   │   │   ├── trips.py          # Gestión de viajes
│   │   │   ├── wialon.py         # Webhook Wialon
│   │   │   ├── whatsapp.py       # Webhook Evolution API
│   │   │   └── webhooks.py       # Admin webhooks Flowtify
│   │   ├── dependencies.py       # Inyección de dependencias
│   │   └── middleware.py         # Middleware personalizado
│   │
│   ├── services/                  # Lógica de negocio (CORE)
│   │   ├── trip_service.py       # Orquestación de viajes
│   │   ├── event_service.py      # Procesamiento eventos Wialon
│   │   ├── message_service.py    # Procesamiento mensajes WhatsApp
│   │   ├── webhook_service.py    # Webhooks a Flowtify
│   │   └── notification_service.py # Notificaciones WhatsApp
│   │
│   ├── repositories/              # Acceso a datos (ORM manual)
│   │   ├── base.py               # Repositorio base
│   │   ├── trip_repository.py    # CRUD trips
│   │   ├── event_repository.py   # CRUD events
│   │   ├── message_repository.py # CRUD messages + conversations
│   │   ├── unit_repository.py    # CRUD units
│   │   └── driver_repository.py  # CRUD drivers
│   │
│   ├── integrations/              # Clientes API externos
│   │   ├── evolution/            # WhatsApp (Evolution API)
│   │   │   ├── client.py         # Cliente Evolution API
│   │   │   └── schemas.py        # Modelos Pydantic
│   │   ├── gemini/               # Gemini AI
│   │   │   ├── client.py         # Cliente Gemini
│   │   │   └── prompts.py        # Prompts para clasificación
│   │   ├── floatify/             # Floatify (callbacks)
│   │   │   └── client.py
│   │   └── wialon/               # Wialon (parsing)
│   │       └── parser.py
│   │
│   ├── models/                    # Modelos Pydantic (DTOs)
│   │   ├── trip.py               # TripCreate, TripUpdate, etc.
│   │   ├── event.py              # WialonEvent, EventCreate
│   │   ├── message.py            # WhatsAppMessage, GeminiResponse
│   │   ├── unit.py               # UnitCreate, UnitUpdate
│   │   ├── driver.py             # DriverCreate, DriverUpdate
│   │   ├── webhooks.py           # Modelos de webhooks
│   │   └── responses.py          # Respuestas API estándar
│   │
│   ├── core/                      # Núcleo del sistema
│   │   ├── database_mysql.py     # Conexión MySQL (aiomysql) ⚠️
│   │   ├── database.py           # Interface Database (abstracta)
│   │   ├── logging.py            # Logging estructurado (structlog)
│   │   ├── errors.py             # Excepciones personalizadas
│   │   ├── constants.py          # Constantes del sistema
│   │   ├── context.py            # Context logging
│   │   └── resilience.py         # Retry, circuit breaker
│   │
│   ├── utils/                     # Utilidades
│   │   ├── helpers.py            # Funciones auxiliares
│   │   └── validators.py         # Validadores custom
│   │
│   ├── config.py                  # Configuración (Pydantic Settings)
│   └── main.py                    # Entry point (FastAPI app)
│
├── scripts/                       # Scripts de utilidad
│   ├── setup_windows.bat         # Setup en Windows
│   ├── backup_database.sh        # Backup MySQL
│   ├── apply_migration.sh        # Aplicar migraciones
│   ├── clean_database_fast.py    # Limpiar BD para tests
│   └── verify_setup.py           # Verificar setup
│
├── tests/                         # Tests (pytest)
│   ├── conftest.py               # Fixtures pytest
│   ├── services/
│   │   └── test_webhook_service.py
│   └── test_webhook_integration_e2e.py
│
├── migrations/                    # Migraciones SQL (manual)
│   └── 001_webhook_tables.sql    # Tablas de webhooks
│
├── docs/                          # Documentación
│   └── brownfield-architecture.md # Este documento
│
├── EXTRA/                         # Scripts adicionales y respaldos
│   ├── code/                     # Scripts de setup y tracking
│   ├── respaldos-bd/             # Backups de base de datos
│   └── scripts/                  # 55 scripts de utilidad
│
├── backup/                        # Backups
│   └── units_backup_20251105_100053.sql
│
├── requirements.txt               # Dependencias Python
├── Dockerfile                     # Imagen Docker
├── docker-compose.yml             # Orquestación Docker
├── pytest.ini                     # Config pytest
├── README.md                      # README principal
├── API_ROUTES.md                  # Documentación de rutas
├── SCHEMA BD.sql                  # Schema completo MySQL
├── e2e_test_log.txt              # Log de pruebas E2E
└── check_*.py                     # Scripts de verificación

Notas:
- NO hay archivo .env (debe crearse manualmente)
- Patrón: 39 archivos .py en EXTRA/scripts
- Total: ~15-20K líneas de código Python
```

---

## 📊 Modelos de Datos y API

### Base de Datos MySQL - Tablas Principales

**IMPORTANTE**: El sistema usa MySQL, NO PostgreSQL. Aunque existe `database.py` y `database_mysql.py`, solo MySQL está implementado.

#### Tabla: `trips` (Viajes)

```sql
CREATE TABLE `trips` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `floatify_trip_id` varchar(100) DEFAULT NULL,  -- Código del viaje desde Floatify
  `tenant_id` int(11) NOT NULL DEFAULT 24,
  `unit_id` varchar(36) DEFAULT NULL,
  `driver_id` varchar(36) DEFAULT NULL,
  `customer_id` varchar(36) DEFAULT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'pending',
  `substatus` varchar(100) NOT NULL DEFAULT 'por_iniciar',
  `origin` varchar(255) DEFAULT NULL,
  `destination` varchar(255) DEFAULT NULL,
  `cargo_description` text DEFAULT NULL,
  `planned_start` datetime DEFAULT NULL,
  `planned_end` datetime DEFAULT NULL,
  `actual_start` datetime DEFAULT NULL,
  `actual_end` datetime DEFAULT NULL,
  `whatsapp_group_id` varchar(255) DEFAULT NULL,
  `whatsapp_group_name` varchar(255) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_trips_floatify_trip_id` (`floatify_trip_id`),
  KEY `idx_trips_tenant_id` (`tenant_id`),
  KEY `idx_trips_status` (`status`),
  KEY `idx_trips_unit_id` (`unit_id`),
  CONSTRAINT `trips_ibfk_1` FOREIGN KEY (`unit_id`) REFERENCES `units` (`id`) ON DELETE SET NULL,
  CONSTRAINT `trips_ibfk_2` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Status Values (de `app/core/constants.py`)**:
- `planned`, `asignado`, `en_ruta_carga`, `en_zona_carga`, `en_ruta_destino`, `en_zona_descarga`, `finalizado`, `cancelado`

**Substatus Values**:
- `por_iniciar`, `esperando_inicio_carga`, `cargando`, `carga_completada`, `rumbo_a_descarga`, `esperando_inicio_descarga`, `descargando`, `descarga_completada`, `entregado_confirmado`

#### Tabla: `units` (Unidades de Transporte)

```sql
CREATE TABLE `units` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `floatify_unit_id` varchar(50) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `plate` varchar(20) DEFAULT NULL,
  `wialon_id` varchar(50) DEFAULT NULL,
  `imei` varchar(50) DEFAULT NULL,
  `provider` varchar(50) DEFAULT 'wialon',
  `whatsapp_group_id` varchar(255) DEFAULT NULL,  -- ⚠️ Grupo compartido por TODOS los viajes de esta unidad
  `whatsapp_group_name` varchar(255) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_units_floatify_unit_id` (`floatify_unit_id`),
  UNIQUE KEY `idx_units_wialon_id` (`wialon_id`),
  KEY `idx_whatsapp_group` (`whatsapp_group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**⚠️ PATRÓN CRÍTICO**: Los grupos de WhatsApp están ahora vinculados a la **UNIDAD**, no al viaje individual. Esto permite reutilizar el mismo grupo para múltiples viajes consecutivos de la misma unidad.

#### Tabla: `drivers` (Conductores)

```sql
CREATE TABLE `drivers` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `name` varchar(255) NOT NULL,
  `phone` varchar(20) NOT NULL,
  `floatify_driver_id` varchar(50) DEFAULT NULL,
  `wialon_driver_code` varchar(100) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `wialon_driver_code` (`wialon_driver_code`),
  UNIQUE KEY `idx_drivers_floatify_driver_id` (`floatify_driver_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Tabla: `events` (Eventos de Wialon)

```sql
CREATE TABLE `events` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `wialon_notification_id` varchar(255) DEFAULT NULL,  -- Para idempotencia
  `trip_id` varchar(36) DEFAULT NULL,
  `unit_id` varchar(36) DEFAULT NULL,
  `event_type` varchar(100) NOT NULL,
  `event_time` bigint(20) NOT NULL,
  `latitude` decimal(10,7) NOT NULL,
  `longitude` decimal(10,7) NOT NULL,
  `altitude` decimal(8,2) DEFAULT NULL,
  `speed` decimal(6,2) DEFAULT NULL,
  `course` int(11) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `geofence_id` varchar(36) DEFAULT NULL,
  `raw_payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`raw_payload`)),
  `processed` tinyint(1) DEFAULT 0,
  `processed_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_events_wialon_notification_id` (`wialon_notification_id`),
  KEY `idx_trip` (`trip_id`),
  KEY `idx_unit` (`unit_id`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_event_time` (`event_time`),
  CONSTRAINT `events_ibfk_1` FOREIGN KEY (`trip_id`) REFERENCES `trips` (`id`) ON DELETE CASCADE,
  CONSTRAINT `events_ibfk_2` FOREIGN KEY (`unit_id`) REFERENCES `units` (`id`) ON DELETE SET NULL,
  CONSTRAINT `events_ibfk_3` FOREIGN KEY (`geofence_id`) REFERENCES `geofences` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Event Types (de `app/core/constants.py`)**:
- `geofence_entry`, `geofence_exit`, `speed_violation`, `panic_button`, `connection_lost`, `route_deviation`

#### Tabla: `messages` (Mensajes WhatsApp)

```sql
CREATE TABLE `messages` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `conversation_id` varchar(36) NOT NULL,
  `trip_id` varchar(36) NOT NULL,
  `whatsapp_message_id` varchar(255) DEFAULT NULL,
  `sender_type` varchar(50) NOT NULL,
  `sender_phone` varchar(20) DEFAULT NULL,
  `direction` varchar(20) NOT NULL,
  `content` text NOT NULL,
  `transcription` text DEFAULT NULL,  -- Para audios transcritos
  `ai_result` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`ai_result`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_conversation` (`conversation_id`),
  KEY `idx_trip` (`trip_id`),
  KEY `idx_sender_type` (`sender_type`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`trip_id`) REFERENCES `trips` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Sender Types**: `driver`, `bot`, `supervisor`, `system`  
**Directions**: `inbound`, `outbound`

#### Tabla: `conversations` (Conversaciones WhatsApp)

```sql
CREATE TABLE `conversations` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `trip_id` varchar(36) NOT NULL,
  `driver_id` varchar(36) DEFAULT NULL,
  `whatsapp_group_id` varchar(255) DEFAULT NULL,
  `status` varchar(50) DEFAULT 'active',
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_trip` (`trip_id`),
  KEY `idx_driver` (`driver_id`),
  KEY `idx_whatsapp_group` (`whatsapp_group_id`),
  CONSTRAINT `conversations_ibfk_1` FOREIGN KEY (`trip_id`) REFERENCES `trips` (`id`) ON DELETE CASCADE,
  CONSTRAINT `conversations_ibfk_2` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Tabla: `ai_interactions` (Interacciones IA)

```sql
CREATE TABLE `ai_interactions` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `message_id` varchar(36) DEFAULT NULL,
  `trip_id` varchar(36) DEFAULT NULL,
  `driver_message` text NOT NULL,
  `ai_classification` varchar(100) DEFAULT NULL,
  `ai_confidence` decimal(5,4) DEFAULT NULL,
  `ai_response` text DEFAULT NULL,
  `model_used` varchar(100) DEFAULT NULL,
  `prompt_used` text DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_message` (`message_id`),
  KEY `idx_trip` (`trip_id`),
  KEY `idx_classification` (`ai_classification`),
  CONSTRAINT `ai_interactions_ibfk_1` FOREIGN KEY (`message_id`) REFERENCES `messages` (`id`) ON DELETE SET NULL,
  CONSTRAINT `ai_interactions_ibfk_2` FOREIGN KEY (`trip_id`) REFERENCES `trips` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Tabla: `geofences` (Geocercas)

```sql
CREATE TABLE `geofences` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `floatify_geofence_id` varchar(100) DEFAULT NULL,
  `wialon_geofence_id` varchar(100) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `geofence_type` varchar(50) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_geofences_floatify_geofence_id` (`floatify_geofence_id`),
  KEY `idx_wialon_geofence_id` (`wialon_geofence_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Tabla: `trip_geofences` (Relación Viaje-Geocercas)

```sql
CREATE TABLE `trip_geofences` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `trip_id` varchar(36) NOT NULL,
  `geofence_id` varchar(36) NOT NULL,
  `sequence_order` int(11) DEFAULT NULL,
  `visit_type` varchar(50) DEFAULT NULL,  -- 'origin', 'loading', 'unloading', 'waypoint', 'route'
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_trip` (`trip_id`),
  KEY `idx_geofence` (`geofence_id`),
  CONSTRAINT `trip_geofences_ibfk_1` FOREIGN KEY (`trip_id`) REFERENCES `trips` (`id`) ON DELETE CASCADE,
  CONSTRAINT `trip_geofences_ibfk_2` FOREIGN KEY (`geofence_id`) REFERENCES `geofences` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Tablas de Webhooks (para Flowtify)

```sql
-- Log de entregas de webhooks
CREATE TABLE `webhook_delivery_log` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `webhook_type` varchar(100) NOT NULL,
  `trip_id` varchar(36) DEFAULT NULL,
  `payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payload`)),
  `target_url` varchar(500) NOT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'pending',
  `retry_count` int(11) DEFAULT 0,
  `last_error` text DEFAULT NULL,
  `delivered_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_webhook_type` (`webhook_type`),
  KEY `idx_trip_id` (`trip_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dead Letter Queue para webhooks fallidos
CREATE TABLE `webhook_dead_letter_queue` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `original_delivery_log_id` varchar(36) NOT NULL,
  `webhook_type` varchar(100) NOT NULL,
  `trip_id` varchar(36) DEFAULT NULL,
  `payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payload`)),
  `target_url` varchar(500) NOT NULL,
  `failure_reason` text DEFAULT NULL,
  `retry_count` int(11) DEFAULT 0,
  `last_attempt_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_webhook_type` (`webhook_type`),
  KEY `idx_trip_id` (`trip_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### API Specifications

**Ver archivo completo**: `API_ROUTES.md` (404 líneas)

Todos los endpoints están bajo el prefijo `/api/v1` (configurable).

**Endpoints principales**:
- `POST /trips/create` - Crear viaje completo (desde Floatify)
- `GET /trips/{trip_id}` - Obtener viaje
- `PUT /trips/{trip_id}/status` - Actualizar estado
- `POST /trips/{trip_id}/complete` - Completar viaje
- `POST /whatsapp/messages` - Webhook Evolution API
- `POST /wialon/events` - Webhook Wialon
- `GET /health`, `/health/detailed`, `/health/ready`, `/health/live` - Health checks

---

## 🚨 Deuda Técnica y Problemas Conocidos

### 1. **Base de Datos: Dual Support MySQL/PostgreSQL (Incompleto)**

**Archivos Afectados**:
- `app/core/database.py` - Interface Database abstracta (no usada)
- `app/core/database_mysql.py` - Implementación MySQL (usada)
- `app/config.py` - Líneas 30-48 (configuración de ambas BDs)

**Problema**: El código tiene configuración para PostgreSQL (Supabase) Y MySQL, pero SOLO MySQL está implementado.

```python
# app/config.py (líneas 30-38)
# Database Selection
db_type: str = "mysql"  # "mysql" o "postgres"  ⚠️ Solo MySQL funciona

# MySQL (XAMPP Local)
mysql_host: str = "localhost"
mysql_port: int = 3307
mysql_database: str = "logistics_db"
mysql_user: str = "root"
mysql_password: str = ""

# Supabase Database (PostgreSQL) - NO IMPLEMENTADO
supabase_db_host: str = ""  # Nunca se usa
```

**Workaround Actual**: Siempre usar `db_type="mysql"` y NO cambiar a `postgres`.

**Recomendación**: Eliminar código de PostgreSQL si no se va a implementar, o completar la implementación.

---

### 2. **Sistema de Repositorios: No es un ORM Real**

**Archivos Afectados**: `app/repositories/*.py`

**Problema**: Los "repositorios" son wrappers muy delgados sobre SQL crudo. No hay abstracción real, mapeo objeto-relacional, ni validación de datos a nivel de repositorio.

**Ejemplo real** (`trip_repository.py`, líneas 20-35):

```python
async def find_by_id(self, trip_id: str) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM trips WHERE id = %s"
    result = await self.db.fetchrow(query, trip_id)
    return dict(result) if result else None
```

**Implicaciones**:
- SQL manual en todos lados (propenso a errores)
- Sin protección contra SQL injection (aunque se usan parámetros)
- Sin validación de esquema antes de insertar
- Difícil de testear sin base de datos real

**Workaround Actual**: Validar con Pydantic ANTES de llamar al repositorio.

**Recomendación**: Considerar SQLAlchemy async o Tortoise ORM para futuras implementaciones.

---

### 3. **Grupos de WhatsApp: Cambio de Arquitectura Reciente**

**Archivos Afectados**:
- `app/services/trip_service.py` (líneas 110-246)
- `app/models/unit.py` (líneas 17-18)

**Problema Histórico**: Originalmente, cada viaje creaba su propio grupo de WhatsApp. Esto generaba:
- Múltiples grupos por unidad (confusión para operadores)
- Necesidad de agregar participantes a cada grupo nuevo
- Grupos "huérfanos" al terminar viajes

**Solución Implementada** (noviembre 2024): Grupos vinculados a **unidades**, no a viajes individuales.

**Patrón CRÍTICO** (`trip_service.py`, líneas 116-195):

```python
# 5.1 Verificar si la unidad YA tiene un grupo asignado
existing_group_id = unit.get("whatsapp_group_id")

if not existing_group_id:
    # CASO A: NO HAY GRUPO - CREAR UNO NUEVO
    group_name = f"Unidad {unit.get('name')}"
    group_result = await self.evolution_client.create_group(...)
    whatsapp_group_id = group_result.get("id")
    
    # Guardar el grupo en la UNIDAD
    await self.unit_repo.update(unit["id"], {
        "whatsapp_group_id": whatsapp_group_id,
        "whatsapp_group_name": group_name
    })
else:
    # CASO B: HAY GRUPO - REUTILIZARLO
    whatsapp_group_id = existing_group_id
    
    # Agregar nuevos participantes si hay
    await self.evolution_client.add_participants(...)
```

**Advertencia**: Si se intenta abandonar un grupo compartido, el método `cleanup_trip_group` lo detecta y lo bloquea (líneas 503-520).

---

### 4. **WebhookService: Circuit Breaker Implementado Manualmente**

**Archivo**: `app/services/webhook_service.py` (líneas 33-99)

**Problema**: Implementación manual de circuit breaker en lugar de usar librería probada.

```python
class CircuitBreaker:
    """Circuit Breaker simple para prevenir cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "closed"  # closed, open, half_open
```

**Estados**:
- `closed`: Normal (permite requests)
- `open`: Rechaza requests después de threshold de fallos
- `half_open`: Intenta recuperarse con request de prueba

**Workaround**: Funciona, pero no tiene persistencia, métricas, ni configuración dinámica.

**Recomendación**: Usar `pybreaker` o `circuitbreaker` en futuras versiones.

---

### 5. **Logging: Mezcla de Structlog y Print Statements**

**Archivos Afectados**: Múltiples servicios

**Problema**: Aunque se usa `structlog` para logging estructurado, hay `print()` y `sys.stdout.write()` en código de producción.

**Ejemplo** (`event_service.py`, líneas 35-42):

```python
# DEBUG - Forzar print a consola
import sys
sys.stdout.write("=" * 80 + "\n")
sys.stdout.write("EventService INITIALIZED\n")
sys.stdout.write(f"  webhook_service: {webhook_service}\n")
sys.stdout.write(f"  webhook_service is None: {webhook_service is None}\n")
sys.stdout.write("=" * 80 + "\n")
sys.stdout.flush()
```

**Implicaciones**:
- Logs no estructurados mezclados con logs JSON
- Dificulta parseo por herramientas de observabilidad
- Afecta rendimiento (especialmente `flush()`)

**Recomendación**: Eliminar todos los `print()` y usar solo `logger.debug()`.

---

### 6. **Gemini AI: Dependencia de Formato de Respuesta JSON**

**Archivo**: `app/integrations/gemini/client.py` (líneas 35-88)

**Problema**: La clasificación de mensajes depende de que Gemini devuelva JSON válido. Si Gemini devuelve texto plano o markdown, el parseo falla.

```python
# Limpiar markdown si existe
if "```json" in text_response:
    text_response = text_response.split("```json")[1].split("```")[0]
elif "```" in text_response:
    text_response = text_response.split("```")[1].split("```")[0]

# Parsear JSON
try:
    result = json.loads(text_response.strip())
    return result
except json.JSONDecodeError as e:
    # Retornar respuesta por defecto
    return {
        "intent": "other",
        "confidence": 0.5,
        "response": "Entendido. ¿Puedes darme más detalles?",
        "action": "no_action",
        "new_substatus": None,
    }
```

**Workaround**: Tiene fallback, pero se pierde la clasificación real.

**Recomendación**: Usar Gemini Function Calling o structured output (disponible en versiones recientes).

---

### 7. **Evolution API: Sin Manejo de Versiones**

**Archivo**: `app/integrations/evolution/client.py`

**Problema**: El cliente asume una versión específica de Evolution API. Si cambia la API, puede romperse.

**Endpoints que pueden fallar**:
- `start_typing()` / `stop_typing()` (líneas 338-456) - Endpoints de presencia son opcionales
- `leave_group()` (líneas 281-336) - Formato puede variar según versión

**Workaround Actual**: Los métodos de presencia (`start_typing`, `stop_typing`) no lanzan excepciones si fallan, solo loguean.

```python
except Exception as e:
    logger.warning("typing_indicator_start_error", error=str(e), number=number)
    # No lanzar excepción - el indicador de typing es opcional
```

---

### 8. **Eventos Wialon: Parsing Flexible pero Frágil**

**Archivo**: `app/api/routes/wialon.py`

**Problema**: Wialon puede enviar eventos en múltiples formatos (JSON, form-encoded, text/plain). El sistema intenta parsear todos, pero puede fallar con formatos inesperados.

**Workaround** (líneas 40-80):

```python
# Intentar obtener datos de múltiples fuentes
if content_type == "application/json":
    data = await request.json()
elif content_type == "application/x-www-form-urlencoded":
    form_data = await request.form()
    data = dict(form_data)
else:
    # Intentar JSON en body raw
    body = await request.body()
    try:
        data = json.loads(body)
    except:
        data = {}
```

**Recomendación**: Definir un contrato estricto con Wialon o usar webhook intermediario.

---

## 🔌 Integraciones y Puntos de Integración

### 1. Evolution API (WhatsApp Gateway)

**Cliente**: `app/integrations/evolution/client.py` (458 líneas)

**Configuración** (`app/config.py`, líneas 50-53):

```python
evolution_api_url: str = ""  # Opcional para testing
evolution_api_key: str = ""  # Opcional para testing
evolution_instance_name: str = "SATECH"
```

**Métodos Principales**:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `send_text()` | POST `/message/sendText/{instance}` | Enviar mensaje de texto |
| `send_audio()` | POST `/message/sendWhatsAppAudio/{instance}` | Enviar audio |
| `create_group()` | POST `/group/create/{instance}` | Crear grupo de WhatsApp |
| `add_participants()` | POST `/group/updateParticipant/{instance}` | Agregar participantes |
| `leave_group()` | DELETE `/group/leaveGroup/{instance}` | Abandonar grupo |
| `download_media()` | GET `{media_url}` | Descargar audio/imagen |
| `start_typing()` | POST `/chat/presence/{instance}` | Indicador "escribiendo..." |
| `stop_typing()` | POST `/chat/presence/{instance}` | Detener indicador |

**Configuración HTTP** (líneas 18-19):

```python
HTTPX_LIMITS = httpx.Limits(max_keepalive_connections=5, max_connections=10)
HTTPX_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
```

**Workarounds Críticos**:
- `trust_env=False` - Evita problemas de proxy en Windows
- `http2=False` - HTTP/1.1 por compatibilidad
- `verify=True` - SSL verificado

**Gotchas**:
- Los números deben estar en formato `+5214771234567@s.whatsapp.net`
- Los grupos tienen formato `120363405870310803@g.us`
- El método `create_group()` normaliza la respuesta para agregar `id` si solo viene `groupId` (líneas 165-166)

---

### 2. Gemini AI (Google Generative AI)

**Cliente**: `app/integrations/gemini/client.py` (289 líneas)

**Configuración** (`app/config.py`, líneas 55-57):

```python
gemini_api_key: str = ""  # Opcional para testing
gemini_model: str = "gemini-2.5-flash"
```

**Métodos Principales**:

| Método | Descripción | Uso |
|--------|-------------|-----|
| `classify_message()` | Clasificar mensaje del conductor | Intención, confianza, respuesta, acción |
| `transcribe_audio()` | Transcribir audio a texto | STT (Speech-to-Text) |
| `generate_response()` | Generar respuesta libre | No usado actualmente |

**Clasificación de Mensajes** (líneas 35-88):

```python
async def classify_message(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retorna:
    {
        "intent": "loading_started",      # Intención detectada
        "confidence": 0.95,               # Confianza (0-1)
        "entities": {},                   # Entidades extraídas
        "response": "...",                # Respuesta para el conductor
        "action": "update_substatus",     # Acción a realizar
        "new_substatus": "cargando"       # Nuevo subestado (si aplica)
    }
    """
```

**Intents Detectados** (de `app/core/constants.py`):
- `waiting_turn`, `loading_started`, `loading_complete`
- `unloading_started`, `unloading_complete`
- `route_update`, `issue_report`, `other`

**Transcripción de Audio** (líneas 90-189):

```python
async def transcribe_audio(
    self, 
    audio_data: bytes, 
    mime_type: str = "audio/ogg",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Formatos soportados: WAV, MP3, AIFF, AAC, OGG, FLAC
    
    Usa inline_data con base64 para enviar audio a Gemini
    """
```

**Gotchas**:
- Gemini no tiene API async nativa (usa sync bloqueante)
- El audio debe ser base64-encoded
- La transcripción usa temperatura muy baja (0.1) para literalidad
- Los prompts están en `app/integrations/gemini/prompts.py`

---

### 3. Wialon (Sistema de Rastreo GPS)

**Parser**: `app/integrations/wialon/parser.py`

**Webhook Receptor**: `app/api/routes/wialon.py`

**Formato de Eventos** (form-urlencoded):

```
unit_name=Torton 309 41BB3T
unit_id=27538728
imei=863719067169228
latitude=21.0505
longitude=-101.7995
speed=6.2
address=ZONA DE CARGA - PLANTA ACME
geofence_name=PLANTA ACME - ZONA CARGA
geofence_id=9001
notification_type=geofence_entry
notification_id=NOTIF_1728280100_1234
event_time=1728280100
```

**Tipos de Eventos**:
- `geofence_entry` - Entrada a geocerca
- `geofence_exit` - Salida de geocerca
- `speed_violation` - Exceso de velocidad
- `panic_button` - Botón de pánico
- `connection_lost` - Pérdida de conexión
- `route_deviation` - Desviación de ruta

**Procesamiento** (`event_service.py`, líneas 50-271):

1. Buscar viaje activo por `wialon_id` de la unidad
2. Registrar evento en BD (con idempotencia vía `notification_id`)
3. Determinar acción según tipo de evento
4. Actualizar estado del viaje si es necesario
5. Enviar notificación WhatsApp si aplica
6. Enviar webhook a Flowtify

**Idempotencia**: Usa `wialon_notification_id` como UNIQUE KEY para evitar duplicados.

---

### 4. Floatify (Sistema de Gestión de Flotas)

**Callbacks (Webhooks a Flowtify)**: `app/services/webhook_service.py` (885 líneas)

**Configuración** (`app/config.py`, líneas 81-87):

```python
flowtify_webhook_url: Optional[str] = None
webhook_retry_max: int = 5
webhook_timeout: int = 30
webhook_circuit_breaker_threshold: int = 5
webhook_circuit_breaker_timeout: int = 60
webhooks_enabled: bool = True
webhooks_enabled_tenants: str = "24"  # Comma-separated tenant IDs
```

**Tipos de Webhooks Enviados**:

| Tipo | Endpoint | Cuándo se Envía |
|------|----------|-----------------|
| `status_update` | POST `/status-update` | Cambio de estado/substatus de viaje |
| `speed_violation` | POST `/speed-violation` | Evento de exceso de velocidad |
| `geofence_transition` | POST `/geofence-transition` | Entrada/salida de geocerca |
| `route_deviation` | POST `/route-deviation` | Desviación de ruta detectada por Wialon |
| `communication_response` | POST `/communication-response` | Respuesta del bot de WhatsApp |

**⚠️ IMPORTANTE - Detección de Desvíos de Ruta**:
- Para que Wialon detecte desvíos, **DEBE definirse una geofence de tipo "route"** en el payload de creación de viaje
- La geofence de ruta representa el corredor/trayecto esperado entre origen y destino
- Wialon genera un evento `route_deviation` cuando la unidad sale fuera del corredor definido
- El webhook incluye: `deviation_distance` (metros), `deviation_duration` (segundos), y ubicación actual

**Seguridad**: Los webhooks se firman con HMAC SHA256 (líneas 149-169):

```python
def _generate_signature(self, payload: str) -> str:
    signature = hmac.new(
        self.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature

# Headers enviados
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Signature": signature,
    "X-Webhook-Type": webhook_type,
    "X-Webhook-Timestamp": str(int(datetime.now(timezone.utc).timestamp())),
}
```

**Retry y Circuit Breaker**:
- Retry automático: 5 intentos con backoff exponencial (tenacity)
- Circuit breaker: Abre después de 5 fallos consecutivos, timeout 60s
- Dead Letter Queue: Webhooks fallidos van a tabla `webhook_dead_letter_queue`

**Logging de Entregas**: Todos los webhooks se loguean en `webhook_delivery_log` con:
- Payload completo
- URL destino
- Status (`pending`, `sent`, `failed`)
- Retry count
- Error message (si falla)

---

## 🔄 Flujos Principales del Sistema

### Flujo 1: Creación de Viaje Completo (desde Floatify)

**Endpoint**: `POST /api/v1/trips/create`  
**Servicio**: `TripService.create_trip_from_floatify()` (líneas 38-296)

```
┌─────────────┐
│  Floatify   │ POST /trips/create (payload completo)
└──────┬──────┘
       │
       v
┌──────────────────────────────────────────────────┐
│ TripService.create_trip_from_floatify()         │
├──────────────────────────────────────────────────┤
│ 1. Upsert Unidad (by floatify_unit_id)         │
│    - unit_repo.upsert(unit_data)                │
│                                                  │
│ 2. Upsert Conductor (by phone)                  │
│    - driver_repo.upsert(driver_data)            │
│                                                  │
│ 3. Crear Viaje                                   │
│    - trip_repo.create_full_trip(trip_data)      │
│                                                  │
│ 4. Crear Geocercas y Asociarlas                 │
│    - INSERT geofences (con ON DUPLICATE KEY)    │
│    - INSERT trip_geofences (asociación)         │
│                                                  │
│ 5. Obtener/Crear Grupo WhatsApp (UNIDAD)        │
│    ┌─────────────────────────────────────┐     │
│    │ existing_group = unit.whatsapp_group_id│   │
│    │                                       │     │
│    │ if not existing_group:                │     │
│    │   • create_group(nombre_unidad)       │     │
│    │   • update unit.whatsapp_group_id     │     │
│    │ else:                                 │     │
│    │   • reutilizar grupo existente        │     │
│    │   • add_participants() si hay nuevos  │     │
│    └─────────────────────────────────────┘     │
│                                                  │
│ 6. Actualizar trip.whatsapp_group_id            │
│    - Mantiene compatibilidad con otros servicios│
│                                                  │
│ 7. Crear Conversación                            │
│    - conversation_repo.create_conversation()    │
│                                                  │
│ 8. Enviar Mensaje de Bienvenida                 │
│    - evolution_client.send_text()               │
│    - Mensaje contextual (grupo nuevo vs reuso)  │
└──────────────────────────────────────────────────┘
       │
       v
   Response:
   {
     "success": true,
     "trip_id": "...",
     "trip_code": "...",
     "whatsapp_group_id": "...",
     "welcome_message_sent": true
   }
```

**Detalles Críticos**:

1. **Upsert**: Usa `ON DUPLICATE KEY UPDATE` para evitar duplicados
2. **Grupos compartidos**: Un grupo por unidad, no por viaje
3. **Orden de operaciones**: DEBE seguirse este orden (unidad → conductor → viaje → geocercas → grupo → conversación)
4. **Error handling**: Si falla el grupo WhatsApp, el viaje se crea igual (no es crítico)
5. **Metadata**: Se preserva metadata original de Floatify en campo JSON

**Ejemplo de Payload con Geofence de Ruta** (para detección de desvíos):

```json
{
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
      "geofence_id": "9003",
      "geofence_name": "RUTA CARRETERA LEON-GUADALAJARA",
      "geofence_type": "polygon",
      "order": 2
    },
    {
      "role": "unloading",
      "geofence_id": "9002",
      "geofence_name": "BODEGA COPPEL JALISCO",
      "geofence_type": "polygon",
      "order": 3
    }
  ]
}
```

**Nota**: La geofence con `role: "route"` define el corredor esperado. Sin esta geofence, Wialon NO podrá detectar desvíos de ruta.

---

### Flujo 2: Procesamiento de Evento Wialon

**Endpoint**: `POST /api/v1/wialon/events`  
**Servicio**: `EventService.process_wialon_event()` (líneas 50-271)

```
┌─────────────┐
│   Wialon    │ POST /wialon/events (form-urlencoded)
└──────┬──────┘
       │
       v
┌──────────────────────────────────────────────────┐
│ EventService.process_wialon_event()             │
├──────────────────────────────────────────────────┤
│ 1. Buscar Viaje Activo                           │
│    - trip_repo.find_active_by_wialon_id()       │
│    - Si no hay viaje activo → retornar OK        │
│                                                  │
│ 2. Buscar Unit en BD                             │
│    - unit_repo.find_by_wialon_id()              │
│                                                  │
│ 3. Resolver Geofence ID (si aplica)             │
│    - Buscar en BD por wialon_geofence_id        │
│    - Necesario para foreign key                 │
│                                                  │
│ 4. Registrar Evento (con Idempotencia)          │
│    - event_repo.create_event()                  │
│    - UNIQUE: wialon_notification_id             │
│    - Si duplicado → retornar evento existente   │
│                                                  │
│ 5. Determinar Acción                             │
│    ┌─────────────────────────────────────┐     │
│    │ _determine_action(event, trip)      │     │
│    │                                     │     │
│    │ geofence_entry:                     │     │
│    │   • Detectar role (loading/unloading)│    │
│    │   • Actualizar status a zona_carga  │     │
│    │   • Enviar notificación WhatsApp    │     │
│    │                                     │     │
│    │ geofence_exit:                      │     │
│    │   • Actualizar status a en_ruta     │     │
│    │                                     │     │
│    │ speed_violation:                    │     │
│    │   • Enviar alerta WhatsApp          │     │
│    │   • Enviar webhook a Flowtify       │     │
│    │                                     │     │
│    │ route_deviation:                    │     │
│    │   • Enviar alerta WhatsApp crítica  │     │
│    │   • Enviar webhook route_deviation  │     │
│    │   • NO actualiza status del viaje   │     │
│    │   • Incluye datos de desviación     │     │
│    │                                     │     │
│    │ panic_button, connection_lost:      │     │
│    │   • Alerta crítica WhatsApp         │     │
│    └─────────────────────────────────────┘     │
│                                                  │
│ 6. Actualizar Estado del Viaje (si aplica)      │
│    - trip_repo.update_status()                  │
│                                                  │
│ 7. Enviar Notificación WhatsApp (si aplica)     │
│    - evolution_client.send_text()               │
│                                                  │
│ 8. Enviar Webhooks a Flowtify                   │
│    ┌─────────────────────────────────────┐     │
│    │ webhook_service.send_*()            │     │
│    │                                     │     │
│    │ • speed_violation                   │     │
│    │ • geofence_transition               │     │
│    │ • route_deviation                   │     │
│    │                                     │     │
│    │ Con retry + circuit breaker         │     │
│    └─────────────────────────────────────┘     │
│                                                  │
│ 9. Marcar Evento como Procesado                 │
│    - event_repo.mark_as_processed()             │
└──────────────────────────────────────────────────┘
       │
       v
   Response: 200 OK (siempre, para evitar reintentos de Wialon)
```

**Detalles Críticos**:

1. **Idempotencia**: `wialon_notification_id` evita procesar el mismo evento dos veces
2. **Detección de Geofence Role**: Primero busca en BD (tabla `trip_geofences`), luego fallback a detección por nombre
3. **Retorno 200 siempre**: Incluso si falla, retorna 200 para que Wialon no reenvíe
4. **Webhooks no bloqueantes**: Si falla el webhook, el evento se procesa igual

**Ejemplo de Webhook `route_deviation` enviado a Flowtify**:

```json
{
  "event": "route_deviation",
  "timestamp": "2025-11-11T15:33:24.888905+00:00",
  "tenant_id": 24,
  "trip": {
    "id": "adce7b29-bf13-11f0-b6e4-f4b5205b5b70",
    "floatify_trip_id": "TEST_FLOW_20251111093235",
    "code": "TEST_FLOW_20251111093235",
    "status": "en_ruta_destino",
    "substatus": "rumbo_a_descarga"
  },
  "driver": {
    "id": "a09395bc-bf11-11f0-b6e4-f4b5205b5b70",
    "name": "PRUEBA_FLOWTIFY",
    "phone": "+5214775589835"
  },
  "unit": {
    "id": "a092d0e0-bf11-11f0-b6e4-f4b5205b5b70",
    "name": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728"
  },
  "deviation": {
    "distance_meters": 8500,
    "duration_seconds": 480,
    "geofence_id": "9003",
    "geofence_name": "RUTA CARRETERA LEON-GUADALAJARA"
  },
  "location": {
    "latitude": 20.9234,
    "longitude": -102.1567,
    "address": "Carretera Alterna León-Aguascalientes, Km 45",
    "speed": 65.3
  },
  "wialon_source": {
    "notification_id": "NOTIF_1762875201_9158",
    "notification_type": "route_deviation"
  },
  "workflow_triggers": {
    "supervisor_alert": true,
    "whatsapp_notification_enabled": true
  }
}
```

**Nota**: El webhook incluye `deviation.distance_meters` y `deviation.duration_seconds` para que Flowtify pueda evaluar la severidad del desvío.


---

### Flujo 3: Procesamiento de Mensaje WhatsApp

**Endpoint**: `POST /api/v1/whatsapp/messages`  
**Servicio**: `MessageService.process_whatsapp_message()` (líneas 37-409)

```
┌────────────────┐
│ Evolution API  │ POST /whatsapp/messages (webhook)
└────────┬───────┘
         │
         v
┌──────────────────────────────────────────────────┐
│ MessageService.process_whatsapp_message()       │
├──────────────────────────────────────────────────┤
│ 1. Extraer Datos del Mensaje                     │
│    - group_id = data.key.remoteJid              │
│    - sender_phone = participantPn o participant │
│    - content = message.conversation             │
│                                                  │
│ 2. Procesar Audio (si aplica)                    │
│    ┌─────────────────────────────────────┐     │
│    │ if audioMessage:                    │     │
│    │   • download_media(audio_url)       │     │
│    │   • transcribe_audio() → Gemini AI  │     │
│    │   • text = transcription            │     │
│    └─────────────────────────────────────┘     │
│                                                  │
│ 3. Buscar Conversación y Viaje                   │
│    ┌─────────────────────────────────────┐     │
│    │ conversation = find_by_group_id()   │     │
│    │                                     │     │
│    │ if not found:                       │     │
│    │   FALLBACK RECOVERY:                │     │
│    │   • unit = find_by_whatsapp_group() │     │
│    │   • trip = find_active_by_unit()    │     │
│    │   • conversation = create_auto()    │     │
│    │     (metadata: auto_created=True)   │     │
│    └─────────────────────────────────────┘     │
│                                                  │
│ 4. Guardar Mensaje (si hay conversación)         │
│    - message_repo.create_message()              │
│    - Incluye transcripción si es audio          │
│                                                  │
│ 5. Procesar con IA                               │
│    ┌─────────────────────────────────────┐     │
│    │ • start_typing() → Evolution        │     │
│    │   (indicador "escribiendo...")      │     │
│    │                                     │     │
│    │ • classify_message() → Gemini AI    │     │
│    │   Input: texto + contexto viaje    │     │
│    │   Output: {                         │     │
│    │     intent: "loading_started",      │     │
│    │     confidence: 0.95,               │     │
│    │     response: "...",                │     │
│    │     action: "update_substatus",     │     │
│    │     new_substatus: "cargando"       │     │
│    │   }                                 │     │
│    │                                     │     │
│    │ • stop_typing() → Evolution         │     │
│    └─────────────────────────────────────┘     │
│                                                  │
│ 6. Guardar Interacción IA                        │
│    - ai_interaction_repo.create_interaction()   │
│                                                  │
│ 7. Actualizar Estado del Viaje (si aplica)      │
│    - Si action = "update_substatus":            │
│      trip_repo.update_status(new_substatus)     │
│                                                  │
│ 8. Finalizar Viaje (si unloading_complete)      │
│    - Si intent = "unloading_complete":          │
│      trip_repo.update_status("finalizado")      │
└──────────────────────────────────────────────────┘
         │
         v
   Response:
   {
     "success": true,
     "message_id": "...",
     "ai_result": { ... },
     "should_respond": true,
     "fallback_recovery": false
   }
```

**Detalles Críticos**:

1. **Fallback Recovery**: Si no encuentra conversación, busca por grupo de WhatsApp de la unidad
2. **Audio → Texto**: Usa Gemini para transcripción (soporta OGG, MP3, WAV)
3. **Indicadores de presencia**: Muestra "escribiendo..." mientras procesa IA
4. **Auto-completar viaje**: Si detecta `unloading_complete`, finaliza el viaje automáticamente
5. **Error handling**: Si falla transcripción, guarda `[Error al transcribir audio]` como contenido

---

## 🛠️ Desarrollo y Deployment

### Setup Local (Windows)

**Script**: `scripts/setup_windows.bat`

```batch
@echo off
echo Configurando entorno de desarrollo...

# 1. Crear venv
python -m venv venv
call venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Verificar setup
python scripts/verify_setup.py

echo Setup completo!
```

**Dependencias Requeridas** (requirements.txt):

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
asyncpg==0.29.0
aiomysql==0.2.0
PyMySQL==1.1.0
httpx==0.26.0
structlog==24.1.0
pydantic==2.5.3
pydantic-settings==2.1.0
google-generativeai==0.3.2
pytest==7.4.4
pytest-asyncio==0.23.3
```

### Variables de Entorno (NO existe .env en repo)

**Archivo**: `.env` (crear manualmente)

```env
# Aplicación
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# MySQL (XAMPP)
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_DATABASE=logistics_db
MYSQL_USER=root
MYSQL_PASSWORD=

# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://your-evolution-api.com
EVOLUTION_API_KEY=your_api_key
EVOLUTION_INSTANCE_NAME=SATECH

# Gemini AI
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash

# Flowtify Webhooks
FLOWTIFY_WEBHOOK_URL=https://floatify.com/webhooks
WEBHOOK_SECRET=your_webhook_secret
WEBHOOKS_ENABLED=true
WEBHOOKS_ENABLED_TENANTS=24

# Timeouts
HTTP_TIMEOUT=30
GEMINI_TIMEOUT=60
```

### Comandos Útiles

```bash
# Desarrollo
python -m app.main
# O con uvicorn:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
pytest
pytest -v --cov=app --cov-report=html

# Verificar setup
python scripts/verify_setup.py

# Limpiar BD (para tests)
python scripts/clean_database_fast.py

# Backup BD
bash scripts/backup_database.sh

# Aplicar migración
bash scripts/apply_migration.sh migrations/001_webhook_tables.sql
```

### Docker

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: logistics-microservice
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    restart: unless-stopped
    volumes:
      - ./app:/app/app
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - logistics-network

networks:
  logistics-network:
    driver: bridge
```

**Ejecutar**:

```bash
docker-compose up --build
```

---

## 🧪 Testing

### Estado Actual de Tests

**Cobertura**: ~30-40% (estimado, no hay reporte formal)

**Tests Existentes**:
- `tests/services/test_webhook_service.py` - Tests unitarios de WebhookService
- `tests/test_webhook_integration_e2e.py` - Tests E2E de webhooks
- `tests/conftest.py` - Fixtures pytest

**Tests E2E Manuales**:
- `e2e_test_log.txt` - Log de prueba E2E completa (473 líneas)
- Incluye flujo completo: creación viaje → eventos → mensajes

**Scripts de Verificación** (en raíz del proyecto):
- `check_events.py` - Verificar eventos
- `check_schema.py` - Verificar schema BD
- `check_trip_status.py` - Verificar estado de viaje
- `check_trips_schema.py` - Verificar schema de trips
- `check_unit_wialon.py` - Verificar unidad por Wialon ID
- `test_db_connection.py` - Probar conexión a BD
- `test_direct_webhook.py` - Probar webhook directo
- `test_webhook_service_injection.py` - Probar inyección de WebhookService

**Ejecutar Tests**:

```bash
# Todos los tests
pytest

# Tests con cobertura
pytest --cov=app --cov-report=html

# Tests específicos
pytest tests/services/test_webhook_service.py -v

# Tests E2E (requiere BD y servicios externos)
pytest tests/test_webhook_integration_e2e.py -v
```

**Gotchas**:
- Los tests E2E requieren MySQL corriendo
- Requieren Evolution API configurada
- Pueden crear datos reales en BD (usar `clean_database_fast.py` después)

---

## 🎯 Patrones y Convenciones

### 1. Inyección de Dependencias

**Archivo**: `app/api/dependencies.py`

```python
# Dependencias de FastAPI (singleton-like)
async def get_trip_service() -> TripService:
    evolution_client = EvolutionClient(...)
    webhook_service = WebhookService(...)  # ⚠️ Inyectado
    return TripService(db, evolution_client, webhook_service)

async def get_event_service() -> EventService:
    evolution_client = EvolutionClient(...)
    webhook_service = WebhookService(...)  # ⚠️ Inyectado
    return EventService(db, evolution_client, webhook_service)
```

**Patrón Crítico**: Los servicios reciben `webhook_service` como parámetro opcional para enviar callbacks a Flowtify.

### 2. Manejo de Errores

**Jerarquía** (de `app/core/errors.py`):

```
BaseServiceError (base)
├── DatabaseError
├── RecordNotFoundError
│   ├── TripNotFoundError
│   └── ...
├── ExternalAPIError
│   ├── EvolutionAPIError
│   ├── GeminiAPIError
│   └── FloatifyAPIError
├── ValidationError
├── ConfigurationError
└── BusinessLogicError
```

**Exception Handler Global** (`app/main.py`, líneas 95-130):

```python
@app.exception_handler(BaseServiceError)
async def service_error_handler(request, exc: BaseServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "context": exc.context,
            },
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )
```

### 3. Logging Estructurado

**Configuración** (`app/core/logging.py`):

```python
import structlog

# Logs en JSON (producción) o coloreados (desarrollo)
setup_logging(log_level="INFO", json_logs=True)

# Uso
logger = get_logger(__name__)

logger.info(
    "trip_created",
    trip_id=trip["id"],
    trip_code=trip["code"],
    unit_id=unit["id"]
)
```

**Context Logging**:

```python
from app.core.context import log_context

# Agregar trace_id al contexto
trace_id = str(uuid.uuid4())
log_context(trace_id=trace_id, trip_code=trip_code)

# Todos los logs subsecuentes incluirán trace_id
```

### 4. Respuestas API Estándar

**Modelos** (`app/models/responses.py`):

```python
class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    trace_id: Optional[str] = None
```

**Uso Consistente**: Todos los endpoints retornan este formato.

### 5. Repositorios (Patrón Manual)

**Base** (`app/repositories/base.py`):

```python
class BaseRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def find_by_id(self, id: str) -> Optional[Dict]:
        query = "SELECT * FROM table_name WHERE id = %s"
        result = await self.db.fetchrow(query, id)
        return dict(result) if result else None
```

**Convención**: Métodos comunes:
- `find_by_id(id)` - Buscar por ID
- `find_by_*()` - Buscar por otro campo
- `create()` - Insertar nuevo registro
- `update(id, data)` - Actualizar registro
- `delete(id)` - Eliminar (soft o hard)
- `upsert(data)` - Insert o update

---

## 📋 Comandos y Scripts Útiles

### Scripts en `/scripts`

| Script | Descripción | Uso |
|--------|-------------|-----|
| `setup_windows.bat` | Setup inicial en Windows | `setup_windows.bat` |
| `backup_database.sh` | Backup MySQL | `bash backup_database.sh` |
| `apply_migration.sh` | Aplicar migración SQL | `bash apply_migration.sh migrations/001_*.sql` |
| `clean_database_fast.py` | Limpiar BD (truncate) | `python clean_database_fast.py` |
| `clean_database_v2.py` | Limpiar BD (delete with FK) | `python clean_database_v2.py` |
| `clean_db_windows.py` | Limpiar BD (Windows) | `python clean_db_windows.py` |
| `verify_setup.py` | Verificar configuración | `python verify_setup.py` |

### Scripts en `/EXTRA/scripts` (55 archivos)

Scripts adicionales para setup, tracking, debugging. Ver contenido para detalles.

### Debugging

**Ver logs en tiempo real**:

```bash
tail -f server_logs.txt
tail -f e2e_test_log.txt
```

**Verificar viaje activo**:

```bash
python check_trip_status.py <trip_id>
python check_unit_wialon.py <wialon_id>
```

**Probar webhook directo**:

```bash
python test_direct_webhook.py
```

**Verificar schema**:

```bash
python check_schema.py
python check_trips_schema.py
```

---

## 🚀 Preparación para Producción

### Checklist Preproducción

#### Base de Datos

- [ ] **Migrar a MySQL en servidor dedicado** (actualmente XAMPP local)
- [ ] **Configurar pool de conexiones** (min: 10, max: 50 para producción)
- [ ] **Habilitar SSL para conexiones MySQL**
- [ ] **Configurar backups automáticos** (diarios, retención 30 días)
- [ ] **Crear índices adicionales** para queries frecuentes
- [ ] **Optimizar queries** (agregar EXPLAIN ANALYZE)

#### Seguridad

- [ ] **Generar SECRET_KEY para JWT** (si se implementa autenticación)
- [ ] **Configurar WEBHOOK_SECRET** para firmar webhooks
- [ ] **Rotar API keys** de servicios externos (Evolution, Gemini)
- [ ] **Habilitar HTTPS** (certificados SSL)
- [ ] **Configurar CORS** restrictivo (no `allow_origins=["*"]`)
- [ ] **Rate limiting** en endpoints públicos
- [ ] **Validación de IP** para webhooks de Wialon

#### Logging y Monitoreo

- [ ] **Eliminar todos los `print()` y `sys.stdout`**
- [ ] **Configurar `json_logs=True`**
- [ ] **Integrar Sentry** (ya está en requirements.txt)
- [ ] **Configurar log rotation** (logrotate)
- [ ] **Dashboards de métricas** (Grafana/Prometheus)
- [ ] **Alertas de error** (Slack/PagerDuty)

#### Performance

- [ ] **Optimizar queries N+1** en servicios
- [ ] **Implementar caching** (Redis para datos frecuentes)
- [ ] **Connection pooling** optimizado
- [ ] **Timeouts apropiados** para todas las llamadas externas
- [ ] **Load testing** (locust, k6)

#### Deployment

- [ ] **Variables de entorno en secrets manager** (no .env)
- [ ] **Docker multi-stage build** (optimizar tamaño imagen)
- [ ] **Health checks** configurados en Kubernetes/Docker
- [ ] **Graceful shutdown** implementado
- [ ] **Rolling deployment** configurado
- [ ] **Rollback automático** en caso de fallos

#### Testing

- [ ] **Cobertura de tests > 80%**
- [ ] **Tests de integración** para todos los flujos críticos
- [ ] **Tests de carga** (10K requests/min mínimo)
- [ ] **Tests de chaos engineering** (simulación de fallos)

---

## 📚 Apéndice - Recursos y Referencias

### Documentación de Integraciones

- **Evolution API**: Verificar documentación oficial para versión exacta
- **Gemini AI**: https://ai.google.dev/docs
- **Floatify**: Documentación interna del cliente
- **Wialon**: https://sdk.wialon.com/wiki/

### Archivos de Referencia

- `API_ROUTES.md` - Documentación completa de endpoints (404 líneas)
- `SCHEMA BD.sql` - Schema MySQL completo con datos de ejemplo
- `README.md` - README principal del proyecto
- `e2e_test_log.txt` - Log de prueba E2E completa (473 líneas)

### Convenciones de Código

- **Estilo**: PEP 8 (Python)
- **Type hints**: Obligatorios para funciones públicas
- **Docstrings**: Google style
- **Commits**: Conventional Commits (feat:, fix:, docs:, refactor:)

### Glosario

| Término | Definición |
|---------|------------|
| **Tenant** | Cliente/empresa en sistema multi-tenant (ej: tenant_id=24) |
| **Unit** | Unidad de transporte (camión, torton, etc.) |
| **Driver** | Conductor/operador de la unidad |
| **Trip** | Viaje asignado (origen → destino) |
| **Geofence** | Geocerca (área geográfica definida) |
| **Event** | Evento de telemetría de Wialon (posición, velocidad, etc.) |
| **Conversation** | Conversación de WhatsApp asociada a un viaje |
| **Message** | Mensaje individual dentro de una conversación |
| **AI Interaction** | Interacción con Gemini AI (clasificación/transcripción) |
| **Webhook** | Callback HTTP a Flowtify para notificar cambios |

---

## 🎓 Notas para Agentes de IA

### Al Implementar Nuevas Features

1. **SIEMPRE verificar que la BD es MySQL**, no PostgreSQL
2. **Usar el patrón de grupos compartidos** (vinculados a unidades)
3. **Incluir idempotencia** en operaciones críticas (usar UNIQUE constraints)
4. **Manejar errores de APIs externas** (Evolution, Gemini pueden fallar)
5. **Usar structlog** para logging (no print())
6. **Seguir el patrón de inyección de dependencias** existente
7. **Probar con `clean_database_fast.py`** entre tests

### Al Refactorizar

1. **NO romper la compatibilidad** con webhooks de Floatify/Wialon
2. **Mantener la estructura de tablas** MySQL existente
3. **NO cambiar formato de respuestas API** sin coordinar
4. **Preservar trace_id** en logging para trazabilidad
5. **Considerar migration path** para datos existentes

### Al Corregir Bugs

1. **Revisar logs** en `server_logs.txt` y `e2e_test_log.txt`
2. **Verificar estado de BD** con scripts `check_*.py`
3. **Probar idempotencia** (ejecutar la misma operación 2 veces)
4. **Validar con payload real** de Floatify/Wialon (ver API_ROUTES.md)
5. **NO asumir que un grupo de WhatsApp es del viaje** (puede ser de la unidad)

---

**Fin del Documento Brownfield**

Este documento refleja el ESTADO REAL del sistema al 11 de noviembre de 2025. Actualizar este documento al implementar cambios significativos.

