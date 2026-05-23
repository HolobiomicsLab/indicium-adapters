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
    qualifiers: frozenset[str]
    ontology_prefixes: dict[str, str]
    api_version: int
    """Protocol API version this adapter targets. Must equal CURRENT_API_VERSION
    (currently 1) to be loaded by discover_adapters()."""

    def extraction_context(self) -> str: ...
    def enrich_claim(self, claim: dict) -> dict: ...


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
        except Exception:
            continue
    return result


__all__ = ["CURRENT_API_VERSION", "DomainAdapter", "SHACLProvider", "discover_adapters"]
