"""Application settings loaded from .env / environment variables."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- External API (OpenAI-compatible) ---------------------------------
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # --- Ollama (used when llm_api_url is empty) --------------------------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Processing -------------------------------------------------------
    chunk_size: int = Field(default=12000, ge=100, le=1_000_000)
    chunk_overlap: int = Field(default=400, ge=0)
    max_file_size_mb: int = Field(default=25, ge=1, le=1024)
    max_files: int = Field(default=10, ge=1, le=100)
    doc_ttl_seconds: int = Field(default=3600, ge=1)
    request_timeout: float = Field(default=300.0, gt=0)
    summary_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_retries: int = Field(default=2, ge=0, le=10)
    # how many chunks of a large document to analyze in parallel
    summary_concurrency: int = Field(default=2, ge=1, le=8)

    # --- Logging ----------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False  # True = JSON (prod), False = readable console (dev)

    @model_validator(mode="after")
    def _check_overlap(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap musi być mniejsze od chunk_size")
        return self

    @model_validator(mode="after")
    def _check_log_level(self) -> "Settings":
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = self.log_level.upper()
        if level not in allowed:
            raise ValueError(f"log_level musi być jednym z: {', '.join(sorted(allowed))}")
        self.log_level = level
        return self

    @property
    def provider(self) -> str:
        return "external" if self.llm_api_url.strip() else "ollama"

    @property
    def active_base_url(self) -> str:
        if self.provider == "external":
            return self.llm_api_url.rstrip("/")
        return self.ollama_base_url.rstrip("/")

    @property
    def active_model(self) -> str:
        return self.llm_model if self.provider == "external" else self.ollama_model

    @property
    def active_label(self) -> str:
        if self.provider == "external":
            return f"API · {self.llm_model}"
        return f"Ollama · {self.ollama_model}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
