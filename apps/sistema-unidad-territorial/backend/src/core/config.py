from abc import ABC, abstractmethod
from functools import lru_cache
from os import getenv, path
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentLoader(ABC):
    @abstractmethod
    def load(self):
        pass


class DotEnvLoader(EnvironmentLoader):
    def load(self):
        load_dotenv()


class APISettings(BaseModel):
    """API specific settings."""
    v1_str: str = "/api/v1"
    project_name: str = "Sistema Unidad Territorial"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30


class GoogleOAuthSettings(BaseModel):
    """Google OAuth settings."""
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "openid email profile"


class GoogleMapsSettings(BaseModel):
    """Google Maps API settings."""
    api_key: Optional[str] = Field(default=None, description="Google Maps API Key")
    enable_validation: bool = Field(default=False, description="Habilitar validación de direcciones con Google Maps")
    timeout_seconds: int = Field(default=10, description="Timeout para requests a Google Maps API")


class FileSettings(BaseModel):
    """File storage specific settings."""
    upload_directory: str = Field(default="uploads", description="Directorio base para archivos subidos")
    base_url: str = Field(default="/files", description="URL base para servir archivos")
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Tamaño máximo de archivo en bytes")
    allowed_extensions: list[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".pdf"], 
        description="Extensiones de archivo permitidas"
    )


class EmailSettings(BaseModel):
    """Email configuration settings."""
    smtp_server: str = Field(default="smtp.gmail.com", description="Servidor SMTP")
    smtp_port: int = Field(default=587, description="Puerto SMTP")
    smtp_username: Optional[str] = Field(default=None, description="Usuario SMTP (email)")
    smtp_password: Optional[str] = Field(default=None, description="Contraseña SMTP (contraseña de aplicación)")
    from_email: Optional[str] = Field(default=None, description="Email remitente")
    from_name: str = Field(default="Sistema Unidad Territorial", description="Nombre del remitente")
    use_tls: bool = Field(default=True, description="Usar TLS")
    enabled: bool = Field(default=False, description="Habilitar envío de emails")

    @property
    def is_configured(self) -> bool:
        """Verificar si el email está configurado correctamente."""
        return all([
            self.smtp_username,
            self.smtp_password,
            self.from_email
        ])


class DatabaseSettings(BaseModel):
    """Database connection settings."""
    user: str
    password: str
    host: str
    port: str
    name: str
    db_schema: str = "sistema_unidad_territorial"
    pool_size: int = 20
    max_overflow: int = 10

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class MigrationSettings(BaseModel):
    """Alembic migration settings."""
    base_dir: str = Field(default="alembic")
    development_versions_dir: str = Field(default="versions/development")
    production_versions_dir: str = Field(default="versions/production")

    def get_versions_path(self, environment: str, script_location: str) -> str:
        """Get the versions path based on environment."""
        if environment.upper() in ["DEVELOPMENT", "STAGING"]:
            return path.join(script_location, self.development_versions_dir)
        return path.join(script_location, self.production_versions_dir)


class Settings(BaseSettings):
    """Application settings."""
    debug: bool = False
    environment: Literal["DEVELOPMENT", "STAGING", "PRODUCTION"]
    database: DatabaseSettings
    migrations: MigrationSettings = MigrationSettings()
    api: APISettings
    google_oauth: GoogleOAuthSettings
    google_maps: GoogleMapsSettings = Field(default_factory=GoogleMapsSettings)
    files: FileSettings = Field(default_factory=FileSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)

    @classmethod
    def get_database_settings(cls, environment: str) -> dict[str, Any]:
        """Get database settings based on environment."""
        if environment.upper() == "DEVELOPMENT":
            return {
                "user": "postgres",
                "password": "secreta123",
                "host": "localhost",
                "port": "5432",
                "name": "postgres",
                "db_schema": "sistema_unidad_territorial",
                "pool_size": 20,
                "max_overflow": 10,
            }
        else:
            return {
                "user": getenv("DB_USER_QP"),
                "password": getenv("DB_PASSWORD_QP"),
                "host": getenv("DB_HOST_QP"),
                "port": getenv("DB_PORT_QP"),
                "name": getenv("DB_DATABASE_QP"),
                "db_schema": getenv("DB_SCHEMA"),
                "pool_size": 20,
                "max_overflow": 10,
            }

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        validate_default=True,
        extra='ignore'
    )


@lru_cache
def get_settings(env_loader: EnvironmentLoader = DotEnvLoader()) -> Settings:
    """Get cached settings instance."""
    env_loader.load()
    environment = getenv("ENVIRONMENT")

    return Settings(
        environment=environment,
        debug=getenv("DEBUG", "false").lower() == "true",
        database=DatabaseSettings(**Settings.get_database_settings(environment)),
        api=APISettings(
            secret_key=getenv("SECRET_KEY"),
        ),
        google_oauth=GoogleOAuthSettings(
            client_id=getenv("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            redirect_uri=getenv("GOOGLE_OAUTH_REDIRECT_URI"),
        ),
        google_maps=GoogleMapsSettings(
            api_key=getenv("GOOGLE_MAPS_API_KEY"),
            enable_validation=getenv("GOOGLE_MAPS_ENABLE_VALIDATION", "false").lower() == "true",
            timeout_seconds=int(getenv("GOOGLE_MAPS_TIMEOUT_SECONDS", "10"))
        ),
        email=EmailSettings(
            smtp_username=getenv("SMTP_USERNAME"),
            smtp_password=getenv("SMTP_PASSWORD"),
            from_email=getenv("SMTP_FROM_EMAIL"),
            from_name=getenv("SMTP_FROM_NAME", "Sistema Unidad Territorial"),
            enabled=getenv("SMTP_ENABLED", "false").lower() == "true"
        )
    )


settings = get_settings()
