"""
Endpoints admin para gestión de webhooks

Estos endpoints permiten:
- Ver logs de delivery de webhooks
- Ver dead letter queue
- Reintentar webhooks fallidos
- Obtener métricas de webhooks
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from app.core.database import Database
from app.api.dependencies import get_database, get_webhook_service
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookRetryRequest(BaseModel):
    """Request para reintentar webhook"""
    delivery_log_id: str


class WebhookStatsResponse(BaseModel):
    """Respuesta con estadísticas de webhooks"""
    total_sent: int
    total_failed: int
    success_rate: float
    pending_retries: int
    dlq_size: int


@router.get("/delivery-log")
async def get_webhook_delivery_log(
    trip_id: Optional[str] = None,
    status: Optional[str] = None,
    webhook_type: Optional[str] = None,
    limit: int = Query(100, le=1000, ge=1),
    offset: int = Query(0, ge=0),
    database: Database = Depends(get_database),
):
    """
    Obtener logs de delivery de webhooks
    
    Query Parameters:
    - trip_id: Filtrar por trip ID
    - status: Filtrar por status (pending, sent, failed, retrying)
    - webhook_type: Filtrar por tipo de webhook
    - limit: Número de resultados (máx 1000)
    - offset: Offset para paginación
    
    Returns:
        Lista de logs de delivery
    """
    conditions = []
    params = []
    
    if trip_id:
        conditions.append("trip_id = %s")
        params.append(trip_id)
    
    if status:
        conditions.append("status = %s")
        params.append(status)
    
    if webhook_type:
        conditions.append("webhook_type = %s")
        params.append(webhook_type)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    query = f"""
        SELECT *
        FROM webhook_delivery_log
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    logs = await database.fetch(query, *params)
    
    # Contar total
    count_query = f"""
        SELECT COUNT(*) as total
        FROM webhook_delivery_log
        {where_clause}
    """
    count_params = params[:-2]  # Sin limit/offset
    
    total_result = await database.fetchrow(count_query, *count_params)
    total = total_result["total"] if total_result else 0
    
    return {
        "success": True,
        "count": len(logs),
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": logs,
    }


@router.get("/dead-letter-queue")
async def get_dead_letter_queue(
    resolved: bool = False,
    limit: int = Query(100, le=1000, ge=1),
    offset: int = Query(0, ge=0),
    database: Database = Depends(get_database),
):
    """
    Obtener webhooks en dead letter queue
    
    Query Parameters:
    - resolved: Si es True, muestra solo resueltos; False muestra pendientes
    - limit: Número de resultados
    - offset: Offset para paginación
    
    Returns:
        Lista de webhooks en DLQ
    """
    query = """
        SELECT *
        FROM webhook_dead_letter_queue
        WHERE resolved = %s
        ORDER BY moved_to_dlq_at DESC
        LIMIT %s OFFSET %s
    """
    
    dlq_items = await database.fetch(query, resolved, limit, offset)
    
    # Contar total
    count_query = "SELECT COUNT(*) as total FROM webhook_dead_letter_queue WHERE resolved = %s"
    total_result = await database.fetchrow(count_query, resolved)
    total = total_result["total"] if total_result else 0
    
    return {
        "success": True,
        "count": len(dlq_items),
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": dlq_items,
    }


