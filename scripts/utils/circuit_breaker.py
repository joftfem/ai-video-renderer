#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation

Provides resilient external API calls with circuit breaker pattern,
exponential backoff, jitter, and comprehensive monitoring.
"""

import asyncio
import time
import random
from typing import Callable, Any, Optional, Dict, List, Union
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import structlog

from .exceptions import (
    NetworkError, APILimitError, ExternalServiceError,
    ErrorSeverity, BaseRendererException
)

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open" # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 30.0               # Request timeout
    
    # Exponential backoff settings
    initial_delay: float = 1.0          # Initial retry delay
    max_delay: float = 300.0            # Maximum retry delay
    backoff_multiplier: float = 2.0     # Backoff multiplier
    jitter: bool = True                 # Add random jitter
    max_retries: int = 3                # Maximum retry attempts
    
    # Monitoring
    enable_metrics: bool = True         # Enable metrics collection
    

@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_open_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    average_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 1.0 - self.success_rate()
    
    def update_response_time(self, response_time: float):
        """Update response time metrics."""
        self.response_times.append(response_time)
        # Keep only last 100 response times
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        
        if self.response_times:
            self.average_response_time = sum(self.response_times) / len(self.response_times)


class CircuitBreakerOpenException(BaseRendererException):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, service_name: str, retry_after: float):
        super().__init__(
            message=f"Circuit breaker is open for {service_name}",
            error_code="CIRCUIT_BREAKER_OPEN",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context={"service_name": service_name},
            retry_after=int(retry_after)
        )


class CircuitBreaker:
    """Circuit breaker implementation for resilient API calls."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        
        logger.info(
            "Circuit breaker initialized",
            name=name,
            config=self.config.__dict__
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if circuit should transition states
            await self._check_state_transition()
            
            # Fail fast if circuit is open
            if self.state == CircuitState.OPEN:
                retry_after = self._get_retry_after()
                raise CircuitBreakerOpenException(self.name, retry_after)
            
            # Execute the function with retries
            return await self._execute_with_retries(func, *args, **kwargs)
    
    async def _execute_with_retries(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retries."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.config.timeout
                    )
                else:
                    result = func(*args, **kwargs)
                
                # Record success
                response_time = time.time() - start_time
                await self._record_success(response_time)
                
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = NetworkError(
                    message=f"Timeout calling {self.name}",
                    context={"timeout": self.config.timeout, "attempt": attempt + 1}
                )
                await self._record_failure(last_exception)
                
            except Exception as e:
                last_exception = e
                await self._record_failure(e)
            
            # Don't retry on the last attempt
            if attempt < self.config.max_retries:
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Retrying after failure",
                    service=self.name,
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(last_exception)
                )
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if isinstance(last_exception, BaseRendererException):
            raise last_exception
        else:
            raise ExternalServiceError(
                message=f"All retries exhausted for {self.name}",
                service=self.name,
                context={"attempts": self.config.max_retries + 1},
                cause=last_exception
            )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = min(
            self.config.initial_delay * (self.config.backoff_multiplier ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    async def _record_success(self, response_time: float):
        """Record a successful call."""
        self.success_count += 1
        
        if self.config.enable_metrics:
            self.metrics.total_calls += 1
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = time.time()
            self.metrics.update_response_time(response_time)
        
        # Transition from half-open to closed if enough successes
        if (self.state == CircuitState.HALF_OPEN and 
            self.success_count >= self.config.success_threshold):
            await self._transition_to_closed()
        
        logger.debug(
            "Circuit breaker success",
            service=self.name,
            state=self.state.value,
            success_count=self.success_count,
            response_time=response_time
        )
    
    async def _record_failure(self, exception: Exception):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.config.enable_metrics:
            self.metrics.total_calls += 1
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = self.last_failure_time
        
        # Transition to open if failure threshold reached
        if (self.state == CircuitState.CLOSED and 
            self.failure_count >= self.config.failure_threshold):
            await self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            # Go back to open on any failure in half-open state
            await self._transition_to_open()
        
        logger.warning(
            "Circuit breaker failure",
            service=self.name,
            state=self.state.value,
            failure_count=self.failure_count,
            error=str(exception)
        )
    
    async def _check_state_transition(self):
        """Check if circuit breaker should transition states."""
        if (self.state == CircuitState.OPEN and 
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.config.recovery_timeout):
            await self._transition_to_half_open()
    
    async def _transition_to_open(self):
        """Transition circuit breaker to open state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.success_count = 0
        
        if self.config.enable_metrics:
            self.metrics.circuit_open_count += 1
        
        logger.error(
            "Circuit breaker opened",
            service=self.name,
            old_state=old_state.value,
            failure_count=self.failure_count,
            recovery_timeout=self.config.recovery_timeout
        )
    
    async def _transition_to_half_open(self):
        """Transition circuit breaker to half-open state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        
        logger.info(
            "Circuit breaker half-opened",
            service=self.name,
            old_state=old_state.value
        )
    
    async def _transition_to_closed(self):
        """Transition circuit breaker to closed state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        
        logger.info(
            "Circuit breaker closed",
            service=self.name,
            old_state=old_state.value
        )
    
    def _get_retry_after(self) -> float:
        """Get retry after time for open circuit."""
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            return max(0, self.config.recovery_timeout - elapsed)
        return self.config.recovery_timeout
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "success_rate": self.metrics.success_rate(),
                "failure_rate": self.metrics.failure_rate(),
                "circuit_open_count": self.metrics.circuit_open_count,
                "average_response_time": self.metrics.average_response_time,
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.metrics.last_success_time
            }
        }
    
    async def reset(self):
        """Reset circuit breaker to closed state."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            
            logger.info("Circuit breaker reset", service=self.name)


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
    
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                config=config or self._default_config
            )
        return self._breakers[name]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers."""
        return {
            name: breaker.get_metrics()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of all services."""
        total_breakers = len(self._breakers)
        open_breakers = sum(
            1 for breaker in self._breakers.values()
            if breaker.state == CircuitState.OPEN
        )
        
        return {
            "total_services": total_breakers,
            "healthy_services": total_breakers - open_breakers,
            "unhealthy_services": open_breakers,
            "overall_health": "healthy" if open_breakers == 0 else "degraded",
            "services": {
                name: {
                    "state": breaker.state.value,
                    "health": "healthy" if breaker.state != CircuitState.OPEN else "unhealthy"
                }
                for name, breaker in self._breakers.items()
            }
        }


# Global circuit breaker manager
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Get a circuit breaker instance."""
    return _circuit_breaker_manager.get_breaker(name, config)


def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator for applying circuit breaker to functions."""
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(name, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in async context
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(breaker.call(func, *args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Predefined circuit breaker configurations
YOUTUBE_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=300.0,  # 5 minutes
    success_threshold=2,
    timeout=30.0,
    initial_delay=2.0,
    max_delay=600.0,  # 10 minutes
    max_retries=2
)

PINECONE_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=120.0,  # 2 minutes
    success_threshold=3,
    timeout=15.0,
    initial_delay=1.0,
    max_delay=300.0,  # 5 minutes
    max_retries=3
)

FIRESTORE_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,   # 1 minute
    success_threshold=2,
    timeout=10.0,
    initial_delay=0.5,
    max_delay=120.0,  # 2 minutes
    max_retries=3
)

BIGQUERY_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=180.0,  # 3 minutes
    success_threshold=2,
    timeout=60.0,  # Longer timeout for BigQuery
    initial_delay=2.0,
    max_delay=600.0,  # 10 minutes
    max_retries=2
)


