"""Protocol compliance tests for DomainAdapter.

Discovery tests (requiring installed entry-points) are in the same file
but isolated so they can be skipped when entry-points aren't registered.
"""
import importlib.util
import warnings
from unittest.mock import MagicMock, patch

import pytest

from indicium_adapters import DomainAdapter, discover_adapters

# Discovering a real domain adapter (metabolomics) needs the separate
# indicium-adapters-metabolomics package installed so its entry-point registers.
# Isolated CI doesn't install it, so these tests skip there (per this module's
# docstring) and run fully in a complete-hub install.
_HAS_METABOLOMICS = importlib.util.find_spec("indicium_adapters_metabolomics") is not None
requires_metabolomics = pytest.mark.skipif(
    not _HAS_METABOLOMICS,
    reason="indicium-adapters-metabolomics not installed (cross-repo discovery test)",
)


# ---------------------------------------------------------------------------
# Structural typing
# ---------------------------------------------------------------------------

class _MinimalAdapter:
    """Smallest valid DomainAdapter — just the required attributes."""
    domain_id = "test_domain"
    qualifiers = frozenset({"test_q"})
    ontology_prefixes = {"TST": "http://test.example.org/"}
    api_version = 1  # required by updated Protocol

    def extraction_context(self) -> str:
        return "Domain: test."

    def enrich_claim(self, claim: dict) -> dict:
        return dict(claim)


class _MissingMethods:
    """Adapter that has data attributes but no methods."""
    domain_id = "bad"
    qualifiers = frozenset()
    ontology_prefixes = {}


class _MissingData:
    """Adapter that has methods but is missing required data attributes."""
    def extraction_context(self) -> str:
        return ""

    def enrich_claim(self, claim: dict) -> dict:
        return claim


def test_minimal_adapter_satisfies_protocol():
    assert isinstance(_MinimalAdapter(), DomainAdapter)


def test_adapter_missing_methods_fails_protocol():
    assert not isinstance(_MissingMethods(), DomainAdapter)


def test_adapter_missing_data_attributes_fails_protocol():
    assert not isinstance(_MissingData(), DomainAdapter)


def test_domain_adapter_is_runtime_checkable():
    """DomainAdapter must be usable with isinstance() — no TypeError."""
    obj = object()
    result = isinstance(obj, DomainAdapter)  # must not raise
    assert result is False


# ---------------------------------------------------------------------------
# discover_adapters() — basic contract (no entry-points needed)
# ---------------------------------------------------------------------------

def test_discover_adapters_returns_dict():
    """discover_adapters() always returns a dict (may be empty if not installed)."""
    result = discover_adapters()
    assert isinstance(result, dict)


def test_discover_adapters_values_satisfy_protocol():
    """Every discovered adapter satisfies isinstance(adapter, DomainAdapter)."""
    adapters = discover_adapters()
    for name, adapter in adapters.items():
        assert isinstance(adapter, DomainAdapter), (
            f"Adapter {name!r} does not satisfy DomainAdapter protocol"
        )


def test_discover_adapters_domain_ids_are_lowercase_no_spaces():
    """domain_id values must be lowercase with no spaces (convention)."""
    adapters = discover_adapters()
    for name, adapter in adapters.items():
        assert isinstance(adapter.domain_id, str)
        assert adapter.domain_id == adapter.domain_id.lower(), (
            f"{name!r} domain_id {adapter.domain_id!r} is not lowercase"
        )
        assert " " not in adapter.domain_id, (
            f"{name!r} domain_id {adapter.domain_id!r} contains spaces"
        )


# ---------------------------------------------------------------------------
# Discovery — requires installed entry-point (run 'uv sync --extra dev' to register)
# ---------------------------------------------------------------------------

@requires_metabolomics
def test_discover_adapters_finds_metabolomics():
    """After installation, discover_adapters() must return the metabolomics adapter."""
    adapters = discover_adapters()
    assert "metabolomics" in adapters, (
        "MetabolomicsAdapter not found. Run 'uv sync --extra dev' in indicium-adapters "
        "to register the entry-point."
    )


@requires_metabolomics
def test_discovered_metabolomics_satisfies_protocol():
    """Discovered metabolomics adapter must satisfy the DomainAdapter protocol."""
    adapters = discover_adapters()
    assert "metabolomics" in adapters, "Run 'uv sync --extra dev' in indicium-adapters"
    assert isinstance(adapters["metabolomics"], DomainAdapter)


