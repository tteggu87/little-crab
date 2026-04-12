"""little-crab configuration via Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    storage_mode: str = Field(default="local", alias="STORAGE_MODE")
    local_data_dir: str = Field(default="./opencrab_data", alias="LOCAL_DATA_DIR")
    chroma_collection: str = Field(
        default="little_crab_vectors", alias="CHROMA_COLLECTION"
    )
    chroma_embedding_provider: str = Field(
        default="onnx", alias="CHROMA_EMBEDDING_PROVIDER"
    )
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_embedding_model: str = Field(
        default="qwen3-embedding:4b", alias="OLLAMA_EMBEDDING_MODEL"
    )
    ollama_timeout: int = Field(default=60, alias="OLLAMA_TIMEOUT")

    # ------------------------------------------------------------------
    # MCP server
    # ------------------------------------------------------------------
    mcp_server_name: str = Field(default="little-crab", alias="MCP_SERVER_NAME")
    mcp_server_version: str = Field(default="0.1.0", alias="MCP_SERVER_VERSION")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def is_local(self) -> bool:
        return True

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.local_data_dir}/opencrab.db"

    @property
    def chroma_runtime_options(self) -> dict[str, Any]:
        return {
            "collection_name": self.chroma_collection,
            "embedding_provider": self.chroma_embedding_provider,
            "ollama_url": self.ollama_url,
            "ollama_embedding_model": self.ollama_embedding_model,
            "ollama_timeout": self.ollama_timeout,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached Settings singleton for tests and host reloads."""
    get_settings.cache_clear()