# Convenience functions for common services
def youtube_circuit_breaker():
    """Get YouTube API circuit breaker."""
    return get_circuit_breaker("youtube_api", YOUTUBE_API_CONFIG)

def pinecone_circuit_breaker():
    """Get Pinecone circuit breaker."""
    return get_circuit_breaker("pinecone", PINECONE_CONFIG)

def firestore_circuit_breaker():
    """Get Firestore circuit breaker."""
    return get_circuit_breaker("firestore", FIRESTORE_CONFIG)

def bigquery_circuit_breaker():
    """Get BigQuery circuit breaker."""
    return get_circuit_breaker("bigquery", BIGQUERY_CONFIG)


if __name__ == "__main__":
    # Example usage and testing
    import asyncio
    
    async def test_circuit_breaker():
        """Test circuit breaker functionality."""
        
        # Create a test function that fails sometimes
        call_count = 0
        
        async def unreliable_service():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 5:
                raise Exception(f"Service failure {call_count}")
            return f"Success on call {call_count}"
        
        # Test with circuit breaker
        breaker = get_circuit_breaker("test_service")
        
        for i in range(10):
            try:
                result = await breaker.call(unreliable_service)
                print(f"Call {i+1}: {result}")
            except Exception as e:
                print(f"Call {i+1}: Failed - {e}")
            
            await asyncio.sleep(0.1)
        
        # Print metrics
        metrics = breaker.get_metrics()
        print(f"\nMetrics: {metrics}")
    
    # Run test
    asyncio.run(test_circuit_breaker())