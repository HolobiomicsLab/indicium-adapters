"""Pure mapping ``ASB* model`` → list of RDF triples.

All functions in this module are pure: no I/O, no network, no clock
reads. Provenance (PROV envelopes) is attached one layer up in
``adapter.py``.

Vocabulary bases are read from ``indicium``, never restated, so they
follow the standard when it moves a namespace. Every record the indicium
model describes is typed with the class its SHACL shapes target and
carries the slots they declare. A claim is an ``asb:Claim`` with
``asb:subject``, ``asb:relation``, ``asb:object``, ``asb:context`` and its
qualifiers. An evidence span is an Evidence (``sepio:0000002``) with
``indicium:eco_code``, ``indicium:quote_exact``, ``indicium:source_doi``
and ``indicium:paragraph_id``. A tool is a SoftwareEntity
(``fabio:ComputerProgram``) whose ``dct:identifier`` is its IRI, and a
paper a Source (``fabio:Expression``) whose ``dct:identifier`` is its DOI.
Skills, which the indicium model does not describe, a claim's
``super_pattern``, names and the skill-to-evidence link are written under
indicium's ``INDICIUM_BASE`` with this mapper's own local names
(``Skill``, ``name``, ``hasEvidence``, ``superPattern``), which the
indicium schema does not declare.

Known departures from the indicium model, which no shape checks:
``indicium:source_doi`` and ``indicium:paragraph_id`` are written on
Evidence although indicium declares them on other classes (paragraph_id
on Source, source_doi on Figure, Script and DataAsset), and the
Evidence shape is
open; ``indicium:of_source``, indicium's Evidence-to-Source link, is
not written; and the skill-to-claim assertion nodes use ``SEPIO_Assertion``,
``SEPIO_hasSubject`` and ``SEPIO_hasObject``, which are not SEPIO terms.

Skill and tool instance IRIs follow the form ASB's release code mints,
since indicium exports no base for them.
"""
from __future__ import annotations

import uuid
from urllib.parse import urlsplit

import rdflib
from indicium import ASB_BASE, INDICIUM_BASE, SuperPatternQualifier
from rdflib.namespace import DCTERMS, RDF, Namespace

ASB_VOCAB = Namespace(ASB_BASE)
INDICIUM = Namespace(INDICIUM_BASE)
ECO = Namespace("http://purl.obolibrary.org/obo/ECO_")
CITO = Namespace("http://purl.org/spar/cito/")
SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
FABIO = Namespace("http://purl.org/spar/fabio/")
ASB_SKILL_BASE = "https://w3id.org/holobiomicslab/asb-skill/"
ASB_TOOL_BASE = "https://w3id.org/holobiomicslab/asb-tool/"
ASB = Namespace(ASB_SKILL_BASE)
ASBTOOL = Namespace(ASB_TOOL_BASE)
BIOTOOLS = Namespace("https://bio.tools/")
EDAM_OP = Namespace("http://edamontology.org/operation_")
EDAM_TOPIC = Namespace("http://edamontology.org/topic_")

# The class IRIs the indicium model gives Evidence, SoftwareEntity and Source.
EVIDENCE_CLASS = SEPIO["0000002"]
SOFTWARE_CLASS = FABIO.ComputerProgram
SOURCE_CLASS = FABIO.Expression

# indicium's EcoCodeAsbSubset: each value and the ECO term the indicium
# schema gives it as ``meaning``.
ECO_CODE_ASB_SUBSET: dict[str, rdflib.URIRef] = {
    "textual_quotation": ECO["0000033"],
    "computational_evidence": ECO["0000251"],
    "expert_curation": ECO["0000305"],
    "inference_from_background_knowledge": ECO["0000302"],
    "author_statement": ECO["0000204"],
    "experimental_evidence": ECO["0000006"],
    "combinatorial_evidence": ECO["0000213"],
    "traceable_author_statement": ECO["0000033"],
}

