"""Settings centralizados do servico de agentes CrewAI.

Carrega variaveis de ambiente via Pydantic Settings. Defaults priorizam
um cenario de desenvolvimento local; todos os campos podem ser
sobrescritos via .env ou variaveis de processo.

Convencao: prefix `AGENTS_*` para evitar colisao com vars de outros
servicos. Vars genericas legadas (ANTHROPIC_API_KEY) sao aceitas via
`AliasChoices`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao unificada do servico de agentes."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # ---- projeto -----------------------------------------------------
    project_name: str = "analise-education-chatbot"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("AGENTS_ENVIRONMENT", "ENVIRONMENT"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("AGENTS_LOG_LEVEL", "LOG_LEVEL"),
    )
    service_version: str = "0.1.0"

    # ---- gateway HTTP (FastAPI da Fase 4) ----------------------------
    gateway_base_url: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices(
            "AGENTS_GATEWAY_BASE_URL", "API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL"
        ),
        description="URL base do FastAPI gateway. Tools chamam endpoints sob /api/data/*.",
    )
    gateway_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="AGENTS_GATEWAY_TIMEOUT",
    )
    gateway_max_retries: int = Field(
        default=2,
        validation_alias="AGENTS_GATEWAY_MAX_RETRIES",
    )

    # ---- LLM (Anthropic) ---------------------------------------------
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AGENTS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"
        ),
    )
    llm_smart_model: str = Field(
        default="claude-sonnet-4-5",
        validation_alias="AGENTS_LLM_SMART_MODEL",
    )
    llm_fast_model: str = Field(
        default="claude-haiku-4-5",
        validation_alias="AGENTS_LLM_FAST_MODEL",
    )
    llm_temperature: float = Field(
        default=0.2,
        validation_alias="AGENTS_LLM_TEMPERATURE",
        ge=0.0,
        le=1.0,
    )
    llm_max_tokens: int = Field(
        default=4096,
        validation_alias="AGENTS_LLM_MAX_TOKENS",
        ge=64,
        le=16384,
    )

    # ---- RAG (ChromaDB) ----------------------------------------------
    rag_persist_dir: Path = Field(
        default=Path("../data/chromadb/edu_literature"),
        validation_alias="AGENTS_RAG_PERSIST_DIR",
        description="Diretorio do ChromaDB embedded. Default relativo a agents/.",
    )
    rag_embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="AGENTS_RAG_EMBEDDING_MODEL",
    )
    rag_collection_name: str = Field(
        default="edu_literature",
        validation_alias="AGENTS_RAG_COLLECTION",
    )
    rag_default_k: int = Field(
        default=5,
        validation_alias="AGENTS_RAG_DEFAULT_K",
        ge=1,
        le=50,
    )

    # ---- observabilidade ---------------------------------------------
    langfuse_host: str | None = Field(
        default=None,
        validation_alias="AGENTS_LANGFUSE_HOST",
    )
    langfuse_public_key: SecretStr | None = Field(
        default=None,
        validation_alias="AGENTS_LANGFUSE_PUBLIC_KEY",
    )
    langfuse_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias="AGENTS_LANGFUSE_SECRET_KEY",
    )

    # ---- propriedades derivadas --------------------------------------
    @property
    def has_anthropic_key(self) -> bool:
        if self.anthropic_api_key is None:
            return False
        secret = self.anthropic_api_key.get_secret_value().strip()
        return bool(secret) and not secret.startswith("sk-ant-...")

    @property
    def has_langfuse(self) -> bool:
        return bool(
            self.langfuse_host and self.langfuse_public_key and self.langfuse_secret_key
        )

    def llm_for(self, role: Literal["fast", "smart"]) -> str:
        return self.llm_fast_model if role == "fast" else self.llm_smart_model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
