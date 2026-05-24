"""Tests for the disk loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from indicium_adapters.asb.loader import load_collection
from indicium_adapters.asb.models import ASBCollection

FIXTURE = Path(__file__).parent / "fixtures" / "sample_collection"


def test_load_collection_returns_validated_collection() -> None:
    coll = load_collection(FIXTURE)
    assert isinstance(coll, ASBCollection)
    assert coll.version == "v1"
    assert len(coll.skills) == 1
    assert coll.skills[0].slug == "feature-detection-lcms"
    assert len(coll.skills[0].evidence_spans) == 1
    assert coll.skills[0].claim_ids == [
        "https://w3id.org/holobiomicslab/asb-skill/feature-detection-lcms/claim/01"
    ]


def test_load_collection_parses_tool_ledger() -> None:
    coll = load_collection(FIXTURE)
    assert len(coll.tools) == 1
    assert coll.tools[0].slug == "mzmine"
    assert coll.tools[0].canonical_url == "https://github.com/mzmine/mzmine"


def test_load_collection_parses_claims() -> None:
    coll = load_collection(FIXTURE)
    assert len(coll.claims) == 1
    assert coll.claims[0].claim_id.endswith("/claim/01")
    assert coll.claims[0].super_pattern == "method-detects-entity"


def test_load_collection_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_collection(tmp_path / "does-not-exist")
