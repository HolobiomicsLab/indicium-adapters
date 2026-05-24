"""Tests for the bio.tools resolver and SQLite cache."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from indicium_adapters.asb.biotools import BioToolsResolver


class _StubTransport(httpx.MockTransport):
    """An httpx MockTransport that counts requests."""

    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            self.calls += 1
            return httpx.Response(status, json=payload)

        super().__init__(handler)


def test_resolver_returns_id_for_known_canonical_url(tmp_path: Path) -> None:
    transport = _StubTransport(
        payload={"list": [{"biotoolsID": "mzmine"}]},
    )
    resolver = BioToolsResolver(
        cache_db=tmp_path / "cache.sqlite",
        client=httpx.Client(transport=transport),
    )
    assert resolver.resolve("https://github.com/mzmine/mzmine") == "mzmine"


def test_resolver_caches_hits(tmp_path: Path) -> None:
    transport = _StubTransport(payload={"list": [{"biotoolsID": "mzmine"}]})
    resolver = BioToolsResolver(
        cache_db=tmp_path / "cache.sqlite",
        client=httpx.Client(transport=transport),
    )
    resolver.resolve("https://github.com/mzmine/mzmine")
    resolver.resolve("https://github.com/mzmine/mzmine")
    assert transport.calls == 1


def test_resolver_caches_misses_as_null(tmp_path: Path) -> None:
    transport = _StubTransport(payload={"list": []})
    resolver = BioToolsResolver(
        cache_db=tmp_path / "cache.sqlite",
        client=httpx.Client(transport=transport),
    )
    assert resolver.resolve("https://example.org/unknown") is None
    assert resolver.resolve("https://example.org/unknown") is None
    assert transport.calls == 1


def test_resolver_returns_none_when_url_is_none(tmp_path: Path) -> None:
    resolver = BioToolsResolver(cache_db=tmp_path / "cache.sqlite")
    assert resolver.resolve(None) is None


def test_resolver_offline_mode_skips_http(tmp_path: Path) -> None:
    # Offline mode: never hits the network. Used by CI without bio.tools.
    resolver = BioToolsResolver(
        cache_db=tmp_path / "cache.sqlite",
        offline=True,
    )
    assert resolver.resolve("https://github.com/mzmine/mzmine") is None
