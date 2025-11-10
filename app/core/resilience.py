"""
Sistema de resiliencia para APIs externas
Implementa Circuit Breaker y reintentos exponenciales con backoff
"""
import asyncio
import time
from typing import Any, Callable, Optional, Dict
from enum import Enum
from functools import wraps
from app.core.logging import get_logger
from app.core.errors import ExternalAPIError

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Estados del Circuit Breaker"""
    CLOSED = "closed"  # Circuito cerrado - funcionando normalmente
    OPEN = "open"      # Circuito abierto - bloqueando llamadas
    HALF_OPEN = "half_open"  # Semi-abierto - probando recuperación


class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker
    
    El circuit breaker previene llamadas repetidas a servicios que están fallando,
    dándoles tiempo para recuperarse.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Inicializar Circuit Breaker
        
        Args:
            name: Nombre del circuit breaker (para logging)
            failure_threshold: Número de fallos consecutivos para abrir el circuito
            timeout: Tiempo en segundos antes de intentar cerrar el circuito
            success_threshold: Número de éxitos para cerrar el circuito desde half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función con circuit breaker (versión sync)
        
        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
            
        Returns:
            Resultado de la función
            
        Raises:
            ExternalAPIError: Si el circuito está abierto o la función falla
        """
        # Verificar estado del circuito
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "circuit_breaker_half_open",
                    circuit=self.name,
                    failure_count=self.failure_count
                )
                self.state = CircuitState.HALF_OPEN
            else:
                logger.warning(
                    "circuit_breaker_open",
                    circuit=self.name,
                    failure_count=self.failure_count,
                    seconds_until_retry=self._seconds_until_retry()
                )
                raise ExternalAPIError(
                    f"Circuit breaker '{self.name}' is open",
                    context={"state": self.state, "failure_count": self.failure_count}
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            logger.error(
                "circuit_breaker_call_failed",
                circuit=self.name,
                error=str(e),
                state=self.state,
                failure_count=self.failure_count
            )
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función asíncrona con circuit breaker
        
        Args:
            func: Función asíncrona a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
            
        Returns:
            Resultado de la función
            
        Raises:
            ExternalAPIError: Si el circuito está abierto o la función falla
        """
        # Verificar estado del circuito
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "circuit_breaker_half_open",
                    circuit=self.name,
                    failure_count=self.failure_count
                )
                self.state = CircuitState.HALF_OPEN
            else:
                logger.warning(
                    "circuit_breaker_open",
                    circuit=self.name,
                    failure_count=self.failure_count,
                    seconds_until_retry=self._seconds_until_retry()
                )
                raise ExternalAPIError(
                    f"Circuit breaker '{self.name}' is open",
                    context={"state": self.state, "failure_count": self.failure_count}
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            logger.error(
                "circuit_breaker_call_failed",
                circuit=self.name,
                error=str(e),
                state=self.state,
                failure_count=self.failure_count
            )
            raise
    
    def _on_success(self):
        """Manejar éxito de llamada"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(
                    "circuit_breaker_closed",
                    circuit=self.name,
                    success_count=self.success_count
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            # Reset failure count on success in CLOSED state
            self.failure_count = 0
    
    def _on_failure(self):
        """Manejar fallo de llamada"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # En half-open, un fallo vuelve a abrir el circuito
            logger.warning(
                "circuit_breaker_reopened",
                circuit=self.name,
                failure_count=self.failure_count
            )
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.failure_count >= self.failure_threshold:
            # Abrir circuito si se alcanza el umbral
            logger.error(
                "circuit_breaker_opened",
                circuit=self.name,
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )
            self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Verificar si es tiempo de intentar resetear el circuito"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.timeout
    
    def _seconds_until_retry(self) -> float:
        """Calcular segundos hasta el próximo intento"""
        if self.last_failure_time is None:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.timeout - elapsed)
    
    def get_state(self) -> Dict[str, Any]:
        """Obtener estado actual del circuit breaker"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "seconds_until_retry": self._seconds_until_retry() if self.state == CircuitState.OPEN else None
        }


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    **kwargs
) -> Any:
    """
    Ejecutar función con reintentos exponenciales y backoff
    
    Args:
        func: Función a ejecutar (puede ser sync o async)
        *args: Argumentos posicionales
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        max_delay: Delay máximo en segundos
        exponential_base: Base para el cálculo exponencial
        exceptions: Tupla de excepciones que deberían causar reintento
        **kwargs: Argumentos nombrados
        
    Returns:
        Resultado de la función
        
    Raises:
        Exception: La última excepción si todos los reintentos fallan
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(
                    "retry_succeeded",
                    function=func.__name__,
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
            
            return result
            
        except exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                # Calcular delay con backoff exponencial
                delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                
                logger.warning(
                    "retry_attempt",
                    function=func.__name__,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    next_retry_in_seconds=delay
                )
                
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "retry_exhausted",
                    function=func.__name__,
                    attempts=attempt + 1,
                    error=str(e)
                )
    
    # Si llegamos aquí, todos los reintentos fallaron
    raise last_exception


# Instancias globales de circuit breakers para cada servicio externo
circuit_breakers = {
    "evolution": CircuitBreaker(
        name="evolution_api",
        failure_threshold=5,
        timeout=60.0,
        success_threshold=2
    ),
    "gemini": CircuitBreaker(
        name="gemini_api",
        failure_threshold=3,
        timeout=30.0,
        success_threshold=2
    ),
    "floatify": CircuitBreaker(
        name="floatify_api",
        failure_threshold=5,
        timeout=60.0,
        success_threshold=2
    ),
    "wialon": CircuitBreaker(
        name="wialon_api",
        failure_threshold=5,
        timeout=60.0,
        success_threshold=2
    ),
}


def get_circuit_breaker(service: str) -> Optional[CircuitBreaker]:
    """
    Obtener circuit breaker para un servicio
    
    Args:
        service: Nombre del servicio ("evolution", "gemini", "floatify", "wialon")
        
    Returns:
        Circuit breaker o None si no existe
    """
    return circuit_breakers.get(service)


def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """
    Obtener estado de todos los circuit breakers
    
    Returns:
        Diccionario con estado de cada circuit breaker
    """
    return {
        service: breaker.get_state()
        for service, breaker in circuit_breakers.items()
    }

