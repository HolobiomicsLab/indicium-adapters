"""Tests for the pure mapper functions."""
from __future__ import annotations

import indicium
import rdflib
from rdflib.namespace import RDF

from indicium_adapters.asb.mapper import (
    ASB,
    ASB_VOCAB,
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
    assert _has(triples, iri, RDF.type, rdflib.URIRef(indicium.asb_term("Claim")))
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


def test_vocabulary_bases_come_from_indicium() -> None:
    """A copied base string would drift when indicium moves its namespace."""
    assert str(ASB_VOCAB) == indicium.ASB_BASE
    assert str(INDICIUM) == indicium.INDICIUM_BASE


def test_claim_slots_use_the_asb_claim_shape_terms() -> None:
    claim = ASBClaimRecord(
        claim_id="https://example.org/claim/01", subject="s", predicate="p", object="o"
    )
    triples = claim_to_triples(claim)
    iri = rdflib.URIRef(claim.claim_id)
    assert _has(triples, iri, ASB_VOCAB.subject, rdflib.Literal("s"))
    assert _has(triples, iri, ASB_VOCAB.relation, rdflib.Literal("p"))
    assert _has(triples, iri, ASB_VOCAB.object, rdflib.Literal("o"))


def test_claim_qualifiers_route_like_the_domain_adapter_contract() -> None:
    """A closed Bucur term rides asb:qualifier, any other asb:domainQualifier."""
    claim = ASBClaimRecord(
        claim_id="https://example.org/claim/01",
        subject="s",
        predicate="p",
        object="o",
        qualifiers=["increases", "measured_in"],
    )
    triples = claim_to_triples(claim)
    iri = rdflib.URIRef(claim.claim_id)
    assert _has(triples, iri, ASB_VOCAB.qualifier, rdflib.Literal("increases"))
    assert _has(triples, iri, ASB_VOCAB.domainQualifier, rdflib.Literal("measured_in"))


def test_mapped_claim_is_evaluated_by_the_indicium_shapes() -> None:
    """Typed asb:Claim, the claim is a focus node; its mapped slots conform."""
    claim = ASBClaimRecord(
        claim_id="https://example.org/claim/01",
        subject="s",
        predicate="p",
        object="o",
        qualifiers=["increases"],
    )
    graph = rdflib.Graph()
    for t in claim_to_triples(claim):
        graph.add(t)
    _, report = indicium.validate_graph(graph)
    assert f"Focus Node: <{claim.claim_id}>" in report
    for slot in ("subject", "relation", "object", "qualifier"):
        assert f"Result Path: asb:{slot}\n" not in report


def test_paper_without_title_emits_no_empty_title() -> None:
    paper = ASBSourcePaper(doi="10.1/abc", title="")
    triples = paper_to_information_source_triples(paper)
    assert not any(t[1] == INDICIUM.title for t in triples)
