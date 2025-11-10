"""
Router para health checks
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio
from typing import Dict, Any
from app.config import settings
from app.core.database import db
from app.core.resilience import get_all_circuit_states
from app.core.logging import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """
    Health check básico - retorna 200 si el servicio está vivo
    
    Este endpoint es para load balancers y orquestadores
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Health check detallado
    
    Verifica:
    - Servicio principal
    - Base de datos MySQL
    - Estado de circuit breakers
    - Configuración
    """
    health_status = {
        "service": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        },
        "dependencies": {},
        "circuit_breakers": {},
        "overall_status": "healthy"
    }
    
    # 1. Verificar base de datos
    db_health = await _check_database()
    health_status["dependencies"]["database"] = db_health
    
    # 2. Estado de circuit breakers
    circuit_states = get_all_circuit_states()
    health_status["circuit_breakers"] = circuit_states
    
    # 3. Determinar estado general
    issues = []
    
    if db_health["status"] != "healthy":
        issues.append("database_unhealthy")
        
    # Verificar circuit breakers abiertos
    open_circuits = [
        name for name, state in circuit_states.items()
        if state["state"] == "open"
    ]
    if open_circuits:
        issues.append(f"circuit_breakers_open: {', '.join(open_circuits)}")
        health_status["circuit_breakers"]["open_circuits"] = open_circuits
    
    # Determinar status code basado en salud
    if issues:
        health_status["overall_status"] = "degraded"
        health_status["issues"] = issues
        status_code = 503  # Service Unavailable
    else:
        status_code = 200
    
    return JSONResponse(content=health_status, status_code=status_code)


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check para Kubernetes
    
    Verifica si el servicio está listo para recibir tráfico:
    - Base de datos accesible
    - Circuit breakers no completamente abiertos
    """
    ready = True
    checks = {}
    
    # Verificar base de datos
    db_health = await _check_database()
    checks["database"] = db_health["status"] == "healthy"
    ready = ready and checks["database"]
    
    # Verificar circuit breakers críticos
    circuit_states = get_all_circuit_states()
    critical_circuits = ["evolution", "gemini"]
    
    for circuit in critical_circuits:
        if circuit in circuit_states:
            is_open = circuit_states[circuit]["state"] == "open"
            checks[f"circuit_{circuit}"] = not is_open
            ready = ready and not is_open
    
    status_code = 200 if ready else 503
    
    return JSONResponse(
        content={
            "ready": ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status_code
    )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check para Kubernetes
    
    Verifica si el servicio está vivo (no deadlocked)
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


async def _check_database() -> Dict[str, Any]:
    """
    Verificar salud de la base de datos
    
    Returns:
        Dict con status y detalles
    """
    try:
        start_time = datetime.utcnow()
        
        # Intentar query simple
        result = await db.fetchval("SELECT 1")
        
        # Calcular latencia
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "status": "healthy",
            "type": "mysql",
            "latency_ms": round(latency_ms, 2),
            "responsive": True
        }
        
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "type": "mysql",
            "error": str(e),
            "responsive": False
        }

