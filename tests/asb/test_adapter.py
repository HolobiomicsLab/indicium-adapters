"""Tests for the ASBAdapter orchestrator."""
from __future__ import annotations

from pathlib import Path

import rdflib
from rdflib.namespace import PROV, RDF

from indicium_adapters.asb.adapter import ASBAdapter
from indicium_adapters.asb.mapper import ASB, ASBTOOL, INDICIUM

FIXTURE = Path(__file__).parent / "fixtures" / "sample_collection"


def test_adapter_to_rdf_graph_round_trips_fixture(tmp_path: Path) -> None:
    adapter = ASBAdapter(
        cache_db=tmp_path / "bt.sqlite",
        offline=True,
    )
    graph = adapter.to_rdf_graph(FIXTURE)
    # Skill: evidence emitted
    skill_iri = ASB["feature-detection-lcms"]
    assert any(graph.triples((skill_iri, INDICIUM.hasEvidence, None)))
    # Tool: SoftwareEntity emitted
    tool_iri = ASBTOOL["mzmine"]
    assert (tool_iri, RDF.type, INDICIUM.SoftwareEntity) in graph
    # Claim: indicium:Claim emitted
    claim_iri = rdflib.URIRef(
        "https://w3id.org/holobiomicslab/asb-skill/feature-detection-lcms/claim/01"
    )
    assert (claim_iri, RDF.type, INDICIUM.Claim) in graph


def test_adapter_attaches_prov_to_every_typed_node(tmp_path: Path) -> None:
    adapter = ASBAdapter(
        cache_db=tmp_path / "bt.sqlite",
        offline=True,
    )
    graph = adapter.to_rdf_graph(FIXTURE)
    # Every node carrying an indicium type must also carry the three PROV triples.
    typed_subjects = {
        s
        for s, _, o in graph.triples((None, RDF.type, None))
        if isinstance(o, rdflib.URIRef)
        and str(o).startswith("https://w3id.org/holobiomicslab/indicium#")
    }
    assert typed_subjects, "fixture should produce at least one typed indicium node"
    for s in typed_subjects:
        assert any(graph.triples((s, PROV.wasGeneratedBy, None))), s
        assert any(graph.triples((s, PROV.wasDerivedFrom, None))), s
        assert any(graph.triples((s, PROV.atTime, None))), s


def test_adapter_run_iri_stable_within_one_invocation(tmp_path: Path) -> None:
    adapter = ASBAdapter(
        cache_db=tmp_path / "bt.sqlite",
        offline=True,
    )
    graph = adapter.to_rdf_graph(FIXTURE)
    run_iris = {o for _, _, o in graph.triples((None, PROV.wasGeneratedBy, None))}
    assert len(run_iris) == 1
