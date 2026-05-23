"""Protocol compliance tests for DomainAdapter.

Discovery tests (requiring installed entry-points) are in the same file
but isolated so they can be skipped when entry-points aren't registered.
"""
from indicium_adapters import DomainAdapter, discover_adapters


# ---------------------------------------------------------------------------
# Structural typing
# ---------------------------------------------------------------------------

class _MinimalAdapter:
    """Smallest valid DomainAdapter — just the required attributes."""
    domain_id = "test_domain"
    qualifiers = frozenset({"test_q"})
    ontology_prefixes = {"TST": "http://test.example.org/"}

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

def test_discover_adapters_finds_metabolomics():
    """After installation, discover_adapters() must return the metabolomics adapter."""
    adapters = discover_adapters()
    assert "metabolomics" in adapters, (
        "MetabolomicsAdapter not found. Run 'uv sync --extra dev' in indicium-adapters "
        "to register the entry-point."
    )


def test_discovered_metabolomics_satisfies_protocol():
    """Discovered metabolomics adapter must satisfy the DomainAdapter protocol."""
    adapters = discover_adapters()
    assert "metabolomics" in adapters, "Run 'uv sync --extra dev' in indicium-adapters"
    assert isinstance(adapters["metabolomics"], DomainAdapter)


def test_discovered_metabolomics_domain_id():
    """Discovered metabolomics adapter must report domain_id == 'metabolomics'."""
    adapters = discover_adapters()
    assert "metabolomics" in adapters, "Run 'uv sync --extra dev' in indicium-adapters"
    assert adapters["metabolomics"].domain_id == "metabolomics"
