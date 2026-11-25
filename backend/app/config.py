"""
Configuration module for VoxSell.

Uses pydantic-settings to validate and inject environment variables from .env
into typed settings with fail-fast validation.
"""

from functools import lru_cache
from typing import List, Union, Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """

    # Application
    APP_NAME: str = "VoxSell"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/voxsell_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/voxsell_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./knowledge_base/chroma_db"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # Deepgram (Speech-to-Text)
    DEEPGRAM_API_KEY: str = Field(default="", description="Deepgram API key for streaming STT")

    # LLM Provider
    LLM_PROVIDER: str = Field(default="openai", description="LLM provider: openai, groq, gemini")
    LLM_API_KEY: str = Field(default="", description="API key for chosen LLM provider")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="Target model name")
    LLM_TEMPERATURE: float = 0.2

    # TTS Provider & Multilingual Voice Configuration
    TTS_PROVIDER: str = Field(default="deepgram_aura", description="TTS provider: deepgram_aura, cartesia, elevenlabs, sarvam")
    TTS_API_KEY: str = Field(default="", description="API key for chosen TTS provider")
    TTS_VOICE_ID: str = Field(default="aura-asteria-en", description="Voice ID / Speaker model")
    TTS_VOICE_MAP: Dict[str, str] = {
        "en": "aura-asteria-en",
        "hinglish": "aura-asteria-en",
        "hi": "hi-IN-Wavenet-A",
        "pa": "pa-IN-Wavenet-A",
    }
    SARVAM_API_KEY: str = ""
    GOOGLE_TTS_API_KEY: str = ""

    # Calendar Integration
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = ""
    GOOGLE_CALENDAR_ID: str = "primary"

    # CRM Integration
    CRM_PROVIDER: str = "postgres"  # 'postgres' or 'hubspot'
    HUBSPOT_ACCESS_TOKEN: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Convert comma-separated string or list to list of origin strings."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return ["*"]
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached instance of application settings.
    Avoids re-reading .env on every dependency injection call.
    """
    return Settings()
