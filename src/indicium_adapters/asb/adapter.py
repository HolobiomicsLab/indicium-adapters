"""ASBAdapter — orchestrate load + bio.tools enrich + map + PROV wrap.

Pipeline::

    load_collection(dir)
        ↓ ASBCollection
    enrich (BioToolsResolver)        — fills ASBToolRecord.bio_tools_id
        ↓
    mapper.* → list[Triple]
        ↓
    attach PROV envelope to every typed node
        ↓
    rdflib.Graph

The graph is what consumers (asb-skill-collections CI, downstream
SPARQL endpoints, the round-trip checker) consume.
"""
from __future__ import annotations

import uuid
import warnings
from pathlib import Path
from typing import Self

import rdflib
from rdflib.namespace import DCTERMS, RDF

from indicium_adapters.asb.biotools import BioToolsResolver
from indicium_adapters.asb.loader import load_collection
from indicium_adapters.asb.mapper import (
    ASB,
    ASB_VOCAB,
    ASBTOOL,
    BIOTOOLS,
    CITO,
    ECO,
    FABIO,
    INDICIUM,
    SEPIO,
    claim_to_triples,
    paper_to_information_source_triples,
    skill_claim_sepio_assertion_triples,
    skill_to_evidence_triples,
    tool_to_software_entity_triples,
)
from indicium_adapters.asb.models import ASBCollection, ASBSourcePaper
from indicium_adapters.asb.prov import ProvEnvelope, attach_prov

# Bases of every class the mapper types a node with.
_MAPPED_TYPE_BASES = (str(INDICIUM), str(ASB_VOCAB), str(SEPIO), str(FABIO))


def _papers(coll: ASBCollection) -> list[ASBSourcePaper]:
    """Return one paper per DOI cited by the collection's records.

    The indicium Source shape allows one ``dct:title``. A paper keeps the
    title its records give when they give one; when they give different
    titles, nothing here can tell which is right, so the paper is written
    without a title and a warning counts such papers. The DOI identifies it.
    """
    titles: dict[str, set[str]] = {}
    for record in [*coll.skills, *coll.tools, *coll.claims]:
        for paper in record.source_papers:
            titles.setdefault(paper.doi, set()).update({paper.title} - {""})
    conflicting = sum(1 for found in titles.values() if len(found) > 1)
    if conflicting:
        warnings.warn(
            f"{conflicting} paper(s) carry different titles across records; "
            "they are written without dct:title.",
            UserWarning,
            stacklevel=3,
        )
    return [
        ASBSourcePaper(doi=doi, title=next(iter(found)) if len(found) == 1 else "")
        for doi, found in titles.items()
    ]


class ASBAdapter:
    """Compose a full indicium graph from an ASB-Skill collection dir."""

    def __init__(
        self,
        cache_db: Path | str | None = None,
        offline: bool | None = None,
    ) -> None:
        if cache_db is None:
            cache_db = Path.home() / ".cache" / "indicium-adapters" / "biotools.sqlite"
        self._resolver = BioToolsResolver(cache_db=cache_db, offline=offline)

    def to_rdf_graph(self, collection_dir: Path | str) -> rdflib.Graph:
        coll = load_collection(collection_dir)
        # Enrich tools with bio.tools ids before mapping.
        for tool in coll.tools:
            tool.bio_tools_id = (
                tool.bio_tools_id or self._resolver.resolve(tool.canonical_url)
            )

        run_iri = f"urn:uuid:{uuid.uuid4()}"
        envelope = ProvEnvelope.new(
            adapter_run_iri=run_iri, collection_iri=coll.collection_iri
        )

        g = rdflib.Graph()
        g.bind("indicium", INDICIUM)
        g.bind("asb", ASB_VOCAB)
        g.bind("eco", ECO)
        g.bind("cito", CITO)
        g.bind("sepio", SEPIO)
        g.bind("fabio", FABIO)
        g.bind("dct", DCTERMS)
        g.bind("asbskill", ASB)
        g.bind("asbtool", ASBTOOL)
        g.bind("biotools", BIOTOOLS)

        # Skills + their evidence + SEPIO assertions
        for skill in coll.skills:
            g.add((ASB[skill.slug], RDF.type, INDICIUM.Skill))
            g.add((ASB[skill.slug], INDICIUM.name, rdflib.Literal(skill.name)))
            for t in skill_to_evidence_triples(skill):
                g.add(t)
            for t in skill_claim_sepio_assertion_triples(skill):
                g.add(t)

        # Tools
        for tool in coll.tools:
            for t in tool_to_software_entity_triples(tool):
                g.add(t)

        # Claims
        for claim in coll.claims:
            for t in claim_to_triples(claim):
                g.add(t)

        # Papers cited by skills, tools and claims, one node per DOI
        for paper in _papers(coll):
            for t in paper_to_information_source_triples(paper):
                g.add(t)

        # Wrap every node typed by this mapper in PROV.
        typed_subjects = {
            s
            for s, _, o in g.triples((None, RDF.type, None))
            if str(o).startswith(_MAPPED_TYPE_BASES)
        }
        for s in typed_subjects:
            attach_prov(g, s, envelope)

        return g

    def close(self) -> None:
        self._resolver.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


__all__ = ["ASBAdapter"]
