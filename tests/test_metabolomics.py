"""Unit tests for MetabolomicsAdapter."""
import pytest
import rdflib
from rdflib import RDF
from indicium_adapters import DomainAdapter
from indicium_adapters.metabolomics import MetabolomicsAdapter


@pytest.fixture
def adapter():
    return MetabolomicsAdapter()


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_metabolomics_adapter_satisfies_protocol(adapter):
    assert isinstance(adapter, DomainAdapter)


def test_domain_id(adapter):
    assert adapter.domain_id == "metabolomics"


def test_qualifiers_is_frozenset(adapter):
    assert isinstance(adapter.qualifiers, frozenset)


def test_qualifiers_non_empty(adapter):
    assert len(adapter.qualifiers) > 0


def test_qualifiers_contain_expected_terms(adapter):
    expected = {"identifies", "quantifies", "is_biomarker_for",
                "discriminates_between", "metabolizes"}
    assert expected.issubset(adapter.qualifiers)


def test_ontology_prefixes_string_keys_and_values(adapter):
    for key, val in adapter.ontology_prefixes.items():
        assert isinstance(key, str)
        assert isinstance(val, str)
        assert val.startswith("http"), f"IRI {val!r} should start with 'http'"


def test_ontology_prefixes_contains_chebi(adapter):
    assert "CHEBI" in adapter.ontology_prefixes
    assert adapter.ontology_prefixes["CHEBI"].startswith("http://purl.obolibrary.org/obo/CHEBI_")


# ---------------------------------------------------------------------------
# extraction_context()
# ---------------------------------------------------------------------------

def test_extraction_context_returns_non_empty_string(adapter):
    ctx = adapter.extraction_context()
    assert isinstance(ctx, str)
    assert len(ctx) > 0


def test_extraction_context_mentions_metabolomics(adapter):
    assert "metabolomics" in adapter.extraction_context().lower()


def test_extraction_context_lists_qualifiers(adapter):
    ctx = adapter.extraction_context()
    # At least one qualifier should be mentioned
    assert any(q in ctx for q in adapter.qualifiers)


# ---------------------------------------------------------------------------
# enrich_claim()
# ---------------------------------------------------------------------------

def test_enrich_claim_adds_ontology_terms_for_known_subject(adapter):
    claim = {
        "context": "in vivo", "subject": "glucose", "qualifier": "quantifies",
        "relation": "measured in", "object": "plasma",
    }
    result = adapter.enrich_claim(claim)
    assert "ontology_terms" in result
    assert result["ontology_terms"]["subject"] == "CHEBI:17234"


def test_enrich_claim_adds_ontology_terms_for_known_object(adapter):
    claim = {
        "context": "in vitro", "subject": "enzyme X", "qualifier": "metabolizes",
        "relation": "converts", "object": "pyruvate",
    }
    result = adapter.enrich_claim(claim)
    assert "ontology_terms" in result
    assert result["ontology_terms"]["object"] == "CHEBI:15361"


def test_enrich_claim_case_insensitive_lookup(adapter):
    claim = {
        "context": "in vivo", "subject": "GLUTAMATE", "qualifier": "identifies",
        "relation": "detected via", "object": "MS",
    }
    result = adapter.enrich_claim(claim)
    assert result["ontology_terms"]["subject"] == "CHEBI:14321"


def test_enrich_claim_unknown_compound_unchanged(adapter):
    claim = {
        "context": "in vitro", "subject": "unknown_xyz_compound",
        "qualifier": "identifies", "relation": "detected", "object": "unknown_abc",
    }
    result = adapter.enrich_claim(claim)
    # No ontology_terms added when nothing is known
    assert "ontology_terms" not in result


def test_enrich_claim_never_mutates_input(adapter):
    original = {
        "context": "in vivo", "subject": "glucose", "qualifier": "quantifies",
        "relation": "measured in", "object": "plasma",
    }
    before = dict(original)
    adapter.enrich_claim(original)
    assert original == before, "enrich_claim() must not mutate the input dict"


def test_enrich_claim_returns_new_dict(adapter):
    claim = {
        "context": "in vivo", "subject": "lactate", "qualifier": "quantifies",
        "relation": "measured in", "object": "serum",
    }
    result = adapter.enrich_claim(claim)
    assert result is not claim


def test_enrich_claim_preserves_existing_fields(adapter):
    claim = {
        "context": "in vivo", "subject": "glucose", "qualifier": "quantifies",
        "relation": "measured in", "object": "plasma",
        "evidence": [{"doi": "10.1/x"}],
    }
    result = adapter.enrich_claim(claim)
    assert result["evidence"] == [{"doi": "10.1/x"}]


def test_enrich_claim_both_slots_known(adapter):
    claim = {
        "context": "cell", "subject": "atp", "qualifier": "metabolizes",
        "relation": "produced from", "object": "glucose",
    }
    result = adapter.enrich_claim(claim)
    assert result["ontology_terms"]["subject"] == "CHEBI:15422"
    assert result["ontology_terms"]["object"] == "CHEBI:17234"


def test_enrich_claim_does_not_mutate_existing_ontology_terms(adapter):
    """When input already has ontology_terms, the original inner dict must not be mutated."""
    inner = {"subject": "HMDB:HMDB0000001"}
    claim = {
        "context": "in vivo", "subject": "glucose", "qualifier": "quantifies",
        "relation": "measured in", "object": "plasma",
        "ontology_terms": inner,
    }
    result = adapter.enrich_claim(claim)
    # result may overwrite subject with CHEBI, but the original inner dict must be unchanged
    assert inner == {"subject": "HMDB:HMDB0000001"}, (
        "enrich_claim() must not mutate the pre-existing ontology_terms dict"
    )
    # The result should have the new CHEBI value (not the old HMDB value)
    assert result["ontology_terms"]["subject"] == "CHEBI:17234"


# ---------------------------------------------------------------------------
# shacl_shapes()
# ---------------------------------------------------------------------------


def test_api_version(adapter):
    """api_version must equal 1."""
    assert adapter.api_version == 1


def test_metabolomics_satisfies_shacl_provider(adapter):
    """MetabolomicsAdapter must satisfy the SHACLProvider mixin protocol."""
    from indicium_adapters import SHACLProvider
    assert isinstance(adapter, SHACLProvider)


def test_shacl_shapes_returns_graph(adapter):
    """shacl_shapes() must return a non-empty rdflib.Graph."""
    g = adapter.shacl_shapes()
    assert isinstance(g, rdflib.Graph)
    assert len(g) > 0


def test_shacl_shapes_contains_node_shape(adapter):
    """The returned graph must contain at least one sh:NodeShape triple."""
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    g = adapter.shacl_shapes()
    node_shapes = list(g.subjects(RDF.type, SH.NodeShape))
    assert len(node_shapes) > 0, (
        "shacl_shapes() graph must contain at least one sh:NodeShape"
    )


def test_shacl_shapes_returns_independent_graphs(adapter):
    """Calling shacl_shapes() twice must return independent Graph objects."""
    g1 = adapter.shacl_shapes()
    g2 = adapter.shacl_shapes()
    assert g1 is not g2
    sentinel = (
        rdflib.URIRef("urn:test:s"),
        rdflib.URIRef("urn:test:p"),
        rdflib.URIRef("urn:test:o"),
    )
    g1.add(sentinel)
    assert sentinel not in g2, (
        "shacl_shapes() must return independent Graphs — mutating one affected the other"
    )
