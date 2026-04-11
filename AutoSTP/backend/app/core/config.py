"""Configuration settings for the application."""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AutoSTP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://autostp:autostp_password@localhost:5432/autostp_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # OPENROUTER API
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "llama3-8b"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 30
    ALLOWED_FILE_EXTENSIONS: List[str] = [".docx", ".txt"]

    # Auto-save
    AUTO_SAVE_INTERVAL_SECONDS: int = 300  # 5 minutes

    # Pricing (in BYN)
    PRICING_DOCUMENT_SMALL_PAGES: int = 40
    PRICING_DOCUMENT_SMALL_PRICE: float = 7.0
    PRICING_DOCUMENT_LARGE_PRICE: float = 15.0
    PRICING_TEMPLATE_PRICE: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
