from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    DATABASE_URL: str = "sqlite:///./apollonian_gasket.db"
    DEBUG: bool = True
    MAX_RECURSION_DEPTH: int = 12
    CACHE_SIZE_LIMIT_MB: int = 500

    class Config:
        env_file = ".env"


settings = Settings()
