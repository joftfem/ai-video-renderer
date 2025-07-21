#!/usr/bin/env python3
"""
Custom Exception Classes for AI Video Renderer

Provides structured error handling with categorized exceptions,
error codes, and detailed context for better debugging and monitoring.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import traceback
import structlog

logger = structlog.get_logger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    API_LIMIT = "api_limit"
    NETWORK = "network"
    DATA_VALIDATION = "data_validation"
    STORAGE = "storage"
    PROCESSING = "processing"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    USER_INPUT = "user_input"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseRendererException(Exception):
    """Base exception class for AI Video Renderer."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        self.retry_after = retry_after
        self.timestamp = None
        
        # Log the exception
        self._log_exception()
        
    def _log_exception(self):
        """Log the exception with structured data."""
        log_data = {
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context
        }
        
        if self.cause:
            log_data["cause"] = str(self.cause)
            
        if self.retry_after:
            log_data["retry_after"] = self.retry_after
            
        logger.error("Exception occurred", **log_data)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
            "retry_after": self.retry_after,
            "traceback": traceback.format_exc() if self.cause else None
        }


# Configuration Exceptions
class ConfigurationError(BaseRendererException):
    """Configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class InvalidConfigurationError(ConfigurationError):
    """Invalid configuration values."""
    
    def __init__(self, message: str, config_key: str, expected_type: str = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'config_key': config_key,
            'expected_type': expected_type
        })
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="INVALID_CONFIG",
            **kwargs
        )


class MissingConfigurationError(ConfigurationError):
    """Missing required configuration."""
    
    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            message=f"Missing required configuration: {config_key}",
            error_code="MISSING_CONFIG",
            config_key=config_key,
            **kwargs
        )


# Authentication Exceptions
class AuthenticationError(BaseRendererException):
    """Authentication-related errors."""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if service:
            context['service'] = service
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class InvalidAPIKeyError(AuthenticationError):
    """Invalid API key errors."""
    
    def __init__(self, service: str, **kwargs):
        super().__init__(
            message=f"Invalid API key for {service}",
            error_code="INVALID_API_KEY",
            service=service,
            **kwargs
        )


class ExpiredCredentialsError(AuthenticationError):
    """Expired credentials errors."""
    
    def __init__(self, service: str, **kwargs):
        super().__init__(
            message=f"Expired credentials for {service}",
            error_code="EXPIRED_CREDENTIALS",
            service=service,
            **kwargs
        )


# API Limit Exceptions
class APILimitError(BaseRendererException):
    """API rate limit and quota errors."""
    
    def __init__(self, message: str, service: str, limit_type: str, retry_after: int = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'service': service,
            'limit_type': limit_type
        })
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="API_LIMIT_EXCEEDED",
            category=ErrorCategory.API_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            retry_after=retry_after,
            **kwargs
        )


class RateLimitExceededError(APILimitError):
    """Rate limit exceeded errors."""
    
    def __init__(self, service: str, retry_after: int = None, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded for {service}",
            service=service,
            limit_type="rate_limit",
            error_code="RATE_LIMIT_EXCEEDED",
            retry_after=retry_after,
            **kwargs
        )


class QuotaExceededError(APILimitError):
    """Quota exceeded errors."""
    
    def __init__(self, service: str, quota_type: str = "daily", **kwargs):
        context = kwargs.get('context', {})
        context['quota_type'] = quota_type
        kwargs['context'] = context
        
        super().__init__(
            message=f"Quota exceeded for {service} ({quota_type})",
            service=service,
            limit_type="quota",
            error_code="QUOTA_EXCEEDED",
            **kwargs
        )


# Network Exceptions
class NetworkError(BaseRendererException):
    """Network-related errors."""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        if url:
            context['url'] = url
        if status_code:
            context['status_code'] = status_code
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ConnectionTimeoutError(NetworkError):
    """Connection timeout errors."""
    
    def __init__(self, url: str, timeout: int, **kwargs):
        context = kwargs.get('context', {})
        context['timeout'] = timeout
        kwargs['context'] = context
        
        super().__init__(
            message=f"Connection timeout to {url} after {timeout}s",
            error_code="CONNECTION_TIMEOUT",
            url=url,
            **kwargs
        )


class HTTPError(NetworkError):
    """HTTP error responses."""
    
    def __init__(self, url: str, status_code: int, response_text: str = None, **kwargs):
        context = kwargs.get('context', {})
        if response_text:
            context['response_text'] = response_text[:500]  # Limit response text
        kwargs['context'] = context
        
        super().__init__(
            message=f"HTTP {status_code} error for {url}",
            error_code="HTTP_ERROR",
            url=url,
            status_code=status_code,
            **kwargs
        )


# Data Validation Exceptions
class DataValidationError(BaseRendererException):
    """Data validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)[:100]  # Limit value length
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="DATA_VALIDATION_ERROR",
            category=ErrorCategory.DATA_VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class InvalidDataFormatError(DataValidationError):
    """Invalid data format errors."""
    
    def __init__(self, field: str, expected_format: str, actual_value: Any, **kwargs):
        context = kwargs.get('context', {})
        context['expected_format'] = expected_format
        kwargs['context'] = context
        
        super().__init__(
            message=f"Invalid format for {field}. Expected: {expected_format}",
            error_code="INVALID_DATA_FORMAT",
            field=field,
            value=actual_value,
            **kwargs
        )


# Storage Exceptions
class StorageError(BaseRendererException):
    """Storage-related errors."""
    
    def __init__(self, message: str, storage_type: str, operation: str = None, **kwargs):
        context = kwargs.get('context', {})
        context['storage_type'] = storage_type
        if operation:
            context['operation'] = operation
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DatabaseConnectionError(StorageError):
    """Database connection errors."""
    
    def __init__(self, database: str, **kwargs):
        super().__init__(
            message=f"Failed to connect to {database}",
            error_code="DB_CONNECTION_ERROR",
            storage_type=database,
            operation="connect",
            **kwargs
        )


