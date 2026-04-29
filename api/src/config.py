"""Settings centralizados da API.

Carrega variaveis de ambiente via Pydantic Settings. Defaults priorizam
um cenario de desenvolvimento local; todos os campos podem ser
sobrescritos via .env ou variaveis de processo.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao unificada do gateway FastAPI.

    Variaveis tem prefixo `API_` para nao colidir com vars de outros
    servicos (ex.: `DUCKDB_PATH=/data/...` definido para Docker no .env
    global). Em casos onde nao ha prefixo (`ENVIRONMENT`, `LOG_LEVEL`),
    usamos `validation_alias=AliasChoices(...)` para aceitar tanto a
    var prefixada quanto a generica.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- projeto -----------------------------------------------------
    project_name: str = "analise-education-chatbot"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("API_ENVIRONMENT", "ENVIRONMENT"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("API_LOG_LEVEL", "LOG_LEVEL"),
    )
    api_version: str = "0.1.0"

    # ---- DuckDB ------------------------------------------------------
    # Path para o DuckDB criado pelo dbt build. Default relativo a `api/`
    # assume layout do repositorio. Em Docker sobrescrever com
    # API_DUCKDB_PATH=/data/duckdb/education.duckdb.
    duckdb_path: Path = Field(
        default=Path("../data/duckdb/education.duckdb"),
        validation_alias="API_DUCKDB_PATH",
    )
    duckdb_memory_limit: str = Field(
        default="4GB",
        validation_alias=AliasChoices("API_DUCKDB_MEMORY_LIMIT", "DUCKDB_MEMORY_LIMIT"),
    )
    duckdb_threads: int = Field(
        default=4,
        validation_alias=AliasChoices("API_DUCKDB_THREADS", "DUCKDB_THREADS"),
    )

    # ---- API ---------------------------------------------------------
    api_cors_origins: str = "http://localhost:3000"
    api_ratelimit_default: str = "60/minute"
    api_ratelimit_disabled: bool = False

    # ---- propriedades derivadas --------------------------------------
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
