"""Pure mapping ``ASB* model`` → list of RDF triples.

All functions in this module are pure: no I/O, no network, no clock
reads. Provenance (PROV envelopes) is attached one layer up in
``adapter.py``.
"""
from __future__ import annotations

import uuid

import rdflib
from rdflib.namespace import RDF, Namespace

INDICIUM = Namespace("https://w3id.org/holobiomicslab/indicium#")
ECO = Namespace("http://purl.obolibrary.org/obo/ECO_")
CITO = Namespace("http://purl.org/spar/cito/")
SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
ASB = Namespace("https://w3id.org/holobiomicslab/asb-skill/")
ASBTOOL = Namespace("https://w3id.org/holobiomicslab/asb-tool/")
BIOTOOLS = Namespace("https://bio.tools/")
EDAM_OP = Namespace("http://edamontology.org/operation_")
EDAM_TOPIC = Namespace("http://edamontology.org/topic_")


Triple = tuple[rdflib.term.Node, rdflib.term.Node, rdflib.term.Node]


def evidence_span_iri(parent_slug: str, index: int) -> rdflib.URIRef:
    """Stable IRI for an evidence span — ``<parent>/evidence/<index>``."""
    return rdflib.URIRef(f"{ASB[parent_slug]}/evidence/{index}")


def _edam_op_iri(local: str) -> rdflib.URIRef:
    return rdflib.URIRef(f"http://edamontology.org/{local}")


def _edam_topic_iri(local: str) -> rdflib.URIRef:
    return rdflib.URIRef(f"http://edamontology.org/{local}")


def _eco_iri(local: str) -> rdflib.URIRef:
    # incoming form: "eco:textual-quotation" → ECO namespace + local
    if ":" in local:
        local = local.split(":", 1)[1]
    return ECO[local]


def skill_to_evidence_triples(skill) -> list[Triple]:  # noqa: ANN001 (Pydantic model)
    """Emit one ``indicium:Evidence`` block per ``evidence_spans[i]``."""
    triples: list[Triple] = []
    for i, span in enumerate(skill.evidence_spans):
        iri = evidence_span_iri(skill.slug, i)
        triples.append((iri, RDF.type, INDICIUM.Evidence))
        triples.append((iri, INDICIUM.ecoCode, _eco_iri(span.eco_code)))
        triples.append((iri, INDICIUM.exactQuote, rdflib.Literal(span.quote)))
        if span.source_doi:
            triples.append(
                (iri, INDICIUM.sourceDoi, rdflib.Literal(span.source_doi))
            )
        if span.paragraph_id:
            triples.append(
                (iri, INDICIUM.paragraphId, rdflib.Literal(span.paragraph_id))
            )
        # Link skill → evidence
        triples.append((ASB[skill.slug], INDICIUM.hasEvidence, iri))
    return triples


def tool_to_software_entity_triples(tool) -> list[Triple]:  # noqa: ANN001
    """Emit one ``indicium:SoftwareEntity`` per tool."""
    triples: list[Triple] = []
    iri = ASBTOOL[tool.slug]
    triples.append((iri, RDF.type, INDICIUM.SoftwareEntity))
    triples.append((iri, INDICIUM.name, rdflib.Literal(tool.name)))
    if tool.canonical_url:
        triples.append(
            (iri, INDICIUM.canonicalUrl, rdflib.Literal(tool.canonical_url))
        )
    # Explicit-null sentinel for bio_tools_id: emit rdf:nil rather than
    # silently dropping the slot so downstream queries can distinguish
    # "not resolved" from "not yet attempted".
    if tool.bio_tools_id:
        triples.append((iri, INDICIUM.bioToolsId, BIOTOOLS[tool.bio_tools_id]))
    else:
        triples.append((iri, INDICIUM.bioToolsId, RDF.nil))
    if tool.edam_operation:
        triples.append(
            (iri, INDICIUM.edamOperation, _edam_op_iri(tool.edam_operation))
        )
    for topic in tool.edam_topics:
        triples.append((iri, INDICIUM.edamTopic, _edam_topic_iri(topic)))
    return triples


def claim_to_triples(claim) -> list[Triple]:  # noqa: ANN001
    """Emit ``indicium:Claim`` with the Bucur 5-slot SuperPattern."""
    triples: list[Triple] = []
    iri = rdflib.URIRef(claim.claim_id)
    triples.append((iri, RDF.type, INDICIUM.Claim))
    triples.append((iri, INDICIUM.subject, rdflib.Literal(claim.subject)))
    triples.append((iri, INDICIUM.predicate, rdflib.Literal(claim.predicate)))
    triples.append((iri, INDICIUM.object, rdflib.Literal(claim.object)))
    for q in claim.qualifiers:
        triples.append((iri, INDICIUM.qualifier, rdflib.Literal(q)))
    if claim.super_pattern:
        triples.append(
            (iri, INDICIUM.superPattern, rdflib.Literal(claim.super_pattern))
        )
    return triples


def skill_claim_sepio_assertion_triples(skill) -> list[Triple]:  # noqa: ANN001
    """Emit one SEPIO assertion node per skill→claim link."""
    triples: list[Triple] = []
    for claim_iri_str in skill.claim_ids:
        assertion_iri = rdflib.URIRef(f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'{skill.slug}|{claim_iri_str}')}")
        triples.append((assertion_iri, RDF.type, SEPIO.Assertion))
        triples.append((assertion_iri, SEPIO.hasSubject, ASB[skill.slug]))
        triples.append((assertion_iri, SEPIO.hasObject, rdflib.URIRef(claim_iri_str)))
    return triples


def paper_to_information_source_triples(paper) -> list[Triple]:  # noqa: ANN001
    """Emit ``indicium:InformationSource`` from a DOI."""
    triples: list[Triple] = []
    iri = rdflib.URIRef(f"https://doi.org/{paper.doi}")
    triples.append((iri, RDF.type, INDICIUM.InformationSource))
    triples.append((iri, CITO.hasIdentifier, rdflib.Literal(paper.doi)))
    triples.append((iri, INDICIUM.title, rdflib.Literal(paper.title)))
    return triples


__all__ = [
    "ASB",
    "ASBTOOL",
    "BIOTOOLS",
    "CITO",
    "ECO",
    "EDAM_OP",
    "EDAM_TOPIC",
    "INDICIUM",
    "SEPIO",
    "Triple",
    "claim_to_triples",
    "evidence_span_iri",
    "paper_to_information_source_triples",
    "skill_claim_sepio_assertion_triples",
    "skill_to_evidence_triples",
    "tool_to_software_entity_triples",
]
