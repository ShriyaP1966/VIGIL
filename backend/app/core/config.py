from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "VIGIL"
    APP_VERSION: str = "3.1.0"
    APP_MODE: str = "offline"  # offline | local | cloud
    DATABASE_URL: str = "sqlite:///./vigil.db"
    T_CANDIDATE: float = 0.75
    LOG_LEVEL: str = "INFO"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: Optional[str] = "gemini-1.5-flash"
    FRONTEND_ORIGIN: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
