"""Testes do BulkDownloader (streaming + cache SHA-256)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.utils.bulk_downloader import BulkDownloader, BulkDownloadResult


PAYLOAD_BYTES = b"hello,world\n1,2\n3,4\n" * 1024  # ~20 KiB


def _mock_client(payload: bytes, *, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_download_writes_file_and_returns_metadata(tmp_path: Path) -> None:
    client = _mock_client(PAYLOAD_BYTES)
    dl = BulkDownloader(cache_root=tmp_path, http_client=client)
    result = dl.download(
        "https://example.com/path/data.zip", filename="data.zip"
    )
    client.close()

    assert isinstance(result, BulkDownloadResult)
    assert result.local_path == tmp_path / "data.zip"
    assert result.local_path.exists()
    assert result.local_path.read_bytes() == PAYLOAD_BYTES
    assert result.bytes_downloaded == len(PAYLOAD_BYTES)
    assert result.sha256 == hashlib.sha256(PAYLOAD_BYTES).hexdigest()
    assert result.cache_hit is False
    # Sidecar .sha256 escrito
    assert (tmp_path / "data.zip.sha256").read_text(encoding="utf-8") == result.sha256


def test_filename_inferred_from_url_when_not_passed(tmp_path: Path) -> None:
    client = _mock_client(PAYLOAD_BYTES)
    dl = BulkDownloader(cache_root=tmp_path, http_client=client)
    result = dl.download("https://example.com/files/sample.csv?v=1")
    client.close()
    assert result.local_path == tmp_path / "sample.csv"


def test_filename_inference_raises_when_url_has_no_tail(tmp_path: Path) -> None:
    client = _mock_client(PAYLOAD_BYTES)
    dl = BulkDownloader(cache_root=tmp_path, http_client=client)
    with pytest.raises(ValueError):
        dl.download("https://example.com/")
    client.close()


def test_cache_hit_skips_redownload(tmp_path: Path) -> None:
    """Segunda chamada com mesmo arquivo + sidecar válido = cache_hit."""
    requests: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=PAYLOAD_BYTES)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    dl = BulkDownloader(cache_root=tmp_path, http_client=client)

    first = dl.download("https://example.com/data.zip", filename="data.zip")
    assert first.cache_hit is False
    assert len(requests) == 1

    second = dl.download("https://example.com/data.zip", filename="data.zip")
    assert second.cache_hit is True
    assert second.sha256 == first.sha256
    # Cache válido: nenhuma nova requisição
    assert len(requests) == 1
    client.close()


def test_invalid_sidecar_triggers_redownload(tmp_path: Path) -> None:
    target = tmp_path / "data.zip"
    target.write_bytes(b"old content")
    target.with_suffix(".zip.sha256").write_text("not-the-real-hash", encoding="utf-8")

    client = _mock_client(PAYLOAD_BYTES)
    dl = BulkDownloader(cache_root=tmp_path, http_client=client)
    result = dl.download("https://example.com/data.zip", filename="data.zip")
    client.close()

    # SHA-256 do sidecar não bate → re-download e sobrescrita.
    assert result.cache_hit is False
    assert target.read_bytes() == PAYLOAD_BYTES


def test_download_creates_nested_directories(tmp_path: Path) -> None:
    client = _mock_client(PAYLOAD_BYTES)
    nested_root = tmp_path / "deep" / "nested"
    dl = BulkDownloader(cache_root=nested_root, http_client=client)
    result = dl.download("https://example.com/x.bin")
    client.close()
    assert result.local_path.exists()
    assert result.local_path.parent == nested_root


def test_download_raises_on_http_error(tmp_path: Path) -> None:
    client = _mock_client(b"", status=404)
    dl = BulkDownloader(cache_root=tmp_path, http_client=client)
    with pytest.raises(httpx.HTTPStatusError):
        dl.download("https://example.com/missing.zip", filename="missing.zip")
    client.close()
