"""
Configuración de pytest y fixtures globales
"""
import pytest
from typing import AsyncGenerator
from unittest.mock import AsyncMock

from app.core.database import Database


@pytest.fixture
def mock_database():
    """
    Mock de base de datos para tests unitarios
    
    Returns:
        Mock de Database con métodos async
    """
    db = AsyncMock(spec=Database)
    db.fetchrow = AsyncMock()
    db.fetch = AsyncMock()
    db.execute = AsyncMock()
    db.fetchval = AsyncMock()
    return db


@pytest.fixture
async def test_database():
    """
    Base de datos real para tests de integración
    
    Nota: Requiere configuración de base de datos de test
    """
    # TODO: Implementar conexión a BD de test
    pytest.skip("Requiere base de datos de test configurada")


# Configuración de markers
def pytest_configure(config):
    """Registrar markers personalizados"""
    config.addinivalue_line(
        "markers", "integration: Tests de integración que requieren BD real"
    )
    config.addinivalue_line(
        "markers", "slow: Tests lentos que pueden omitirse en CI rápido"
    )