# The closed Bucur terms; any other qualifier is a domain qualifier.
_BUCUR_QUALIFIERS = frozenset(q.value for q in SuperPatternQualifier)


Triple = tuple[rdflib.term.Node, rdflib.term.Node, rdflib.term.Node]


def evidence_span_iri(parent_slug: str, index: int) -> rdflib.URIRef:
    """Stable IRI for an evidence span — ``<parent>/evidence/<index>``."""
    return rdflib.URIRef(f"{ASB[parent_slug]}/evidence/{index}")


def _edam_op_iri(local: str) -> rdflib.URIRef:
    return rdflib.URIRef(f"http://edamontology.org/{local}")


def _edam_topic_iri(local: str) -> rdflib.URIRef:
    return rdflib.URIRef(f"http://edamontology.org/{local}")


def _eco_term(code: str) -> rdflib.term.Node:
    """Return the ECO IRI of an ``eco_code``.

    A value of indicium's EcoCodeAsbSubset maps to the ECO term the
    standard gives it, and an ``ECO:`` CURIE to its IRI. Any other value
    stays a literal, which the indicium shape on ``eco_code`` reports,
    instead of becoming an ECO IRI that does not exist.
    """
    if code in ECO_CODE_ASB_SUBSET:
        return ECO_CODE_ASB_SUBSET[code]
    prefix, _, local = code.partition(":")
    if prefix == "ECO" and local.isdigit():
        return ECO[local]
    return rdflib.Literal(code)


def skill_to_evidence_triples(skill) -> list[Triple]:
    """Emit one indicium Evidence (``sepio:0000002``) per evidence span."""
    triples: list[Triple] = []
    for i, span in enumerate(skill.evidence_spans):
        iri = evidence_span_iri(skill.slug, i)
        triples.append((iri, RDF.type, EVIDENCE_CLASS))
        triples.append((iri, INDICIUM.eco_code, _eco_term(span.eco_code)))
        triples.append((iri, INDICIUM.quote_exact, rdflib.Literal(span.quote)))
        if span.source_doi:
            triples.append(
                (iri, INDICIUM.source_doi, rdflib.Literal(span.source_doi))
            )
        if span.paragraph_id:
            triples.append(
                (iri, INDICIUM.paragraph_id, rdflib.Literal(span.paragraph_id))
            )
        # Link skill → evidence
        triples.append((ASB[skill.slug], INDICIUM.hasEvidence, iri))
    return triples


def _url_term(url: str) -> rdflib.term.Identifier:
    """Return ``url`` as an IRI when it is an absolute one, else as a literal.

    A relative or whitespace-bearing value would pass the shape's
    ``sh:nodeKind sh:IRI`` as a URIRef yet break the Turtle serialisation;
    as a literal the shape reports it.
    """
    parts = urlsplit(url)
    if parts.scheme and parts.netloc and not any(c.isspace() for c in url):
        return rdflib.URIRef(url)
    return rdflib.Literal(url)


def tool_to_software_entity_triples(tool) -> list[Triple]:
    """Emit one indicium SoftwareEntity (``fabio:ComputerProgram``) per tool.

    ``dct:identifier``, which the indicium shape requires, carries the tool
    IRI. ``indicium:bio_tools_id`` is written only when a bio.tools id is
    known: the shape takes a string, so no ``rdf:nil`` stands in for it.
    """
    triples: list[Triple] = []
    iri = ASBTOOL[tool.slug]
    triples.append((iri, RDF.type, SOFTWARE_CLASS))
    triples.append((iri, DCTERMS.identifier, rdflib.Literal(str(iri))))
    triples.append((iri, INDICIUM.name, rdflib.Literal(tool.name)))
    if tool.canonical_url:
        triples.append((iri, INDICIUM.canonical_url, _url_term(tool.canonical_url)))
    if tool.bio_tools_id:
        triples.append(
            (iri, INDICIUM.bio_tools_id, rdflib.Literal(tool.bio_tools_id))
        )
    if tool.edam_operation:
        triples.append(
            (iri, INDICIUM.edam_operation, _edam_op_iri(tool.edam_operation))
        )
    for topic in tool.edam_topics:
        triples.append((iri, INDICIUM.edam_topics, _edam_topic_iri(topic)))
    return triples


