"""Tests for the round-trip CI gate."""
from __future__ import annotations

from pathlib import Path

import pytest
import rdflib

from indicium_adapters.asb.round_trip import (
    RoundTripResult,
    run_round_trip_check,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_collection"
GRAPH_OK = Path(__file__).parent / "fixtures" / "indicium_graph.ttl"
GRAPH_BROKEN = Path(__file__).parent / "fixtures" / "indicium_graph_broken.ttl"


def _load(path: Path) -> rdflib.Graph:
    g = rdflib.Graph()
    g.parse(path, format="turtle")
    return g


def test_round_trip_succeeds_when_all_claims_resolve() -> None:
    result = run_round_trip_check(FIXTURE, _load(GRAPH_OK))
    assert isinstance(result, RoundTripResult)
    assert result.ok is True
    assert result.unresolved == []


def test_round_trip_lists_unresolved_when_claim_missing() -> None:
    result = run_round_trip_check(FIXTURE, _load(GRAPH_BROKEN))
    assert result.ok is False
    assert len(result.unresolved) == 1
    assert result.unresolved[0].claim_iri.endswith("/claim/01")
    assert result.unresolved[0].skill_slug == "feature-detection-lcms"


def test_round_trip_raises_when_fail_on_missing(tmp_path: Path) -> None:
    with pytest.raises(AssertionError) as excinfo:
        run_round_trip_check(
            FIXTURE, _load(GRAPH_BROKEN), fail_on_missing=True
        )
    assert "claim/01" in str(excinfo.value)


SLUG_LIST = Path(__file__).parent / "fixtures" / "slug_list_collection"


def test_round_trip_reads_slug_list_collection() -> None:
    """The gate runs on the current layout and says how many skills it read."""
    result = run_round_trip_check(SLUG_LIST, _load(GRAPH_OK))
    assert result.ok is True
    assert result.resolved_count == 1
    assert result.skills_checked == 2


def test_round_trip_reports_dangling_claim_in_slug_list_collection() -> None:
    result = run_round_trip_check(SLUG_LIST, _load(GRAPH_BROKEN))
    assert [u.skill_slug for u in result.unresolved] == ["skill-with-claim"]
