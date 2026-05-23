"""Unit tests for MetabolomicsAdapter."""
import pytest
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
    assert result["ontology_terms"]["subject"] == "CHEBI:4167"


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
    assert result["ontology_terms"]["object"] == "CHEBI:4167"