@requires_metabolomics
def test_discovered_metabolomics_domain_id():
    """Discovered metabolomics adapter must report domain_id == 'metabolomics'."""
    adapters = discover_adapters()
    assert "metabolomics" in adapters, "Run 'uv sync --extra dev' in indicium-adapters"
    assert adapters["metabolomics"].domain_id == "metabolomics"


# ---------------------------------------------------------------------------
# Protocol versioning (Task 1)
# ---------------------------------------------------------------------------


def test_current_api_version_exported():
    """CURRENT_API_VERSION must be exported and be an int equal to 1."""
    from indicium_adapters import CURRENT_API_VERSION
    assert isinstance(CURRENT_API_VERSION, int)
    assert CURRENT_API_VERSION == 1


@requires_metabolomics
def test_metabolomics_has_api_version():
    """Discovered metabolomics adapter must have api_version == CURRENT_API_VERSION.

    MetabolomicsAdapter now lives in indicium-adapters-metabolomics; test via
    discover_adapters() so the test is package-location-agnostic.
    """
    from indicium_adapters import CURRENT_API_VERSION
    adapters = discover_adapters()
    assert "metabolomics" in adapters, (
        "MetabolomicsAdapter not found. Install indicium-adapters-metabolomics."
    )
    adapter = adapters["metabolomics"]
    assert hasattr(adapter, "api_version")
    assert adapter.api_version == CURRENT_API_VERSION


def test_discover_adapters_skips_wrong_api_version():
    """discover_adapters() must emit UserWarning and skip adapters with wrong api_version."""
    class _WrongVersionAdapter:
        domain_id = "bad"
        api_version = 999
        qualifiers = frozenset()
        ontology_prefixes = {}
        def extraction_context(self): return ""
        def enrich_claim(self, c): return c

    mock_ep = MagicMock()
    mock_ep.name = "bad_adapter"
    mock_ep.load.return_value = _WrongVersionAdapter

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = discover_adapters()

    assert "bad" not in result
    assert any("api_version" in str(warning.message) for warning in w), (
        "Expected a UserWarning mentioning api_version"
    )
    assert any(warning.category is UserWarning for warning in w), (
        "Expected category to be UserWarning"
    )


def test_discover_adapters_loads_correct_api_version():
    """discover_adapters() must load adapters with the current api_version."""
    from indicium_adapters import CURRENT_API_VERSION

    class _GoodVersionAdapter:
        domain_id = "good"
        api_version = CURRENT_API_VERSION
        qualifiers = frozenset()
        ontology_prefixes = {}
        def extraction_context(self): return ""
        def enrich_claim(self, c): return c

    mock_ep = MagicMock()
    mock_ep.name = "good_adapter"
    mock_ep.load.return_value = _GoodVersionAdapter

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = discover_adapters()

    assert "good" in result
    assert isinstance(result["good"], DomainAdapter)


# ---------------------------------------------------------------------------
# SHACL Provider protocol (Task 2)
# ---------------------------------------------------------------------------


def test_shacl_provider_is_exported():
    """SHACLProvider must be importable from indicium_adapters."""
    from indicium_adapters import SHACLProvider
    assert SHACLProvider is not None


def test_shacl_provider_is_runtime_checkable():
    """isinstance() with SHACLProvider must not raise TypeError."""
    from indicium_adapters import SHACLProvider
    result = isinstance(object(), SHACLProvider)
    assert result is False


def test_minimal_adapter_does_not_satisfy_shacl_provider():
    """A plain DomainAdapter without shacl_shapes() must NOT satisfy SHACLProvider."""
    from indicium_adapters import SHACLProvider
    assert not isinstance(_MinimalAdapter(), SHACLProvider)


def test_shacl_provider_requires_shacl_shapes_method():
    """A class with all DomainAdapter attrs + shacl_shapes() satisfies SHACLProvider."""
    import rdflib
    from indicium_adapters import SHACLProvider

    class _FullSHACLAdapter:
        domain_id = "test"
        api_version = 1
        qualifiers = frozenset()
        ontology_prefixes = {}
        def extraction_context(self): return ""
        def enrich_claim(self, c): return c
        def shacl_shapes(self) -> rdflib.Graph:
            return rdflib.Graph()

    assert isinstance(_FullSHACLAdapter(), SHACLProvider)
