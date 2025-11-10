"""
Configuración centralizada del sistema usando Pydantic Settings
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicación
    app_name: str = "logistics-microservice"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Database Selection
    db_type: str = "mysql"  # "mysql" o "postgres"
    
    # MySQL (XAMPP Local)
    mysql_host: str = "localhost"
    mysql_port: int = 3307
    mysql_database: str = "logistics_db"
    mysql_user: str = "root"
    mysql_password: str = ""
    
    # Supabase Database (PostgreSQL)
    supabase_db_host: str = ""
    supabase_db_port: int = 5432
    supabase_db_name: str = "postgres"
    supabase_db_user: str = "postgres"
    supabase_db_password: str = ""
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    db_pool_timeout: float = 10.0

    # Evolution API (WhatsApp)
    evolution_api_url: str
    evolution_api_key: str
    evolution_instance_name: str = "SATECH"

    # Gemini AI
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # Floatify
    floatify_api_url: Optional[str] = None
    floatify_api_key: Optional[str] = None

    # Wialon
    wialon_token: Optional[str] = None

    # Security
    webhook_secret: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    allowed_origins: list[str] = ["*"]

    # Timeouts (en segundos)
    http_timeout: int = 30
    gemini_timeout: int = 60

    # Retry configuration
    max_retries: int = 3
    retry_initial_delay: float = 1.0
    retry_max_delay: float = 10.0

    # Sentry (opcional)
    sentry_dsn: Optional[str] = None

    @property
    def database_url(self) -> str:
        """Construir URL de conexión a la base de datos"""
        return (
            f"postgresql://{self.supabase_db_user}:{self.supabase_db_password}"
            f"@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"
        )

    @property
    def is_production(self) -> bool:
        """Verificar si estamos en producción"""
        return self.environment.lower() == "production"

    @property
    def json_logs(self) -> bool:
        """Usar logs en formato JSON en producción"""
        return self.is_production


# Instancia global de configuración
settings = Settings()

