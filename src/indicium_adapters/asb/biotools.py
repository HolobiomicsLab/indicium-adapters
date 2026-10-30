"""bio.tools resolver for ASB-Tool canonical URLs.

Looks up ``canonical_url`` against the bio.tools REST API and returns
the ``biotoolsID`` when one matches. Results — including explicit
misses, stored as SQL ``NULL`` — are cached in a local SQLite DB to
avoid hammering bio.tools across adapter runs and to make CI
deterministic.

Set ``offline=True`` (or env ``ASB_ADAPTER_OFFLINE=1``) to disable
network entirely; the resolver then returns ``None`` for every URL not
already in cache. This is the mode CI uses for the round-trip test.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Self

import httpx

_BIOTOOLS_SEARCH = "https://bio.tools/api/tool/"


class BioToolsResolver:
    """Resolve ``canonical_url`` → ``biotoolsID``, with SQLite cache."""

    def __init__(
        self,
        cache_db: Path | str,
        client: httpx.Client | None = None,
        offline: bool | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._db_path = Path(cache_db)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS biotools_cache (
                canonical_url TEXT PRIMARY KEY,
                biotools_id   TEXT
            )
            """
        )
        self._conn.commit()
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)
        if offline is None:
            offline = os.environ.get("ASB_ADAPTER_OFFLINE", "") == "1"
        self._offline = offline

    def resolve(self, canonical_url: str | None) -> str | None:
        """Return a bio.tools id, ``None`` for misses or missing URL."""
        if not canonical_url:
            return None
        cached = self._conn.execute(
            "SELECT biotools_id FROM biotools_cache WHERE canonical_url = ?",
            (canonical_url,),
        ).fetchone()
        if cached is not None:
            return cached[0]
        if self._offline:
            return None
        resolved = self._fetch(canonical_url)
        self._conn.execute(
            "INSERT OR REPLACE INTO biotools_cache(canonical_url, biotools_id) "
            "VALUES (?, ?)",
            (canonical_url, resolved),
        )
        self._conn.commit()
        return resolved

    def _fetch(self, canonical_url: str) -> str | None:
        try:
            response = self._client.get(
                _BIOTOOLS_SEARCH,
                params={"homepage": canonical_url, "format": "json"},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        payload = response.json()
        hits = payload.get("list") or []
        if not hits:
            return None
        return hits[0].get("biotoolsID")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


__all__ = ["BioToolsResolver"]