class DataNotFoundError(StorageError):
    """Data not found errors."""
    
    def __init__(self, resource: str, identifier: str, storage_type: str, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'resource': resource,
            'identifier': identifier
        })
        kwargs['context'] = context
        
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="DATA_NOT_FOUND",
            storage_type=storage_type,
            operation="read",
            severity=ErrorSeverity.LOW,
            **kwargs
        )


# Processing Exceptions
class ProcessingError(BaseRendererException):
    """Processing-related errors."""
    
    def __init__(self, message: str, process_type: str, **kwargs):
        context = kwargs.get('context', {})
        context['process_type'] = process_type
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class VideoProcessingError(ProcessingError):
    """Video processing errors."""
    
    def __init__(self, message: str, video_id: str = None, **kwargs):
        context = kwargs.get('context', {})
        if video_id:
            context['video_id'] = video_id
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="VIDEO_PROCESSING_ERROR",
            process_type="video",
            **kwargs
        )


class AnalyticsProcessingError(ProcessingError):
    """Analytics processing errors."""
    
    def __init__(self, message: str, metric_type: str = None, **kwargs):
        context = kwargs.get('context', {})
        if metric_type:
            context['metric_type'] = metric_type
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="ANALYTICS_PROCESSING_ERROR",
            process_type="analytics",
            **kwargs
        )


# External Service Exceptions
class ExternalServiceError(BaseRendererException):
    """External service errors."""
    
    def __init__(self, message: str, service: str, **kwargs):
        context = kwargs.get('context', {})
        context['service'] = service
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class YouTubeAPIError(ExternalServiceError):
    """YouTube API specific errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="YOUTUBE_API_ERROR",
            service="youtube",
            **kwargs
        )


class PineconeError(ExternalServiceError):
    """Pinecone service errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="PINECONE_ERROR",
            service="pinecone",
            **kwargs
        )


class FirestoreError(ExternalServiceError):
    """Firestore service errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="FIRESTORE_ERROR",
            service="firestore",
            **kwargs
        )


# System Exceptions
class SystemError(BaseRendererException):
    """System-level errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SYSTEM_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class ResourceExhaustionError(SystemError):
    """Resource exhaustion errors."""
    
    def __init__(self, resource_type: str, **kwargs):
        context = kwargs.get('context', {})
        context['resource_type'] = resource_type
        kwargs['context'] = context
        
        super().__init__(
            message=f"Resource exhausted: {resource_type}",
            error_code="RESOURCE_EXHAUSTION",
            **kwargs
        )


# User Input Exceptions
class UserInputError(BaseRendererException):
    """User input validation errors."""
    
    def __init__(self, message: str, input_field: str = None, **kwargs):
        context = kwargs.get('context', {})
        if input_field:
            context['input_field'] = input_field
        kwargs['context'] = context
        
        super().__init__(
            message=message,
            error_code="USER_INPUT_ERROR",
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


# Exception Handler Utilities
class ExceptionHandler:
    """Centralized exception handling utilities."""
    
    @staticmethod
    def categorize_exception(exc: Exception) -> ErrorCategory:
        """Categorize an unknown exception."""
        exc_type = type(exc).__name__.lower()
        
        if 'config' in exc_type or 'setting' in exc_type:
            return ErrorCategory.CONFIGURATION
        elif 'auth' in exc_type or 'permission' in exc_type:
            return ErrorCategory.AUTHENTICATION
        elif 'network' in exc_type or 'connection' in exc_type or 'timeout' in exc_type:
            return ErrorCategory.NETWORK
        elif 'validation' in exc_type or 'value' in exc_type:
            return ErrorCategory.DATA_VALIDATION
        elif 'database' in exc_type or 'storage' in exc_type:
            return ErrorCategory.STORAGE
        else:
            return ErrorCategory.SYSTEM
    
    @staticmethod
    def wrap_exception(exc: Exception, context: Dict[str, Any] = None) -> BaseRendererException:
        """Wrap a generic exception in our custom exception hierarchy."""
        if isinstance(exc, BaseRendererException):
            return exc
            
        category = ExceptionHandler.categorize_exception(exc)
        
        return BaseRendererException(
            message=str(exc),
            error_code="WRAPPED_EXCEPTION",
            category=category,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            cause=exc
        )
    
    @staticmethod
    def get_error_summary(exceptions: List[BaseRendererException]) -> Dict[str, Any]:
        """Get summary statistics for a list of exceptions."""
        if not exceptions:
            return {}
            
        categories = {}
        severities = {}
        error_codes = {}
        
        for exc in exceptions:
            # Count by category
            cat = exc.category.value
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count by severity
            sev = exc.severity.value
            severities[sev] = severities.get(sev, 0) + 1
            
            # Count by error code
            code = exc.error_code
            error_codes[code] = error_codes.get(code, 0) + 1
            
        return {
            "total_exceptions": len(exceptions),
            "by_category": categories,
            "by_severity": severities,
            "by_error_code": error_codes,
            "most_common_category": max(categories.items(), key=lambda x: x[1])[0] if categories else None,
            "highest_severity": max(severities.keys(), key=lambda x: ErrorSeverity(x)) if severities else None
        }


# Decorator for exception handling
def handle_exceptions(default_return=None, reraise=True):
    """Decorator for automatic exception handling and logging."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseRendererException:
                if reraise:
                    raise
                return default_return
            except Exception as e:
                wrapped_exc = ExceptionHandler.wrap_exception(e)
                if reraise:
                    raise wrapped_exc
                return default_return
        return wrapper
    return decorator