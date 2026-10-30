"""Tests for the round-trip CI gate."""
from __future__ import annotations

from pathlib import Path

import pytest
import rdflib

from indicium_adapters.asb.round_trip import (
    RoundTripResult,
    UnresolvedClaim,
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
    assert result.skills_listed == 2
    assert result.skills_checked == 2
    assert result.skills_skipped == []
    assert result.skills_with_unlisted_claims == 0


def test_round_trip_reports_dangling_claim_in_slug_list_collection() -> None:
    result = run_round_trip_check(SLUG_LIST, _load(GRAPH_BROKEN))
    assert [u.skill_slug for u in result.unresolved] == ["skill-with-claim"]


def test_round_trip_ignores_claims_typed_outside_indicium() -> None:
    """Only indicium's Claim class counts; another class does not resolve."""
    graph = rdflib.Graph()
    graph.parse(
        data=(
            "<https://w3id.org/holobiomicslab/asb-skill/feature-detection-lcms/claim/01> "
            "a <https://example.org/vocab#Claim> ."
        ),
        format="turtle",
    )
    result = run_round_trip_check(FIXTURE, graph)
    assert [u.skill_slug for u in result.unresolved] == ["feature-detection-lcms"]


SKIPPED = Path(__file__).parent / "fixtures" / "skipped_skill_collection"
UNLISTED = Path(__file__).parent / "fixtures" / "unlisted_claims_collection"


def test_round_trip_fails_on_a_listed_skill_it_could_not_read() -> None:
    """A skill dropped by the loader must block the release, not shrink it."""
    with pytest.warns(UserWarning):
        result = run_round_trip_check(SKIPPED, _load(GRAPH_OK))
    assert result.ok is False
    assert result.skills_listed == 2
    assert result.skills_checked == 0
    assert [s.slug for s in result.skills_skipped] == [
        "skill-with-claim-and-empty-span",
        "listed-but-not-promoted",
    ]


def test_round_trip_checks_the_claims_of_a_skipped_skill() -> None:
    """A skill that fails validation still has its claim IRIs checked."""
    with pytest.warns(UserWarning):
        result = run_round_trip_check(SKIPPED, _load(GRAPH_OK))
    assert result.resolved_count == 1
    assert result.unresolved == [
        UnresolvedClaim(
            skill_slug="skill-with-claim-and-empty-span",
            claim_iri="https://w3id.org/holobiomicslab/asb-skill/"
            "skill-with-claim-and-empty-span/claim/02",
        )
    ]


def test_round_trip_raises_on_a_skipped_skill_when_fail_on_missing() -> None:
    with pytest.warns(UserWarning), pytest.raises(
        AssertionError, match="listed-but-not-promoted: SKILL.md not found"
    ):
        run_round_trip_check(SKIPPED, _load(GRAPH_OK), fail_on_missing=True)


def test_round_trip_counts_skills_that_declare_claims_they_do_not_list() -> None:
    """n_claims above 0 with no claim IRI is a pass that checked nothing."""
    result = run_round_trip_check(UNLISTED, _load(GRAPH_OK))
    assert result.ok is True
    assert result.resolved_count == 0
    assert result.skills_with_unlisted_claims == 1
