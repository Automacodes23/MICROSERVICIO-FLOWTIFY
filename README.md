# 🚛 Microservicio de Gestión Logística

Microservicio modular en Python (FastAPI) para gestión de 2,500 unidades de transporte logístico, integrando Floatify, Wialon, WhatsApp (Evolution API) y Gemini AI.

## 📋 Características

- **Arquitectura Modular**: Separación clara de responsabilidades (API, Services, Repositories, Integrations)
- **Gestión de Viajes**: Creación, actualización y seguimiento de viajes
- **Eventos en Tiempo Real**: Procesamiento de eventos de Wialon (geocercas, velocidad, pánico)
- **Bot de WhatsApp**: Comunicación inteligente con conductores via Evolution API
- **IA Integrada**: Gemini AI para clasificación de mensajes y respuestas contextuales
- **Base de Datos**: Supabase (PostgreSQL) con pools de conexión async
- **Logging Estructurado**: structlog para trazabilidad completa
- **Contenedorización**: Docker y docker-compose

## 🏗️ Arquitectura

```
┌─────────────┐          ┌──────────────────────┐
│  Floatify   │─────────▶│   Microservicio      │
└─────────────┘          │   Python (FastAPI)   │
                         │                       │
┌─────────────┐          │  - Gestión de viajes │
│   Wialon    │─────────▶│  - Procesamiento IA  │
│Notificaciones│          │  - Orquestación      │
└─────────────┘          │  - Logs centralizados│
                         └───────┬──────┬───────┘
                                 │      │
              ┌──────────────────┘      └─────────────┐
              ▼                                        ▼
     ┌────────────────┐                      ┌──────────────┐
     │  Evolution API │                      │   Supabase   │
     │  (WhatsApp)    │                      │ (PostgreSQL) │
     └────────┬───────┘                      └──────────────┘
              │
              ▼
     ┌────────────────┐
     │   Gemini AI    │
     │  (NLU/STT)     │
     └────────────────┘
```

## 🚀 Quick Start

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose (opcional)
- Cuenta de Supabase (proyecto TESTING-FLOWTIFY)
- Evolution API configurada
- API Key de Google Gemini

### Instalación Local

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd SHOW-SERVICE
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp env.example .env
# Editar .env con tus credenciales
```

5. **Inicializar base de datos**
- Abrir Supabase SQL Editor
- Ejecutar `scripts/init_supabase.sql`

6. **Ejecutar aplicación**
```bash
python -m app.main
# O con uvicorn:
uvicorn app.main:app --reload
```

La aplicación estará disponible en: `http://localhost:8000`

### Instalación con Docker

1. **Configurar .env**
```bash
cp env.example .env
# Editar .env con tus credenciales
```

2. **Construir y ejecutar**
```bash
docker-compose up --build
```

## 📡 Endpoints Principales

### Health Check
```http
GET /api/v1/health
```

### Viajes
```http
POST /api/v1/trips/create           # Crear viaje desde Floatify
GET  /api/v1/trips/{trip_id}        # Obtener viaje
POST /api/v1/trips/{trip_id}/complete  # Completar viaje
PUT  /api/v1/trips/{trip_id}/status    # Actualizar estado
```

### Eventos Wialon
```http
POST /api/v1/wialon/events          # Webhook para eventos de Wialon
```

### Mensajes WhatsApp
```http
POST /api/v1/whatsapp/messages      # Webhook de Evolution API
```

## 📦 Estructura del Proyecto

```
show-service/
├── app/
│   ├── api/                       # Capa de presentación
│   │   ├── routes/               # Endpoints
│   │   ├── dependencies.py       # Dependencias de FastAPI
│   │   └── middleware.py         # Middleware personalizado
│   ├── services/                  # Lógica de negocio
│   ├── repositories/              # Acceso a datos
│   ├── integrations/              # Clientes API externos
│   │   ├── evolution/            # WhatsApp
│   │   ├── gemini/               # Gemini AI
│   │   ├── floatify/             # Callbacks
│   │   └── wialon/               # Parsers
│   ├── models/                    # Modelos Pydantic
│   ├── core/                      # Núcleo del sistema
│   │   ├── database.py           # Pool de conexiones
│   │   ├── logging.py            # Logger estructurado
│   │   ├── errors.py             # Excepciones
│   │   └── constants.py          # Constantes
│   ├── config.py                  # Configuración
│   └── main.py                    # Entry point
├── scripts/                       # Scripts de utilidad
├── tests/                         # Tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔧 Configuración

### Variables de Entorno

Todas las variables se configuran en `.env`:

**Base de Datos**
- `SUPABASE_DB_HOST`: Host de Supabase
- `SUPABASE_DB_PASSWORD`: Password de PostgreSQL

**Evolution API**
- `EVOLUTION_API_URL`: URL de tu instancia
- `EVOLUTION_API_KEY`: API key
- `EVOLUTION_INSTANCE_NAME`: Nombre de la instancia

**Gemini AI**
- `GEMINI_API_KEY`: API key de Google
- `GEMINI_MODEL`: Modelo a usar (default: gemini-1.5-flash)

Ver `env.example` para lista completa.

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Tests unitarios solamente
pytest tests/unit/

# Tests de integración
pytest tests/integration/ -m integration

# Con coverage
pytest --cov=app --cov-report=html
```

## 📝 Flujos Principales

### 1. Creación de Viaje

1. Floatify envía POST a `/api/v1/trips/create`
2. Se crea/actualiza unidad, conductor y viaje
3. Se crean geocercas y asociaciones
4. Se crea grupo de WhatsApp
5. Se envía mensaje de bienvenida

### 2. Evento de Wialon

1. Wialon envía notificación a `/api/v1/wialon/events`
2. Se identifica el viaje activo
3. Se registra el evento
4. Se determina acción (actualizar estado, enviar alerta)
5. Se envía notificación si es necesario

### 3. Mensaje de WhatsApp

1. Evolution API envía webhook a `/api/v1/whatsapp/messages`
2. Se identifica la conversación y viaje
3. Gemini AI clasifica el mensaje
4. Se actualiza el subestado del viaje
5. Se genera y envía respuesta contextual

## 🔐 Seguridad

- Validación de payloads con Pydantic
- Sanitización de inputs
- Rate limiting (recomendado en producción)
- CORS configurables
- Webhook secrets para verificar origen

## 📊 Logging y Monitoreo

- Logs estructurados en JSON (producción)
- Trace ID para trazabilidad end-to-end
- Context logging con structlog
- Health check endpoint
- Métricas en headers de respuesta

## 🚢 Deployment

### Producción

1. **Variables de entorno**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

2. **Docker**
```bash
docker build -t logistics-microservice .
docker run -p 8000:8000 --env-file .env logistics-microservice
```

3. **Railway / Render**
- Conectar repositorio
- Configurar variables de entorno
- Deploy automático desde main branch

## 🤝 Contribución

1. Fork el proyecto
2. Crea tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

## 📞 Soporte

Para dudas o problemas, contactar al equipo de desarrollo.

---

**Nota**: Este es un microservicio modular diseñado para ser mantenible y escalable. Sigue las mejores prácticas de desarrollo y arquitectura de software.

