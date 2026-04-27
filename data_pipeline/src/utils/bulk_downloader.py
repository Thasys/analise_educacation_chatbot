"""Download em streaming de arquivos grandes (ZIP/XLSX/CSV) para cache local.

Algumas fontes oficiais (INEP, IEA) não expõem API e exigem download de
microdados em pacotes ZIP/Excel. Este util cuida de:

  - Stream chunked para evitar carregar tudo em memória.
  - SHA-256 do conteúdo (proveniência).
  - Cache local: se o arquivo destino já existe e tem o mesmo SHA-256
    em um sidecar `.sha256`, evita re-download.
  - Retorno estruturado para uso pelos coletores.

A camada Bronze persiste o resultado processado (Parquet) — este util
serve apenas como buffer para fontes que não respondem em JSON.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class BulkDownloadResult:
    """Resultado de um download em massa."""

    local_path: Path
    source_url: str
    sha256: str
    bytes_downloaded: int
    cache_hit: bool


class BulkDownloader:
    """Baixa um arquivo de uma URL para `cache_root`, com streaming e SHA-256."""

    DEFAULT_CHUNK_BYTES = 1024 * 1024  # 1 MiB

    def __init__(
        self,
        cache_root: Path | str,
        *,
        http_client: httpx.Client | None = None,
        chunk_size: int = DEFAULT_CHUNK_BYTES,
    ) -> None:
        self.cache_root = Path(cache_root)
        self._http_client = http_client
        self.chunk_size = chunk_size

    def download(
        self,
        url: str,
        *,
        filename: str | None = None,
        timeout: float = 600.0,
    ) -> BulkDownloadResult:
        """Baixa `url` em streaming. Retorna metadados do arquivo local.

        Args:
            url: URL completa do arquivo.
            filename: nome do arquivo local. Se None, usa o último
                segmento do path da URL.
            timeout: timeout total da requisição em segundos.
        """
        target_path = self._resolve_target_path(url, filename)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        cached = self._cache_lookup(target_path)
        if cached is not None:
            log.info(
                "bulk_download.cache_hit",
                url=url,
                local_path=str(target_path),
                sha256=cached,
            )
            return BulkDownloadResult(
                local_path=target_path,
                source_url=url,
                sha256=cached,
                bytes_downloaded=target_path.stat().st_size,
                cache_hit=True,
            )

        client = self._http_client or httpx.Client(timeout=timeout)
        try:
            log.info("bulk_download.start", url=url, local_path=str(target_path))
            digest = hashlib.sha256()
            total = 0
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with target_path.open("wb") as fh:
                    for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        digest.update(chunk)
                        total += len(chunk)
        finally:
            if self._http_client is None:
                client.close()

        sha256 = digest.hexdigest()
        target_path.with_suffix(target_path.suffix + ".sha256").write_text(
            sha256, encoding="utf-8"
        )
        log.info(
            "bulk_download.done",
            url=url,
            local_path=str(target_path),
            sha256=sha256,
            bytes=total,
        )
        return BulkDownloadResult(
            local_path=target_path,
            source_url=url,
            sha256=sha256,
            bytes_downloaded=total,
            cache_hit=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_target_path(self, url: str, filename: str | None) -> Path:
        if filename:
            return self.cache_root / filename
        # Pega o último segmento, removendo querystring.
        tail = url.rsplit("/", 1)[-1].split("?", 1)[0]
        if not tail:
            raise ValueError(
                f"Não foi possível inferir o nome do arquivo da URL {url!r}; "
                "passe `filename=` explicitamente."
            )
        return self.cache_root / tail

    def _cache_lookup(self, target_path: Path) -> str | None:
        """Retorna o SHA-256 do arquivo cacheado se válido; senão None."""
        if not target_path.exists():
            return None
        sha_file = target_path.with_suffix(target_path.suffix + ".sha256")
        if not sha_file.exists():
            return None
        cached_sha = sha_file.read_text(encoding="utf-8").strip()
        # Confere se o arquivo no disco bate com o sidecar.
        actual = hashlib.sha256(target_path.read_bytes()).hexdigest()
        if actual != cached_sha:
            log.warning(
                "bulk_download.cache_invalid",
                local_path=str(target_path),
                cached_sha=cached_sha,
                actual_sha=actual,
            )
            return None
        return cached_sha
