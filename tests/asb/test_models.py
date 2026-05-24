"""Tests for the Pydantic v2 models mirroring on-disk ASB-Skill state."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from indicium_adapters.asb.models import (
    ASBClaimRecord,
    ASBCollection,
    ASBEvidenceSpan,
    ASBSkillRecord,
    ASBSourcePaper,
    ASBToolRecord,
)


def test_source_paper_requires_doi() -> None:
    with pytest.raises(ValidationError):
        ASBSourcePaper(doi="", title="x")  # type: ignore[arg-type]


def test_source_paper_normalises_doi() -> None:
    p = ASBSourcePaper(doi=" https://doi.org/10.1/abc ", title="x")
    assert p.doi == "10.1/abc"


def test_evidence_span_defaults_to_textual_quotation() -> None:
    e = ASBEvidenceSpan(quote="lcms data was processed with mzmine 4")
    assert e.eco_code == "eco:textual-quotation"


def test_tool_record_canonical_url_optional() -> None:
    t = ASBToolRecord(slug="mzmine", name="MZmine")
    assert t.canonical_url is None
    assert t.bio_tools_id is None


def test_skill_record_round_trip() -> None:
    skill = ASBSkillRecord(
        slug="feature-detection-lcms",
        name="Feature detection (LC-MS)",
        evidence_spans=[ASBEvidenceSpan(quote="quote 1")],
        source_papers=[ASBSourcePaper(doi="10.1/abc", title="Paper")],
    )
    dumped = skill.model_dump(mode="json")
    rebuilt = ASBSkillRecord.model_validate(dumped)
    assert rebuilt == skill


def test_claim_record_minimal() -> None:
    c = ASBClaimRecord(
        claim_id="claim-01",
        subject="MZmine",
        predicate="processes",
        object="LC-MS data",
    )
    assert c.qualifiers == []


def test_collection_links_skills_and_tools() -> None:
    coll = ASBCollection(
        collection_iri="https://w3id.org/holobiomicslab/asb-skill/collection/metabolomics/v1",
        version="v1",
        skills=[ASBSkillRecord(slug="s", name="S")],
        tools=[ASBToolRecord(slug="t", name="T")],
        claims=[],
    )
    assert coll.skills[0].slug == "s"
