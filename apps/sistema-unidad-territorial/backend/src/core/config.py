from abc import ABC, abstractmethod
from functools import lru_cache
from os import getenv, path
from typing import Any, Literal

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


class DatabaseSettings(BaseModel):
    """Database connection settings."""
    user: str
    password: str
    host: str
    port: str
    name: str
    schema: str = "sistema_unidad_territorial"
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
                "schema": "sistema_unidad_territorial",
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
                "schema": getenv("DB_SCHEMA"),
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
        )
    )


settings = get_settings()
