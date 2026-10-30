"""Tests for CompositeAdapter and compose_adapters()."""
from __future__ import annotations

from typing import ClassVar

import pytest
import rdflib
from rdflib import RDF

from indicium_adapters import CURRENT_API_VERSION, DomainAdapter, SHACLProvider
from indicium_adapters.composite import CompositeAdapter, compose_adapters

# ---------------------------------------------------------------------------
# Minimal mock adapters (no external deps)
# ---------------------------------------------------------------------------

class _AdapterA:
    domain_id = "domain_a"
    api_version = 1
    qualifiers = frozenset({"qualifier_a1", "qualifier_a2"})
    ontology_prefixes: ClassVar[dict[str, str]] = {
        "PREFIX_A": "http://example.org/a/",
        "SHARED": "http://example.org/shared_a/",   # conflicts with B
    }

    def extraction_context(self) -> str:
        return "Domain A context."

    def enrich_claim(self, claim: dict) -> dict:
        c = dict(claim)
        c["ontology_terms"] = {**c.get("ontology_terms", {}), "subject": "A:001"}
        return c

    def shacl_shapes(self) -> rdflib.Graph:
        g = rdflib.Graph()
        g.add((rdflib.URIRef("urn:shape:a"), RDF.type,
               rdflib.URIRef("http://www.w3.org/ns/shacl#NodeShape")))
        return g


class _AdapterB:
    domain_id = "domain_b"
    api_version = 1
    qualifiers = frozenset({"qualifier_b1"})
    ontology_prefixes: ClassVar[dict[str, str]] = {
        "PREFIX_B": "http://example.org/b/",
        "SHARED": "http://example.org/shared_b/",   # conflicts with A; B wins
    }

    def extraction_context(self) -> str:
        return "Domain B context."

    def enrich_claim(self, claim: dict) -> dict:
        c = dict(claim)
        c["ontology_terms"] = {**c.get("ontology_terms", {}), "object": "B:002"}
        return c

    def shacl_shapes(self) -> rdflib.Graph:
        g = rdflib.Graph()
        g.add((rdflib.URIRef("urn:shape:b"), RDF.type,
               rdflib.URIRef("http://www.w3.org/ns/shacl#NodeShape")))
        return g


class _AdapterNoSHACL:
    """Adapter that satisfies DomainAdapter but NOT SHACLProvider (no shacl_shapes)."""
    domain_id = "domain_c"
    api_version = 1
    qualifiers = frozenset({"qualifier_c1"})
    ontology_prefixes: ClassVar[dict[str, str]] = {"PREFIX_C": "http://example.org/c/"}

    def extraction_context(self) -> str:
        return "Domain C context."

    def enrich_claim(self, claim: dict) -> dict:
        c = dict(claim)
        c["seen_by_c"] = True
        return c


@pytest.fixture
def a():
    return _AdapterA()


@pytest.fixture
def b():
    return _AdapterB()


@pytest.fixture
def c_no_shacl():
    return _AdapterNoSHACL()


@pytest.fixture
def composite_ab(a, b):
    return CompositeAdapter([a, b])


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_composite_satisfies_domain_adapter_protocol(composite_ab):
    assert isinstance(composite_ab, DomainAdapter)


def test_composite_satisfies_shacl_provider_protocol(composite_ab):
    assert isinstance(composite_ab, SHACLProvider)


def test_composite_api_version_equals_current(composite_ab):
    assert composite_ab.api_version == CURRENT_API_VERSION


# ---------------------------------------------------------------------------
# domain_id
# ---------------------------------------------------------------------------

def test_composite_domain_id_joins_with_plus(composite_ab):
    assert composite_ab.domain_id == "domain_a+domain_b"


# ---------------------------------------------------------------------------
# qualifiers
# ---------------------------------------------------------------------------

def test_composite_qualifiers_is_frozenset(composite_ab):
    assert isinstance(composite_ab.qualifiers, frozenset)


def test_composite_qualifiers_is_union_of_all(composite_ab):
    expected = frozenset({"qualifier_a1", "qualifier_a2", "qualifier_b1"})
    assert composite_ab.qualifiers == expected


# ---------------------------------------------------------------------------
# ontology_prefixes
# ---------------------------------------------------------------------------

def test_composite_ontology_prefixes_contains_all_non_conflicting_keys(composite_ab):
    assert "PREFIX_A" in composite_ab.ontology_prefixes
    assert "PREFIX_B" in composite_ab.ontology_prefixes


def test_composite_ontology_prefixes_later_adapter_wins_on_conflict(composite_ab):
    # Both A and B define SHARED; B is second, so B wins
    assert composite_ab.ontology_prefixes["SHARED"] == "http://example.org/shared_b/"


# ---------------------------------------------------------------------------
# extraction_context()
# ---------------------------------------------------------------------------

