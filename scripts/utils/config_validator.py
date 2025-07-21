#!/usr/bin/env python3
"""
Configuration Validator for AI Video Renderer

Provides centralized configuration management with validation,
environment-specific overlays, and type safety using Pydantic.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, validator, root_validator
from pydantic.env_settings import BaseSettings
import structlog

logger = structlog.get_logger(__name__)


class GoogleCloudConfig(BaseModel):
    """Google Cloud Platform configuration."""
    project_id: str = Field(..., description="GCP Project ID")
    region: str = Field(default="us-central1", description="GCP Region")
    credentials_path: Optional[str] = Field(None, description="Service account key path")
    
    @validator('project_id')
    def validate_project_id(cls, v):
        if not v or len(v) < 6:
            raise ValueError("Project ID must be at least 6 characters")
        return v


class BigQueryConfig(BaseModel):
    """BigQuery configuration."""
    dataset_id: str = Field(default="ai_renderer", description="BigQuery dataset")
    analytics_table: str = Field(default="analytics", description="Analytics table name")
    cost_table: str = Field(default="cost_tracking", description="Cost tracking table")
    location: str = Field(default="US", description="BigQuery location")
    partition_field: str = Field(default="timestamp", description="Partition field")
    partition_type: Literal["DAY", "HOUR", "MONTH"] = Field(default="DAY")
    

class FirestoreConfig(BaseModel):
    """Firestore configuration."""
    collection_name: str = Field(default="video_memory", description="Main collection")
    ttl_field: str = Field(default="expires_at", description="TTL field name")
    ttl_days: int = Field(default=45, ge=1, le=365, description="TTL in days")
    

class PineconeConfig(BaseModel):
    """Pinecone vector database configuration."""
    api_key: str = Field(..., description="Pinecone API key")
    environment: str = Field(..., description="Pinecone environment")
    index_name: str = Field(default="video-embeddings", description="Index name")
    dimension: int = Field(default=384, ge=128, le=2048, description="Vector dimension")
    metric: Literal["cosine", "euclidean", "dotproduct"] = Field(default="cosine")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Pinecone API key is required")
        return v


class YouTubeAPIConfig(BaseModel):
    """YouTube Data API configuration."""
    api_key: str = Field(..., description="YouTube Data API key")
    quota_limit: int = Field(default=10000, ge=1000, description="Daily quota limit")
    rate_limit_per_second: int = Field(default=100, ge=1, description="Rate limit per second")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or len(v) < 20:
            raise ValueError("YouTube API key is required")
        return v


class GoogleSheetsConfig(BaseModel):
    """Google Sheets integration configuration."""
    enabled: bool = Field(default=False, description="Enable Sheets sync")
    spreadsheet_id: Optional[str] = Field(None, description="Spreadsheet ID")
    worksheet_name: str = Field(default="Analytics", description="Worksheet name")
    
    @root_validator
    def validate_sheets_config(cls, values):
        if values.get('enabled') and not values.get('spreadsheet_id'):
            raise ValueError("Spreadsheet ID required when Sheets is enabled")
        return values


class AnalyticsConfig(BaseModel):
    """Analytics collection configuration."""
    auto_collection: bool = Field(default=True, description="Enable auto collection")
    collection_interval_hours: int = Field(default=24, ge=1, le=168)
    metrics_to_collect: List[str] = Field(
        default=[
            "views", "likes", "comments", "shares", "impressions", 
            "ctr", "average_view_duration", "thumbnail_performance"
        ]
    )
    performance_thresholds: Dict[str, float] = Field(
        default={
            "min_ctr": 0.02,
            "min_avg_view_duration": 30.0,
            "min_engagement_rate": 0.05
        }
    )


class MemorySystemConfig(BaseModel):
    """Hybrid memory system configuration."""
    enable_logging: bool = Field(default=True, description="Enable event logging")
    cleanup_schedule_hours: int = Field(default=24, ge=1, le=168)
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    batch_size: int = Field(default=100, ge=1, le=1000, description="Processing batch size")
    

class CostTrackingConfig(BaseModel):
    """Cost tracking configuration."""
    tts_cost_per_char: float = Field(default=0.000016, ge=0)
    thumbnail_cost_per_generation: float = Field(default=0.02, ge=0)
    moderation_cost_per_request: float = Field(default=0.001, ge=0)
    budget_alert_threshold: float = Field(default=100.0, ge=0)
    

class SecurityConfig(BaseModel):
    """Security configuration."""
    api_key_rotation_days: int = Field(default=90, ge=30, le=365)
    enable_encryption: bool = Field(default=True)
    allowed_origins: List[str] = Field(default=["localhost", "127.0.0.1"])
    rate_limit_requests_per_minute: int = Field(default=60, ge=1)
    

class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration."""
    health_check_interval_seconds: int = Field(default=30, ge=5)
    metrics_retention_days: int = Field(default=30, ge=1, le=365)
    alert_channels: List[str] = Field(default=["email"], description="Alert channels")
    sla_uptime_target: float = Field(default=0.999, ge=0.9, le=1.0)
    

