"""
Voice Agent – Zentrales Konfigurationsmodul.
Lädt alle Einstellungen aus Umgebungsvariablen (.env) via Pydantic Settings.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Hauptkonfiguration – alle Werte aus .env / Umgebungsvariablen.
    Verwendung: settings = Settings() oder settings = get_settings()
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")
    ollama_embed_model: str = Field(
        default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL"
    )

    # Whisper (STT)
    whisper_model_size: str = Field(default="base", alias="WHISPER_MODEL_SIZE")
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", alias="WHISPER_COMPUTE_TYPE")

    # TTS (Piper)
    tts_de_model_path: str = Field(
        default="tts-models/de_DE-thorsten-high.onnx",
        alias="TTS_DE_MODEL_PATH",
    )
    tts_en_model_path: str = Field(
        default="tts-models/en_US-amy-medium.onnx",
        alias="TTS_EN_MODEL_PATH",
    )

    # RAG (ChromaDB)
    chroma_db_path: str = Field(default="./chroma_db", alias="CHROMA_DB_PATH")
    rag_chunk_size: int = Field(default=500, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=100, alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=3, alias="RAG_TOP_K")

    # Booking API
    booking_api_host: str = Field(default="0.0.0.0", alias="BOOKING_API_HOST")
    booking_api_port: int = Field(default=8080, alias="BOOKING_API_PORT")
    booking_db_path: str = Field(default="./booking.db", alias="BOOKING_DB_PATH")

    # Agent
    agent_default_language: str = Field(default="de", alias="AGENT_DEFAULT_LANGUAGE")

    # LiveKit
    livekit_url: str = Field(default="ws://localhost:7880", alias="LIVEKIT_URL")
    livekit_api_key: str = Field(default="devkey", alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="secret", alias="LIVEKIT_API_SECRET")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @property
    def tts_de_path(self) -> Path:
        p = Path(self.tts_de_model_path)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p

    @property
    def tts_en_path(self) -> Path:
        p = Path(self.tts_en_model_path)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p

    @property
    def chroma_path(self) -> Path:
        p = Path(self.chroma_db_path)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p

    @property
    def booking_db_abs_path(self) -> Path:
        p = Path(self.booking_db_path)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p


def get_settings() -> Settings:
    """Factory für Settings-Instanz (für Dependency Injection)."""
    return Settings()
