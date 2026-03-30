"""Application configuration loaded from environment / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/po_management"
    SYNC_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/po_management"

    # JWT
    SECRET_KEY: str = "change-me-in-production-at-least-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # OAuth Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # AI
    ANTHROPIC_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    FRONTEND_ORIGIN: str = "http://localhost:8000"


settings = Settings()