def _qualifier_term(qualifier: str) -> rdflib.URIRef:
    """Route a qualifier the way the DomainAdapter contract states.

    A closed Bucur SuperPattern term rides ``asb:qualifier``; any other
    term rides the open ``asb:domainQualifier``.
    """
    if qualifier in _BUCUR_QUALIFIERS:
        return ASB_VOCAB.qualifier
    return ASB_VOCAB.domainQualifier


def claim_to_triples(claim) -> list[Triple]:
    """Emit an indicium ``asb:Claim`` with its subject, relation and object.

    The record's ``predicate`` fills ``asb:relation``, the slot the
    indicium shape declares for it. Its ``context``, when present, fills
    ``asb:context``; none is invented when the record has none.
    """
    triples: list[Triple] = []
    iri = rdflib.URIRef(claim.claim_id)
    triples.append((iri, RDF.type, ASB_VOCAB.Claim))
    if claim.context:
        triples.append((iri, ASB_VOCAB.context, rdflib.Literal(claim.context)))
    triples.append((iri, ASB_VOCAB.subject, rdflib.Literal(claim.subject)))
    triples.append((iri, ASB_VOCAB.relation, rdflib.Literal(claim.predicate)))
    triples.append((iri, ASB_VOCAB.object, rdflib.Literal(claim.object)))
    for q in claim.qualifiers:
        triples.append((iri, _qualifier_term(q), rdflib.Literal(q)))
    if claim.super_pattern:
        triples.append(
            (iri, INDICIUM.superPattern, rdflib.Literal(claim.super_pattern))
        )
    return triples


def skill_claim_sepio_assertion_triples(skill) -> list[Triple]:
    """Emit one SEPIO assertion node per skill→claim link."""
    triples: list[Triple] = []
    for claim_iri_str in skill.claim_ids:
        assertion_iri = rdflib.URIRef(f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'{skill.slug}|{claim_iri_str}')}")
        triples.append((assertion_iri, RDF.type, SEPIO.Assertion))
        triples.append((assertion_iri, SEPIO.hasSubject, ASB[skill.slug]))
        triples.append((assertion_iri, SEPIO.hasObject, rdflib.URIRef(claim_iri_str)))
    return triples


def paper_to_information_source_triples(paper) -> list[Triple]:
    """Emit an indicium Source (``fabio:Expression``) from a DOI.

    ``dct:identifier`` carries the DOI and ``dct:title`` the title, the
    terms the indicium shape declares for ``doi`` and ``title``.
    """
    triples: list[Triple] = []
    iri = rdflib.URIRef(f"https://doi.org/{paper.doi}")
    triples.append((iri, RDF.type, SOURCE_CLASS))
    triples.append((iri, DCTERMS.identifier, rdflib.Literal(paper.doi)))
    if paper.title:
        triples.append((iri, DCTERMS.title, rdflib.Literal(paper.title)))
    return triples


__all__ = [
    "ASB",
    "ASBTOOL",
    "ASB_SKILL_BASE",
    "ASB_TOOL_BASE",
    "ASB_VOCAB",
    "BIOTOOLS",
    "CITO",
    "ECO",
    "ECO_CODE_ASB_SUBSET",
    "EDAM_OP",
    "EDAM_TOPIC",
    "EVIDENCE_CLASS",
    "FABIO",
    "INDICIUM",
    "SEPIO",
    "SOFTWARE_CLASS",
    "SOURCE_CLASS",
    "Triple",
    "claim_to_triples",
    "evidence_span_iri",
    "paper_to_information_source_triples",
    "skill_claim_sepio_assertion_triples",
    "skill_to_evidence_triples",
    "tool_to_software_entity_triples",
]
