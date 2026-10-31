"""Tests for the pure mapper functions."""
from __future__ import annotations

from importlib.resources import files

import indicium
import rdflib
import yaml
from indicium.generated.model import EcoCodeAsbSubset
from rdflib.namespace import DCTERMS, RDF

from indicium_adapters.asb.mapper import (
    ASB,
    ASB_VOCAB,
    ASBTOOL,
    CITO,
    ECO,
    ECO_CODE_ASB_SUBSET,
    EVIDENCE_CLASS,
    INDICIUM,
    SEPIO,
    SOFTWARE_CLASS,
    SOURCE_CLASS,
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
from indicium_adapters.asb.round_trip import (
    count_shape_targeted_nodes,
    shape_targeted_classes,
)


def _has(triples: list, s, p, o) -> bool:
    return (s, p, o) in [(t[0], t[1], t[2]) for t in triples]


def test_skill_evidence_emits_evidence_class_and_eco() -> None:
    skill = ASBSkillRecord(
        slug="feature-detection-lcms",
        name="x",
        evidence_spans=[
            ASBEvidenceSpan(quote="q", source_doi="10.1/abc", paragraph_id="p-3")
        ],
    )
    triples = skill_to_evidence_triples(skill)
    evidence_iri = evidence_span_iri(skill.slug, 0)
    assert _has(triples, evidence_iri, RDF.type, SEPIO["0000002"])
    assert _has(triples, evidence_iri, INDICIUM.eco_code, ECO["0000033"])
    assert _has(triples, evidence_iri, INDICIUM.quote_exact, rdflib.Literal("q"))
    assert _has(triples, evidence_iri, INDICIUM.source_doi, rdflib.Literal("10.1/abc"))
    assert _has(triples, evidence_iri, INDICIUM.paragraph_id, rdflib.Literal("p-3"))


def test_eco_codes_are_the_ecocodeasbsubset_meanings_of_the_indicium_schema() -> None:
    """Each eco_code value maps to the ECO term indicium's schema gives it."""
    schema = yaml.safe_load(
        files("indicium").joinpath("schema/indicium.yaml").read_text(encoding="utf-8")
    )
    values = schema["enums"]["EcoCodeAsbSubset"]["permissible_values"]
    assert set(ECO_CODE_ASB_SUBSET) == {code.value for code in EcoCodeAsbSubset}
    for code, iri in ECO_CODE_ASB_SUBSET.items():
        assert str(iri) == indicium.expand_curie(values[code]["meaning"]), code


def test_eco_code_given_as_an_eco_curie_maps_to_its_iri() -> None:
    skill = ASBSkillRecord(
        slug="s", name="x", evidence_spans=[ASBEvidenceSpan(quote="q", eco_code="ECO:0000251")]
    )
    triples = skill_to_evidence_triples(skill)
    assert _has(triples, evidence_span_iri("s", 0), INDICIUM.eco_code, ECO["0000251"])


def test_unknown_eco_code_is_kept_as_a_literal_the_indicium_shape_reports() -> None:
    """No ECO IRI is made up from a value outside indicium's subset."""
    skill = ASBSkillRecord(
        slug="s",
        name="x",
        evidence_spans=[ASBEvidenceSpan(quote="q", eco_code="eco:textual-quotation")],
    )
    graph = rdflib.Graph()
    for t in skill_to_evidence_triples(skill):
        graph.add(t)
    eco = graph.value(evidence_span_iri("s", 0), INDICIUM.eco_code)
    assert eco == rdflib.Literal("eco:textual-quotation")
    conforms, report = indicium.validate_graph(graph)
    assert not conforms
    assert "Result Path: indicium:eco_code\n" in report


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
    assert _has(triples, iri, RDF.type, rdflib.URIRef("http://purl.org/spar/fabio/ComputerProgram"))
    assert _has(triples, iri, DCTERMS.identifier, rdflib.Literal(str(iri)))
    assert _has(triples, iri, INDICIUM.canonical_url, rdflib.URIRef(tool.canonical_url))
    assert _has(triples, iri, INDICIUM.bio_tools_id, rdflib.Literal("mzmine"))
    assert _has(
        triples,
        iri,
        INDICIUM.edam_operation,
        rdflib.URIRef("http://edamontology.org/operation_3215"),
    )
    assert _has(
        triples, iri, INDICIUM.edam_topics, rdflib.URIRef("http://edamontology.org/topic_3172")
    )


def test_tool_without_biotools_id_emits_no_biotools_triple() -> None:
    """The indicium shape wants a string; no rdf:nil sentinel is written."""
    tool = ASBToolRecord(slug="x", name="X", bio_tools_id=None)
    triples = tool_to_software_entity_triples(tool)
    assert not any(t[1] == INDICIUM.bio_tools_id for t in triples)
    assert not any(t[2] == RDF.nil for t in triples)


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
    assert _has(triples, iri, RDF.type, rdflib.URIRef("http://purl.org/spar/fabio/Expression"))
    assert _has(triples, iri, DCTERMS.identifier, rdflib.Literal("10.1/abc"))
    assert _has(triples, iri, DCTERMS.title, rdflib.Literal("t"))
    assert not any(t[1] == CITO.hasIdentifier for t in triples)


def test_mapped_classes_are_classes_the_indicium_shapes_target() -> None:
    """A class no shape targets would let validation pass without checking it."""
    for cls in (EVIDENCE_CLASS, SOFTWARE_CLASS, SOURCE_CLASS, ASB_VOCAB.Claim):
        assert cls in shape_targeted_classes(), cls


def test_mapped_evidence_tool_and_paper_conform_to_the_indicium_shapes() -> None:
    skill = ASBSkillRecord(
        slug="s",
        name="x",
        evidence_spans=[ASBEvidenceSpan(quote="q", source_doi="10.1/abc", paragraph_id="p-1")],
    )
    tool = ASBToolRecord(
        slug="mzmine",
        name="MZmine",
        canonical_url="https://github.com/mzmine/mzmine",
        bio_tools_id="mzmine",
        edam_operation="operation_3215",
        edam_topics=["topic_3172"],
    )
    paper = ASBSourcePaper(doi="10.1/abc", title="t")
    graph = rdflib.Graph()
    for t in (
        skill_to_evidence_triples(skill)
        + tool_to_software_entity_triples(tool)
        + paper_to_information_source_triples(paper)
    ):
        graph.add(t)
    assert count_shape_targeted_nodes(graph) == 3
    conforms, report = indicium.validate_graph(graph)
    assert conforms, report


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


def test_claim_context_fills_the_asb_context_the_shape_requires() -> None:
    claim = ASBClaimRecord(
        claim_id="https://example.org/claim/01",
        subject="s",
        predicate="p",
        object="o",
        qualifiers=["increases"],
        context="in human plasma",
    )
    graph = rdflib.Graph()
    for t in claim_to_triples(claim):
        graph.add(t)
    iri = rdflib.URIRef(claim.claim_id)
    assert (iri, ASB_VOCAB.context, rdflib.Literal("in human plasma")) in graph
    conforms, report = indicium.validate_graph(graph)
    assert conforms, report


def test_claim_without_context_is_reported_by_the_indicium_shapes() -> None:
    """No context is invented: the shape reports the missing asb:context."""
    claim = ASBClaimRecord(
        claim_id="https://example.org/claim/01", subject="s", predicate="p", object="o"
    )
    graph = rdflib.Graph()
    for t in claim_to_triples(claim):
        graph.add(t)
    conforms, report = indicium.validate_graph(graph)
    assert not conforms
    assert "Result Path: asb:context\n" in report


def test_paper_without_title_emits_no_empty_title() -> None:
    paper = ASBSourcePaper(doi="10.1/abc", title="")
    triples = paper_to_information_source_triples(paper)
    assert not any(t[1] == DCTERMS.title for t in triples)
