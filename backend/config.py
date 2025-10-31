"""
Configuration module for Apollonian Gasket application.

Reference: .DESIGN_SPEC.md section 4 (Database Schema)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    # Database
    DATABASE_URL: str = "sqlite:///./gaskets.db"

    # Application
    DEBUG: bool = True
    APP_NAME: str = "Apollonian Gasket Visualizer"
    APP_VERSION: str = "1.0.0"

    # Generation limits (from .DESIGN_SPEC.md)
    MAX_GASKET_DEPTH: int = 15
    DEFAULT_GASKET_DEPTH: int = 5

    # Cache settings
    CACHE_SIZE_LIMIT_MB: int = 500

    class Config:
        env_file = ".env"


settings = Settings()
