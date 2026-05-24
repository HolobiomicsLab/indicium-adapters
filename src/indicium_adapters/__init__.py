"""indicium-adapters — shared domain knowledge layer for the indicium ecosystem.

Defines the DomainAdapter structural Protocol, the SHACLProvider opt-in mixin,
and the discover_adapters() entry-point discovery function.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import rdflib

CURRENT_API_VERSION: int = 1
"""The protocol API version this package implements.

Increment when DomainAdapter gains or removes required members.
Adapters whose api_version != CURRENT_API_VERSION are skipped by
discover_adapters() with a UserWarning.
"""


@runtime_checkable
class DomainAdapter(Protocol):
    """Structural protocol for domain-specific claim enrichment adapters.

    Third-party implementations do NOT need to import this class.
    Any class that has these five attributes satisfies
    ``isinstance(obj, DomainAdapter)``.
    """

    domain_id: str
    """Unique identifier, lowercase, hyphen-separated. e.g. "metabolomics"."""

    qualifiers: frozenset[str]
    """Domain-specific qualifiers to add to Perspicacite's _QUALIFIERS set and
    LLM prompt. Must not conflict with the base 20-qualifier set in indicium."""

    ontology_prefixes: dict[str, str]
    """Prefix → base IRI mapping, e.g. {"CHEBI": "http://purl.obolibrary.org/obo/CHEBI_"}.
    Used by enrich_claim() and by Scriptorium's RDF builder to expand CURIEs.
    Note: indicium's own expand_curie() covers ECO/IAO/DoCO/CiTO/FaBiO/DCAT only —
    domain-specific prefixes must be expanded using THIS adapter's ontology_prefixes."""

    api_version: int
    """Protocol API version this adapter targets. Must equal CURRENT_API_VERSION
    (currently 1) to be loaded by discover_adapters()."""

    def extraction_context(self) -> str:
        """Return a short plain-text string appended to Perspicacite's LLM
        extraction prompt. Should name the domain, list extra qualifiers, and
        guide subject/object naming conventions."""
        ...

    def enrich_claim(self, claim: dict) -> dict:
        """Receive a validated 5-slot claim dict; return a new dict (never mutate
        input). May add an "ontology_terms" sub-dict mapping slot names to CURIEs
        e.g. {"subject": "CHEBI:14321"}. Must be a pure function (no I/O)."""
        ...


@runtime_checkable
class SHACLProvider(DomainAdapter, Protocol):
    """Optional mixin: adapters that can contribute domain-specific SHACL shapes.

    Implement this in addition to DomainAdapter when your adapter ships SHACL
    NodeShapes for domain-specific RDF classes. Consumers check
    ``isinstance(adapter, SHACLProvider)`` (or ``hasattr(adapter, "shacl_shapes")``)
    before calling ``shacl_shapes()``.
    """

    def shacl_shapes(self) -> rdflib.Graph: ...


def discover_adapters() -> dict[str, DomainAdapter]:
    """Return all installed DomainAdapters keyed by domain_id.

    Discovers via the 'indicium.adapters' entry-point group. Adapters whose
    api_version != CURRENT_API_VERSION are skipped with a UserWarning.
    If two packages register the same domain_id, the last one wins.

    Returns an empty dict when no adapters are installed (never raises).
    """
    import warnings
    from importlib.metadata import entry_points

    result: dict[str, DomainAdapter] = {}
    for ep in entry_points(group="indicium.adapters"):
        try:
            adapter: DomainAdapter = ep.load()()
            v = getattr(adapter, "api_version", None)
            if v != CURRENT_API_VERSION:
                warnings.warn(
                    f"Skipping adapter '{ep.name}': api_version={v!r}, "
                    f"expected {CURRENT_API_VERSION}. Reinstall or update the adapter.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            result[adapter.domain_id] = adapter
        except Exception as exc:
            warnings.warn(
                f"Failed to load adapter '{ep.name}': {exc}",
                UserWarning,
                stacklevel=2,
            )
            continue
    return result


from indicium_adapters.composite import CompositeAdapter, compose_adapters


def __getattr__(name: str):
    # Lazy-load the asb subpackage so the optional extras aren't
    # required for users who only need the core DomainAdapter Protocol.
    if name == "ASBAdapter":
        from indicium_adapters.asb import ASBAdapter

        return ASBAdapter
    raise AttributeError(name)


__all__ = [
    "ASBAdapter",
    "CURRENT_API_VERSION",
    "CompositeAdapter",
    "DomainAdapter",
    "SHACLProvider",
    "compose_adapters",
    "discover_adapters",
]
