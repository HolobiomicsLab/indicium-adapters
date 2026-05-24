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
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

from indicium_adapters.asb.biotools import BioToolsResolver
from indicium_adapters.asb.loader import load_collection
from indicium_adapters.asb.mapper import (
    ASB,
    ASBTOOL,
    BIOTOOLS,
    CITO,
    ECO,
    INDICIUM,
    SEPIO,
    claim_to_triples,
    paper_to_information_source_triples,
    skill_claim_sepio_assertion_triples,
    skill_to_evidence_triples,
    tool_to_software_entity_triples,
)
from indicium_adapters.asb.prov import ProvEnvelope, attach_prov


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
        g.bind("eco", ECO)
        g.bind("cito", CITO)
        g.bind("sepio", SEPIO)
        g.bind("asb", ASB)
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
            for paper in skill.source_papers:
                for t in paper_to_information_source_triples(paper):
                    g.add(t)

        # Tools
        for tool in coll.tools:
            for t in tool_to_software_entity_triples(tool):
                g.add(t)
            for paper in tool.source_papers:
                for t in paper_to_information_source_triples(paper):
                    g.add(t)

        # Claims
        for claim in coll.claims:
            for t in claim_to_triples(claim):
                g.add(t)
            for paper in claim.source_papers:
                for t in paper_to_information_source_triples(paper):
                    g.add(t)

        # Wrap every typed indicium node + every SEPIO assertion in PROV.
        typed_subjects = {
            s
            for s, _, o in g.triples((None, RDF.type, None))
            if isinstance(o, rdflib.URIRef)
            and (
                str(o).startswith(str(INDICIUM))
                or str(o).startswith(str(SEPIO))
            )
        }
        for s in typed_subjects:
            attach_prov(g, s, envelope)

        return g

    def close(self) -> None:
        self._resolver.close()

    def __enter__(self) -> "ASBAdapter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


__all__ = ["ASBAdapter"]