@router.post("/retry/{delivery_log_id}")
async def retry_webhook(
    delivery_log_id: str,
    database: Database = Depends(get_database),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Reintentar manualmente un webhook fallido
    
    Path Parameters:
    - delivery_log_id: ID del log de delivery a reintentar
    
    Returns:
        Resultado del reintento
    """
    if not webhook_service:
        raise HTTPException(
            status_code=503,
            detail="Webhook service not available (webhooks may be disabled)",
        )
    
    # Obtener webhook del log
    webhook = await database.fetchrow(
        "SELECT * FROM webhook_delivery_log WHERE id = %s",
        delivery_log_id,
    )
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook delivery log not found")
    
    # TODO: Implementar lógica de reenvío
    # Por ahora solo marcamos como pending para que el retry automático lo tome
    
    await database.execute(
        """
        UPDATE webhook_delivery_log
        SET status = %s, retry_count = 0
        WHERE id = %s
        """,
        "pending",
        delivery_log_id,
    )
    
    return {
        "success": True,
        "message": "Webhook marked for retry",
        "delivery_log_id": delivery_log_id,
    }


@router.get("/stats")
async def get_webhook_stats(
    hours: int = Query(24, ge=1, le=168),  # Últimas 24 horas por defecto
    database: Database = Depends(get_database),
) -> WebhookStatsResponse:
    """
    Obtener estadísticas de webhooks
    
    Query Parameters:
    - hours: Número de horas hacia atrás para calcular stats (1-168)
    
    Returns:
        Estadísticas de webhooks
    """
    # Total enviados
    sent_query = """
        SELECT COUNT(*) as count
        FROM webhook_delivery_log
        WHERE status = 'sent'
          AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
    """
    sent_result = await database.fetchrow(sent_query, hours)
    total_sent = sent_result["count"] if sent_result else 0
    
    # Total fallidos
    failed_query = """
        SELECT COUNT(*) as count
        FROM webhook_delivery_log
        WHERE status = 'failed'
          AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
    """
    failed_result = await database.fetchrow(failed_query, hours)
    total_failed = failed_result["count"] if failed_result else 0
    
    # Calcular success rate
    total = total_sent + total_failed
    success_rate = (total_sent / total * 100) if total > 0 else 100.0
    
    # Pending retries
    pending_query = """
        SELECT COUNT(*) as count
        FROM webhook_delivery_log
        WHERE status IN ('pending', 'retrying')
    """
    pending_result = await database.fetchrow(pending_query)
    pending_retries = pending_result["count"] if pending_result else 0
    
    # DLQ size
    dlq_query = """
        SELECT COUNT(*) as count
        FROM webhook_dead_letter_queue
        WHERE resolved = false
    """
    dlq_result = await database.fetchrow(dlq_query)
    dlq_size = dlq_result["count"] if dlq_result else 0
    
    return WebhookStatsResponse(
        total_sent=total_sent,
        total_failed=total_failed,
        success_rate=round(success_rate, 2),
        pending_retries=pending_retries,
        dlq_size=dlq_size,
    )


@router.get("/health")
async def webhook_health_check(
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Health check del servicio de webhooks
    
    Returns:
        Estado del servicio
    """
    if not webhook_service:
        return {
            "status": "disabled",
            "message": "Webhooks are disabled",
            "webhook_service_is_none": True,
        }
    
    # Verificar configuración
    has_url = bool(webhook_service.target_url)
    has_secret = bool(webhook_service.secret_key)
    
    if has_url and has_secret:
        status = "healthy"
    elif has_url:
        status = "degraded"
        message = "Missing webhook secret"
    else:
        status = "unhealthy"
        message = "Missing target URL"
    
    return {
        "status": status,
        "has_target_url": has_url,
        "has_secret": has_secret,
        "circuit_breaker_state": webhook_service._circuit_breaker.state,
        "webhook_service_is_none": False,
    }


@router.get("/debug/injection")
async def debug_injection(
    database: Database = Depends(get_database),
    webhook_service: Optional[WebhookService] = Depends(get_webhook_service),
):
    """
    Endpoint de debugging para verificar inyección de dependencias
    """
    from app.config import settings
    
    return {
        "webhook_service_injected": webhook_service is not None,
        "webhook_service_type": str(type(webhook_service)),
        "settings_webhooks_enabled": settings.webhooks_enabled,
        "settings_webhook_url": settings.flowtify_webhook_url,
        "settings_has_secret": bool(settings.webhook_secret),
        "settings_enabled_tenants": settings.webhooks_enabled_tenants,
        "database_connected": database is not None,
    }


@router.post("/debug/test-send/{trip_id}")
async def test_send_webhook(
    trip_id: str,
    webhook_service: Optional[WebhookService] = Depends(get_webhook_service),
):
    """
    Endpoint de testing para enviar webhook manualmente
    """
    if not webhook_service:
        return {
            "success": False,
            "error": "WebhookService is None - not injected",
        }
    
    try:
        result = await webhook_service.send_status_update(
            trip_id=trip_id,
            old_status="test_old",
            old_substatus="test_old_sub",
            new_status="test_new",
            new_substatus="test_new_sub",
            change_reason="manual_test",
        )
        
        return {
            "success": True,
            "webhook_result": result,
            "webhook_service_injected": True,
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