class PerformanceConfig(BaseModel):
    """Performance optimization configuration."""
    enable_async: bool = Field(default=True)
    connection_pool_size: int = Field(default=10, ge=1, le=100)
    cache_ttl_seconds: int = Field(default=300, ge=60)
    batch_processing_size: int = Field(default=100, ge=1, le=1000)
    

class DevelopmentConfig(BaseModel):
    """Development and testing configuration."""
    debug_mode: bool = Field(default=False)
    mock_apis: bool = Field(default=False)
    test_data_enabled: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    

class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Core configurations
    google_cloud: GoogleCloudConfig
    bigquery: BigQueryConfig = BigQueryConfig()
    firestore: FirestoreConfig = FirestoreConfig()
    pinecone: PineconeConfig
    youtube_api: YouTubeAPIConfig
    
    # Optional configurations
    google_sheets: GoogleSheetsConfig = GoogleSheetsConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()
    memory_system: MemorySystemConfig = MemorySystemConfig()
    cost_tracking: CostTrackingConfig = CostTrackingConfig()
    security: SecurityConfig = SecurityConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    performance: PerformanceConfig = PerformanceConfig()
    development: DevelopmentConfig = DevelopmentConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        
    @root_validator
    def validate_config(cls, values):
        """Cross-field validation."""
        # Validate production settings
        dev_config = values.get('development', DevelopmentConfig())
        if not dev_config.debug_mode:
            # Production validations
            security = values.get('security', SecurityConfig())
            if security.enable_encryption is False:
                logger.warning("Encryption disabled in production mode")
                
        return values


class ConfigManager:
    """Configuration manager with environment-specific overlays."""
    
    def __init__(self, config_path: Optional[Path] = None, environment: str = "development"):
        self.config_path = config_path or Path("config/analytics_config.yaml")
        self.environment = environment
        self._config: Optional[AppConfig] = None
        
    def load_config(self) -> AppConfig:
        """Load and validate configuration with environment overlay."""
        if self._config is not None:
            return self._config
            
        try:
            # Load base configuration
            base_config = self._load_yaml_config(self.config_path)
            
            # Load environment-specific overlay
            env_config_path = self.config_path.parent / f"environments/{self.environment}.yaml"
            if env_config_path.exists():
                env_config = self._load_yaml_config(env_config_path)
                base_config = self._merge_configs(base_config, env_config)
                
            # Apply environment variables
            self._config = AppConfig(**base_config)
            
            logger.info(
                "Configuration loaded successfully",
                environment=self.environment,
                config_path=str(self.config_path)
            )
            
            return self._config
            
        except Exception as e:
            logger.error(
                "Failed to load configuration",
                error=str(e),
                config_path=str(self.config_path)
            )
            raise
            
    def _load_yaml_config(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
            
    def _merge_configs(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration dictionaries recursively."""
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def validate_runtime_config(self) -> bool:
        """Validate runtime configuration and dependencies."""
        try:
            config = self.load_config()
            
            # Check required environment variables
            required_env_vars = [
                "GOOGLE_APPLICATION_CREDENTIALS",
                "PINECONE_API_KEY",
                "YOUTUBE_API_KEY"
            ]
            
            missing_vars = [var for var in required_env_vars if not os.getenv(var)]
            if missing_vars:
                logger.error(
                    "Missing required environment variables",
                    missing_vars=missing_vars
                )
                return False
                
            # Validate API connectivity (optional)
            if hasattr(config, 'validate_connectivity'):
                return config.validate_connectivity()
                
            return True
            
        except Exception as e:
            logger.error("Configuration validation failed", error=str(e))
            return False
            
    def get_config(self) -> AppConfig:
        """Get validated configuration instance."""
        return self.load_config()
        
    def reload_config(self) -> AppConfig:
        """Reload configuration from disk."""
        self._config = None
        return self.load_config()


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(environment: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    
    if _config_manager is None:
        env = environment or os.getenv("ENVIRONMENT", "development")
        _config_manager = ConfigManager(environment=env)
        
    return _config_manager


def get_config() -> AppConfig:
    """Get validated application configuration."""
    return get_config_manager().get_config()


if __name__ == "__main__":
    # CLI for configuration validation
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration validator")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    parser.add_argument("--environment", default="development", help="Environment name")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't load")
    
    args = parser.parse_args()
    
    try:
        manager = ConfigManager(args.config, args.environment)
        
        if args.validate_only:
            success = manager.validate_runtime_config()
            print(f"Configuration validation: {'PASSED' if success else 'FAILED'}")
        else:
            config = manager.load_config()
            print(f"Configuration loaded successfully for environment: {args.environment}")
            print(f"Project ID: {config.google_cloud.project_id}")
            print(f"Region: {config.google_cloud.region}")
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)