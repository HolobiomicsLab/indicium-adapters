"""Tests for the ASBAdapter orchestrator."""
from __future__ import annotations

from pathlib import Path

import indicium
import pytest
import rdflib
from rdflib.namespace import DCTERMS, PROV, RDF

from indicium_adapters.asb.adapter import ASBAdapter
from indicium_adapters.asb.mapper import (
    ASB,
    ASB_VOCAB,
    ASBTOOL,
    EVIDENCE_CLASS,
    FABIO,
    INDICIUM,
    SEPIO,
    SOFTWARE_CLASS,
    SOURCE_CLASS,
)
from indicium_adapters.asb.round_trip import count_shape_targeted_nodes

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
    # Tool: typed with the class indicium gives SoftwareEntity
    tool_iri = ASBTOOL["mzmine"]
    assert (tool_iri, RDF.type, SOFTWARE_CLASS) in graph
    # Claim: typed with the class indicium's shapes target
    claim_iri = rdflib.URIRef(
        "https://w3id.org/holobiomicslab/asb-skill/feature-detection-lcms/claim/01"
    )
    assert (claim_iri, RDF.type, rdflib.URIRef(indicium.asb_term("Claim"))) in graph


def test_adapter_attaches_prov_to_every_typed_node(tmp_path: Path) -> None:
    adapter = ASBAdapter(
        cache_db=tmp_path / "bt.sqlite",
        offline=True,
    )
    graph = adapter.to_rdf_graph(FIXTURE)
    # Every node the adapter types must also carry the three PROV triples.
    typed_subjects = {
        s
        for s, _, o in graph.triples((None, RDF.type, None))
        if str(o).startswith((str(INDICIUM), str(ASB_VOCAB), str(SEPIO), str(FABIO)))
    }
    claim_iri = rdflib.URIRef(
        "https://w3id.org/holobiomicslab/asb-skill/feature-detection-lcms/claim/01"
    )
    assert claim_iri in typed_subjects
    assert ASBTOOL["mzmine"] in typed_subjects
    assert rdflib.URIRef("https://doi.org/10.1/abc") in typed_subjects
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


def test_adapter_binds_asb_prefix_to_the_vocabulary(tmp_path: Path) -> None:
    """asb: names the vocabulary, not the skill instances."""
    adapter = ASBAdapter(cache_db=tmp_path / "bt.sqlite", offline=True)
    graph = adapter.to_rdf_graph(FIXTURE)
    prefixes = dict(graph.namespaces())
    assert str(prefixes["asb"]) == indicium.ASB_BASE
    assert str(prefixes["asbskill"]) == str(ASB)


def test_adapter_graph_is_validated_by_the_indicium_shapes(tmp_path: Path) -> None:
    """Evidence, tool, paper and claim nodes are focus nodes, and they conform."""
    with ASBAdapter(cache_db=tmp_path / "bt.sqlite", offline=True) as adapter:
        graph = adapter.to_rdf_graph(FIXTURE)
    for cls in (EVIDENCE_CLASS, SOFTWARE_CLASS, SOURCE_CLASS, ASB_VOCAB.Claim):
        assert any(graph.triples((None, RDF.type, cls))), cls
    # One skill evidence span, one tool, one paper (the skill, tool and claim
    # records cite the same DOI) and one claim.
    assert count_shape_targeted_nodes(graph) == 4
    conforms, report = indicium.validate_graph(graph)
    assert conforms, report


def _two_skill_collection(root: Path, titles: tuple[str, str]) -> Path:
    """Write a collection whose two skills cite one DOI with the given titles."""
    lines = [
        "collection_iri: https://w3id.org/holobiomicslab/asb-skill/collection/t/v1",
        "version: v1",
        "skills:",
    ]
    for i, title in enumerate(titles):
        slug = f"skill-{i}"
        lines += [f"  - slug: {slug}", f"    path: skills/{slug}/SKILL.md"]
        skill_dir = root / "skills" / slug
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nslug: {slug}\nname: Skill {i}\n"
            f"source_papers:\n  - doi: 10.1/abc\n    title: \"{title}\"\n---\n",
            encoding="utf-8",
        )
    (root / "collection.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def test_adapter_writes_the_title_the_records_of_a_paper_agree_on(tmp_path: Path) -> None:
    coll = _two_skill_collection(tmp_path / "c", ("A study", "A study"))
    with ASBAdapter(cache_db=tmp_path / "bt.sqlite", offline=True) as adapter:
        graph = adapter.to_rdf_graph(coll)
    paper = rdflib.URIRef("https://doi.org/10.1/abc")
    assert list(graph.objects(paper, DCTERMS.title)) == [rdflib.Literal("A study")]


def test_adapter_writes_no_title_when_the_records_of_a_paper_disagree(
    tmp_path: Path,
) -> None:
    """The Source shape allows one title; none is picked between two."""
    coll = _two_skill_collection(tmp_path / "c", ("A study", "tool-name"))
    with (
        ASBAdapter(cache_db=tmp_path / "bt.sqlite", offline=True) as adapter,
        pytest.warns(UserWarning, match=r"1 paper.*: 10\.1/abc\."),
    ):
        graph = adapter.to_rdf_graph(coll)
    paper = rdflib.URIRef("https://doi.org/10.1/abc")
    assert (paper, RDF.type, SOURCE_CLASS) in graph
    assert (paper, DCTERMS.identifier, rdflib.Literal("10.1/abc")) in graph
    assert list(graph.objects(paper, DCTERMS.title)) == []
    conforms, report = indicium.validate_graph(graph)
    assert conforms, report