def test_composite_extraction_context_contains_adapter_a_text(composite_ab):
    ctx = composite_ab.extraction_context()
    assert "Domain A context." in ctx


def test_composite_extraction_context_contains_adapter_b_text(composite_ab):
    ctx = composite_ab.extraction_context()
    assert "Domain B context." in ctx


def test_composite_extraction_context_uses_double_newline_separator(composite_ab):
    ctx = composite_ab.extraction_context()
    assert "\n\n" in ctx


# ---------------------------------------------------------------------------
# enrich_claim()
# ---------------------------------------------------------------------------

def test_composite_enrich_claim_chains_both_adapters(composite_ab):
    """Both A and B enrichments must appear in the result."""
    claim = {
        "context": "in vivo", "subject": "X", "qualifier": "inhibits",
        "relation": "inhibits", "object": "Y",
    }
    result = composite_ab.enrich_claim(claim)
    # A sets subject, B sets object
    assert result["ontology_terms"]["subject"] == "A:001"
    assert result["ontology_terms"]["object"] == "B:002"


def test_composite_enrich_claim_never_mutates_input(composite_ab):
    original = {
        "context": "in vivo", "subject": "X", "qualifier": "inhibits",
        "relation": "inhibits", "object": "Y",
    }
    before = dict(original)
    composite_ab.enrich_claim(original)
    assert original == before


def test_composite_enrich_claim_returns_new_dict(composite_ab):
    claim = {
        "context": "in vivo", "subject": "X", "qualifier": "inhibits",
        "relation": "inhibits", "object": "Y",
    }
    result = composite_ab.enrich_claim(claim)
    assert result is not claim


def test_composite_enrich_claim_second_adapter_sees_first_output(a, c_no_shacl):
    """Chain: A sets ontology_terms.subject, C_no_shacl sets seen_by_c on A's output."""
    comp = CompositeAdapter([a, c_no_shacl])
    claim = {"context": "x", "subject": "s", "qualifier": "q", "relation": "r", "object": "o"}
    result = comp.enrich_claim(claim)
    assert result["ontology_terms"]["subject"] == "A:001"
    assert result.get("seen_by_c") is True


# ---------------------------------------------------------------------------
# shacl_shapes()
# ---------------------------------------------------------------------------

def test_composite_shacl_shapes_returns_rdflib_graph(composite_ab):
    g = composite_ab.shacl_shapes()
    assert isinstance(g, rdflib.Graph)


def test_composite_shacl_shapes_contains_shapes_from_both_adapters(composite_ab):
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    g = composite_ab.shacl_shapes()
    node_shapes = list(g.subjects(RDF.type, SH.NodeShape))
    # Expect shape:a and shape:b
    shape_uris = {str(s) for s in node_shapes}
    assert "urn:shape:a" in shape_uris
    assert "urn:shape:b" in shape_uris


def test_composite_shacl_shapes_returns_independent_graphs(composite_ab):
    g1 = composite_ab.shacl_shapes()
    g2 = composite_ab.shacl_shapes()
    assert g1 is not g2
    sentinel = (rdflib.URIRef("urn:t:s"), rdflib.URIRef("urn:t:p"), rdflib.URIRef("urn:t:o"))
    g1.add(sentinel)
    assert sentinel not in g2


def test_composite_shacl_shapes_skips_non_shacl_providers(a, c_no_shacl):
    """Adapters without shacl_shapes() must be silently skipped."""
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    comp = CompositeAdapter([a, c_no_shacl])
    g = comp.shacl_shapes()
    node_shapes = {str(s) for s in g.subjects(RDF.type, SH.NodeShape)}
    assert "urn:shape:a" in node_shapes     # A's shape present
    # c_no_shacl has no shacl_shapes(), so no crash and graph still valid


# ---------------------------------------------------------------------------
# Constructor guards
# ---------------------------------------------------------------------------

def test_composite_requires_at_least_two_adapters(a):
    with pytest.raises(ValueError, match="at least 2"):
        CompositeAdapter([a])


def test_composite_requires_non_empty_list():
    with pytest.raises(ValueError, match="at least 2"):
        CompositeAdapter([])


# ---------------------------------------------------------------------------
# compose_adapters() factory
# ---------------------------------------------------------------------------

def test_compose_adapters_single_returns_same_object(a):
    result = compose_adapters([a])
    assert result is a


def test_compose_adapters_multiple_returns_composite(a, b):
    result = compose_adapters([a, b])
    assert isinstance(result, CompositeAdapter)


def test_compose_adapters_empty_raises():
    with pytest.raises(ValueError, match="at least one"):
        compose_adapters([])


def test_compose_adapters_three_adapters(a, b, c_no_shacl):
    result = compose_adapters([a, b, c_no_shacl])
    assert isinstance(result, CompositeAdapter)
    assert "domain_a" in result.domain_id
    assert "domain_b" in result.domain_id
    assert "domain_c" in result.domain_id
