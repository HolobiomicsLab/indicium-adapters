"""Tests for the disk loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from indicium_adapters.asb.loader import _extract_frontmatter, load_collection
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


SLUG_LIST = Path(__file__).parent / "fixtures" / "slug_list_collection"


def test_load_slug_list_collection_reads_leaf_skills() -> None:
    """Current releases list skills by slug and keep leaf SKILL.md under leaves/."""
    coll = load_collection(SLUG_LIST)
    assert [s.slug for s in coll.skills] == [
        "skill-with-claim",
        "skill-with-provenance-papers",
    ]
    assert coll.skills[0].claim_ids == [
        "https://w3id.org/holobiomicslab/asb-skill/skill-with-claim/claim/01"
    ]
    assert coll.skills[1].claim_ids == []


def test_load_slug_list_collection_takes_iri_key() -> None:
    coll = load_collection(SLUG_LIST)
    assert coll.collection_iri == (
        "https://w3id.org/holobiomicslab/asb-skill/collection/example/v2"
    )
    assert coll.version == "2"


def test_load_slug_list_collection_reads_string_evidence_and_papers() -> None:
    """Spans are plain strings; papers sit in derived_from or provenance."""
    with_claim, with_provenance = load_collection(SLUG_LIST).skills
    assert [e.quote for e in with_claim.evidence_spans] == [
        "Convert the raw files to an open format --- then align the runs.",
        "A second verbatim span.",
    ]
    assert [(p.doi, p.title) for p in with_claim.source_papers] == [
        ("10.1000/example.1", "An example method paper"),
        ("10.1000/example.2", ""),
    ]
    assert [p.doi for p in with_provenance.source_papers] == ["10.1000/example.3"]
    assert with_claim.edam_operation == "http://edamontology.org/operation_0004"


def test_load_slug_list_collection_reads_tools_by_slug() -> None:
    """A tool slug that contains the word "path" is still a slug."""
    coll = load_collection(SLUG_LIST)
    assert sorted(t.slug for t in coll.tools) == ["pathway-tool", "plain-tool"]
    plain = next(t for t in coll.tools if t.slug == "plain-tool")
    assert plain.evidence_spans[0].quote == "The runs were processed with Plain Tool."
    assert plain.source_papers[0].doi == "10.1000/example.1"


def test_frontmatter_ends_at_the_fence_line_only(tmp_path: Path) -> None:
    """A value containing --- must not cut the frontmatter short."""
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: x\nnote: 'a --- b'\n---\nbody\n---\n", encoding="utf-8")
    assert _extract_frontmatter(md) == {"name": "x", "note": "a --- b"}


SKIPPED = Path(__file__).parent / "fixtures" / "skipped_skill_collection"
UNLISTED = Path(__file__).parent / "fixtures" / "unlisted_claims_collection"


def test_load_collection_records_each_skipped_skill_with_its_reason() -> None:
    """A listed skill the loader cannot read is kept with the reason, not dropped."""
    with pytest.warns(UserWarning) as warned:
        coll = load_collection(SKIPPED)
    assert [str(w.message) for w in warned] == [
        (
            "loader: skipping skill skill-with-claim-and-empty-span: "
            "evidence_spans.0.quote: String should have at least 1 character"
        ),
        "loader: skipping skill listed-but-not-promoted: SKILL.md not found",
    ]
    assert coll.skills == []
    assert [(s.slug, s.reason) for s in coll.skipped_skills] == [
        (
            "skill-with-claim-and-empty-span",
            "evidence_spans.0.quote: String should have at least 1 character",
        ),
        ("listed-but-not-promoted", "SKILL.md not found"),
    ]


def test_skipped_skill_keeps_the_claim_iris_its_frontmatter_lists() -> None:
    with pytest.warns(UserWarning):
        invalid, missing = load_collection(SKIPPED).skipped_skills
    assert invalid.claim_ids == [
        "https://w3id.org/holobiomicslab/asb-skill/skill-with-claim/claim/01",
        "https://w3id.org/holobiomicslab/asb-skill/skill-with-claim-and-empty-span/claim/02",
    ]
    assert missing.claim_ids == []


def test_load_collection_reads_the_declared_claim_count() -> None:
    (skill,) = load_collection(UNLISTED).skills
    assert skill.n_claims == 3
    assert skill.claim_ids == []
