import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Freight Forwarding Phase 1 API"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str

    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800

    AUTO_CREATE_TABLES: bool = True

    AI_PROVIDER: str = "groq"
    AI_ENABLED: bool = False
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_CONTEXT_ROWS: int = 30
    AI_LOG_INTERACTIONS: bool = True

    GMAIL_ENABLED: bool = False
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/email/oauth/callback"
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly"
    EMAIL_MAX_RESULTS: int = 20
    EMAIL_LOOKBACK_DAYS: int = 30
    TOKEN_ENCRYPTION_KEY: str = ""

    ADMIN_NAME: str = "Admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        value = self.BACKEND_CORS_ORIGINS.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def gmail_scopes(self) -> list[str]:
        return [scope.strip() for scope in self.GMAIL_SCOPES.split(",") if scope.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
