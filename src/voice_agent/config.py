from functools import lru_cache
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    eleven_api_key: str = Field(default_factory=lambda: os.getenv("ELEVEN_API_KEY", ""))
    eleven_voice_id: str = Field(default_factory=lambda: os.getenv("ELEVEN_VOICE_ID", ""))
    eleven_stt_model_id: str = Field(default_factory=lambda: os.getenv("ELEVEN_STT_MODEL_ID", "scribe_v1"))
    debug_responses: bool = Field(default_factory=lambda: os.getenv("VOICE_AGENT_DEBUG", "false").lower() == "true")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
