"""Application settings loaded from environment / .env (no secrets in code)."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_whisper_model: str = "whisper-large-v3-turbo"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    default_llm_provider: str = "groq"
    default_stt_provider: str = "groq"
    ai_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    max_audio_mb: float = Field(default=15.0, gt=0, le=25)
    database_path: str = "medtriage.db"
    cors_origins: str = ("http://localhost:3000,http://localhost:5173,"
                         "http://127.0.0.1:3000,http://127.0.0.1:5173")
    emergency_number_hint: str = "112"
    report_font_path: str = ""  # optional path to a Unicode .ttf for PDFs

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        return self.default_llm_provider == "groq" and bool(self.groq_api_key.strip())

    @property
    def stt_configured(self) -> bool:
        return self.default_stt_provider == "groq" and bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
