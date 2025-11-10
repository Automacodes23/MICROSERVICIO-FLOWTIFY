"""
Tests unitarios para WebhookService

Ejecutar: pytest tests/services/test_webhook_service.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime

from app.services.webhook_service import WebhookService, CircuitBreaker
from app.core.database import Database


@pytest.fixture
def mock_db():
    """Mock de base de datos"""
    db = AsyncMock(spec=Database)
    db.fetchrow = AsyncMock()
    db.fetch = AsyncMock()
    db.execute = AsyncMock()
    db.fetchval = AsyncMock()
    return db


@pytest.fixture
def webhook_service(mock_db):
    """Fixture de WebhookService"""
    service = WebhookService(
        db=mock_db,
        target_url="https://test.flowtify.com/webhooks",
        secret_key="test_secret_key_123456789",
        timeout=30,
    )
    return service


@pytest.mark.asyncio
class TestWebhookService:
    """Tests para WebhookService"""
    
    async def test_generate_signature(self, webhook_service):
        """Test de generación de firma HMAC"""
        payload = '{"event": "test", "data": "value"}'
        signature = webhook_service._generate_signature(payload)
        
        # Verificar que la firma no esté vacía
        assert signature
        assert len(signature) == 64  # SHA256 hex = 64 caracteres
        assert isinstance(signature, str)
    
    async def test_generate_signature_same_payload_same_signature(self, webhook_service):
        """Test de consistencia de firma"""
        payload = '{"event": "test"}'
        
        sig1 = webhook_service._generate_signature(payload)
        sig2 = webhook_service._generate_signature(payload)
        
        assert sig1 == sig2
    
    async def test_is_enabled_for_tenant(self, webhook_service):
        """Test de verificación de tenant habilitado"""
        # Mock de settings
        with patch("app.services.webhook_service.settings") as mock_settings:
            mock_settings.is_webhook_enabled_for_tenant.return_value = True
            
            assert webhook_service._is_enabled_for_tenant(24) is True
    
    async def test_format_driver_data(self, webhook_service):
        """Test de formateo de datos de conductor"""
        driver = {
            "id": "driver-123",
            "name": "Test Driver",
            "phone": "+1234567890",
            "wialon_driver_code": "DRV001",
            "extra_field": "ignored",
        }
        
        formatted = webhook_service._format_driver_data(driver)
        
        assert formatted["id"] == "driver-123"
        assert formatted["name"] == "Test Driver"
        assert formatted["phone"] == "+1234567890"
        assert formatted["wialon_driver_code"] == "DRV001"
        assert "extra_field" not in formatted
    
    async def test_format_driver_data_none(self, webhook_service):
        """Test de formateo con driver None"""
        formatted = webhook_service._format_driver_data(None)
        assert formatted == {}
    
    async def test_format_unit_data(self, webhook_service):
        """Test de formateo de datos de unidad"""
        unit = {
            "id": "unit-456",
            "code": "TRUCK-001",
            "plate": "ABC123",
            "wialon_id": "27538728",
            "imei": "863719067169228",
            "name": "Torton 309",
        }
        
        formatted = webhook_service._format_unit_data(unit)
        
        assert formatted["id"] == "unit-456"
        assert formatted["code"] == "TRUCK-001"
        assert formatted["plate"] == "ABC123"
        assert formatted["wialon_id"] == "27538728"
    
    async def test_log_webhook_attempt(self, webhook_service, mock_db):
        """Test de logging de intento de webhook"""
        mock_db.execute.return_value = 1
        
        delivery_log_id = await webhook_service._log_webhook_attempt(
            webhook_type="status_update",
            trip_id="trip-123",
            payload={"event": "test"},
            target_url="https://test.com/webhook",
        )
        
        assert delivery_log_id
        assert mock_db.execute.called
        
        # Verificar que se insertó con status pending
        call_args = mock_db.execute.call_args
        assert "pending" in call_args[0]
    
    @patch("app.services.webhook_service.httpx.AsyncClient")
    async def test_send_status_update_success(self, mock_httpx, webhook_service, mock_db):
        """Test de envío exitoso de status update webhook"""
        # Mock trip data
        mock_db.fetchrow.return_value = {
            "id": "trip-123",
            "floatify_trip_id": "TRIP-001",
            "tenant_id": 24,
            "status": "en_ruta",
            "substatus": "rumbo_carga",
            "created_at": datetime.utcnow(),
            "actual_start": None,
            "driver_id": "driver-123",
            "driver_name": "Test Driver",
            "driver_phone": "+1234567890",
            "wialon_driver_code": "DRV001",
            "unit_id": "unit-456",
            "unit_code": "TRUCK-001",
            "unit_plate": "ABC123",
            "unit_wialon_id": "27538728",
            "unit_imei": "863719067169228",
            "unit_name": "Torton 309",
        }
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        webhook_service.client = AsyncMock()
        webhook_service.client.post = AsyncMock(return_value=mock_response)
        
        # Ejecutar
        result = await webhook_service.send_status_update(
            trip_id="trip-123",
            old_status="planned",
            old_substatus="por_iniciar",
            new_status="en_ruta",
            new_substatus="rumbo_carga",
            change_reason="driver_started",
        )
        
        # Verificar
        assert result["success"] is True
        assert result["status_code"] == 200
        assert webhook_service.client.post.called
        
        # Verificar estructura de payload
        call_args = webhook_service.client.post.call_args
        payload_json = call_args.kwargs["content"]
        payload = json.loads(payload_json)
        
        assert payload["event"] == "status_update"
        assert payload["trip"]["status"] == "en_ruta"
        assert payload["trip"]["substatus"] == "rumbo_carga"
        assert payload["trip"]["previous_status"] == "planned"


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Tests para Circuit Breaker"""
    
    async def test_circuit_breaker_closed_state(self):
        """Test de estado cerrado del circuit breaker"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        assert cb.state == "closed"
        assert cb.failure_count == 0
    
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test de apertura después de threshold"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Simular 3 fallos
        async def failing_func():
            raise Exception("Test error")
        
        for i in range(3):
            try:
                await cb.call(failing_func)
            except Exception:
                pass
        
        # Verificar que se abrió
        assert cb.state == "open"
        assert cb.failure_count == 3
    
    async def test_circuit_breaker_resets_on_success(self):
        """Test de reset en éxito"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Simular 2 fallos
        async def failing_func():
            raise Exception("Test error")
        
        for i in range(2):
            try:
                await cb.call(failing_func)
            except Exception:
                pass
        
        assert cb.failure_count == 2
        
        # Simular éxito
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        
        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == "closed"
    
    async def test_circuit_breaker_blocks_when_open(self):
        """Test de bloqueo cuando circuit breaker está abierto"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Abrir circuit breaker
        async def failing_func():
            raise Exception("Test error")
        
        for i in range(2):
            try:
                await cb.call(failing_func)
            except Exception:
                pass
        
        assert cb.state == "open"
        
        # Intentar llamar función - debe lanzar error de circuit breaker
        from app.core.errors import BusinessLogicError
        
        async def any_func():
            return "test"
        
        with pytest.raises(BusinessLogicError, match="Circuit breaker is OPEN"):
            await cb.call(any_func)


# ============================================================================
# Integration Tests (requieren base de datos de test)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestWebhookServiceIntegration:
    """Tests de integración con base de datos real"""
    
    # Estos tests requieren una base de datos de test configurada
    # Ejecutar con: pytest tests/services/test_webhook_service.py -v -m integration
    
    async def test_log_webhook_attempt_database(self, webhook_service, mock_db):
        """Test de logging a base de datos"""
        # Este test requiere BD real, por ahora skip
        pytest.skip("Requiere base de datos de test configurada")
    
    async def test_move_to_dead_letter_queue(self, webhook_service, mock_db):
        """Test de movimiento a DLQ"""
        pytest.skip("Requiere base de datos de test configurada")


# ============================================================================
# Fixtures adicionales
# ============================================================================

@pytest.fixture
def sample_trip_data():
    """Datos de ejemplo de un viaje"""
    return {
        "id": "trip-123",
        "floatify_trip_id": "TRIP-001",
        "tenant_id": 24,
        "status": "en_ruta",
        "substatus": "rumbo_carga",
        "origin": "León",
        "destination": "Jalisco",
        "created_at": datetime.utcnow(),
        "actual_start": None,
        "driver": {
            "id": "driver-123",
            "name": "Test Driver",
            "phone": "+1234567890",
            "wialon_driver_code": "DRV001",
        },
        "unit": {
            "id": "unit-456",
            "code": "TRUCK-001",
            "plate": "ABC123",
            "wialon_id": "27538728",
            "imei": "863719067169228",
            "name": "Torton 309",
        },
    }


@pytest.fixture
def sample_violation_data():
    """Datos de ejemplo de violación de velocidad"""
    return {
        "speed": 105.8,
        "max_speed": 80.0,
        "duration_seconds": 45,
        "distance_km": 1.2,
        "notification_id": "NOTIF_123",
        "external_id": "wialon_speed_123",
        "location": {
            "latitude": 21.1502,
            "longitude": -101.8503,
            "address": "Test Address",
        },
    }

