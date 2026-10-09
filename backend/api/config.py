from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Zewnetrzne API (zgodne z OpenAI) ---------------------------------
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # --- Ollama (uzywana, gdy llm_api_url jest puste) ---------------------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Przetwarzanie -----------------------------------------------------
    chunk_size: int = 12000
    chunk_overlap: int = 400
    max_file_size_mb: int = 25
    max_files: int = 10
    doc_ttl_seconds: int = 3600
    request_timeout: float = 300.0
    summary_temperature: float = 0.3
    max_retries: int = 2

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
