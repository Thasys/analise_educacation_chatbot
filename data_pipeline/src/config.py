"""Settings centralizados do data pipeline.

Carrega variáveis de ambiente via Pydantic Settings. Os defaults priorizam
um cenário de desenvolvimento local (rodando fora dos containers Docker),
mas todos os campos podem ser sobrescritos via `.env` ou variáveis de processo.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração unificada do pipeline.

    O arquivo `.env` no diretório do projeto é a fonte canônica.
    Campos não declarados aqui são ignorados (extra='ignore').
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- projeto -----------------------------------------------------------
    project_name: str = "analise-education-chatbot"
    environment: str = "development"
    log_level: str = "INFO"
    tz: str = "America/Sao_Paulo"

    # ---- armazenamento -----------------------------------------------------
    # Default aponta para o diretório `data/` do repositório, mas em container
    # o docker-compose monta o volume em `/data`.
    data_root: Path = Field(default=Path("./data"))

    # ---- Postgres ----------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "educacao"
    postgres_password: str = ""
    postgres_db: str = "educacao_metadata"
    database_url: str | None = None

    # ---- APIs externas -----------------------------------------------------
    ibge_sidra_api_base: str = "https://apisidra.ibge.gov.br"
    worldbank_api_base: str = "https://api.worldbank.org/v2"
    oecd_sdmx_base: str = "https://sdmx.oecd.org/public/rest"
    ipea_odata_api_base: str = "http://www.ipeadata.gov.br/api/odata4"
    unesco_uis_api_base: str = "https://api.uis.unesco.org/sdmx"
    eurostat_api_base: str = (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0"
    )
    cepalstat_api_base: str = "https://statistics.cepal.org/portal/cepalstat/api/v1"

    # ---- limites de rede ---------------------------------------------------
    http_timeout_seconds: float = 120.0
    http_retries: int = 3

    # ---- propriedades derivadas -------------------------------------------
    @property
    def bronze_root(self) -> Path:
        return self.data_root / "bronze"

    @property
    def silver_root(self) -> Path:
        return self.data_root / "silver"

    @property
    def gold_root(self) -> Path:
        return self.data_root / "gold"

    @property
    def effective_database_url(self) -> str:
        """URL Postgres a usar.

        Se `database_url` não estiver definida ou contiver o placeholder
        `troque_esta_senha`, monta a URL a partir dos campos individuais
        (que sempre têm preferência neste caso).
        """
        if self.database_url and "troque_esta_senha" not in self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
