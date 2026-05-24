"""Tests for the pure mapper functions."""
from __future__ import annotations

import rdflib
from rdflib.namespace import RDF

from indicium_adapters.asb.mapper import (
    ASB,
    ASBTOOL,
    BIOTOOLS,
    CITO,
    ECO,
    INDICIUM,
    SEPIO,
    claim_to_triples,
    evidence_span_iri,
    paper_to_information_source_triples,
    skill_claim_sepio_assertion_triples,
    skill_to_evidence_triples,
    tool_to_software_entity_triples,
)
from indicium_adapters.asb.models import (
    ASBClaimRecord,
    ASBEvidenceSpan,
    ASBSkillRecord,
    ASBSourcePaper,
    ASBToolRecord,
)


def _has(triples: list, s, p, o) -> bool:
    return (s, p, o) in [(t[0], t[1], t[2]) for t in triples]


def test_skill_evidence_emits_evidence_class_and_eco() -> None:
    skill = ASBSkillRecord(
        slug="feature-detection-lcms",
        name="x",
        evidence_spans=[ASBEvidenceSpan(quote="q", source_doi="10.1/abc")],
    )
    triples = skill_to_evidence_triples(skill)
    evidence_iri = evidence_span_iri(skill.slug, 0)
    assert _has(triples, evidence_iri, RDF.type, INDICIUM.Evidence)
    assert _has(triples, evidence_iri, INDICIUM.ecoCode, ECO["textual-quotation"])
    assert _has(triples, evidence_iri, INDICIUM.exactQuote, rdflib.Literal("q"))


def test_tool_emits_software_entity_with_edam_and_biotools() -> None:
    tool = ASBToolRecord(
        slug="mzmine",
        name="MZmine",
        canonical_url="https://github.com/mzmine/mzmine",
        bio_tools_id="mzmine",
        edam_operation="operation_3215",
        edam_topics=["topic_3172"],
    )
    triples = tool_to_software_entity_triples(tool)
    iri = ASBTOOL["mzmine"]
    assert _has(triples, iri, RDF.type, INDICIUM.SoftwareEntity)
    assert _has(triples, iri, INDICIUM.canonicalUrl, rdflib.Literal(tool.canonical_url))
    assert _has(triples, iri, INDICIUM.bioToolsId, BIOTOOLS["mzmine"])
    assert any(t[1] == INDICIUM.edamOperation for t in triples)
    assert any(t[1] == INDICIUM.edamTopic for t in triples)


def test_tool_emits_null_biotools_when_unresolved() -> None:
    tool = ASBToolRecord(slug="x", name="X", bio_tools_id=None)
    triples = tool_to_software_entity_triples(tool)
    # Explicit-null sentinel: emit a single triple with rdf:nil object.
    iri = ASBTOOL["x"]
    assert _has(triples, iri, INDICIUM.bioToolsId, RDF.nil)


def test_claim_to_triples_emits_class_and_super_pattern() -> None:
    claim = ASBClaimRecord(
        claim_id="https://example.org/claim/01",
        subject="s",
        predicate="p",
        object="o",
        super_pattern="method-detects-entity",
    )
    triples = claim_to_triples(claim)
    iri = rdflib.URIRef(claim.claim_id)
    assert _has(triples, iri, RDF.type, INDICIUM.Claim)
    assert _has(
        triples,
        iri,
        INDICIUM.superPattern,
        rdflib.Literal("method-detects-entity"),
    )


def test_skill_claim_sepio_assertion() -> None:
    skill = ASBSkillRecord(
        slug="feature-detection-lcms",
        name="x",
        claim_ids=["https://example.org/claim/01"],
    )
    triples = skill_claim_sepio_assertion_triples(skill)
    skill_iri = ASB["feature-detection-lcms"]
    claim_iri = rdflib.URIRef("https://example.org/claim/01")
    # An assertion node links skill → SEPIO assertion → claim
    assertion_subjects = {t[0] for t in triples if t[1] == RDF.type and t[2] == SEPIO.Assertion}
    assert len(assertion_subjects) == 1
    a = next(iter(assertion_subjects))
    assert _has(triples, a, SEPIO.hasSubject, skill_iri)
    assert _has(triples, a, SEPIO.hasObject, claim_iri)


def test_paper_to_information_source_triples() -> None:
    paper = ASBSourcePaper(doi="10.1/abc", title="t")
    triples = paper_to_information_source_triples(paper)
    iri = rdflib.URIRef("https://doi.org/10.1/abc")
    assert _has(triples, iri, RDF.type, INDICIUM.InformationSource)
    assert _has(triples, iri, CITO.hasIdentifier, rdflib.Literal("10.1/abc"))
    assert _has(triples, iri, INDICIUM.title, rdflib.Literal("t"))
