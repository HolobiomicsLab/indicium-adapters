"""CompositeAdapter — combine multiple DomainAdapters into a single adapter.

Use ``compose_adapters()`` as the preferred factory: it returns the adapter
unchanged when only one is provided, avoiding unnecessary wrapping.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from indicium_adapters import CURRENT_API_VERSION, SHACLProvider

if TYPE_CHECKING:
    import rdflib
    from indicium_adapters import DomainAdapter


class CompositeAdapter:
    """Combines 2+ DomainAdapters into one that satisfies both
    DomainAdapter and SHACLProvider protocols.

    Composition rules:
    - ``domain_id``: adapter IDs joined with "+".
    - ``qualifiers``: frozenset union of all adapters' qualifier sets.
    - ``ontology_prefixes``: merged dict; later adapters win on key conflict.
    - ``api_version``: always ``CURRENT_API_VERSION``.
    - ``extraction_context()``: all contexts joined with "\\n\\n".
    - ``enrich_claim()``: sequential chain — each adapter enriches the output
      of the previous one.
    - ``shacl_shapes()``: merged ``rdflib.Graph`` from all adapters that
      implement ``shacl_shapes()``; adapters without it are silently skipped.
    """

    def __init__(self, adapters: list[DomainAdapter]) -> None:
        if len(adapters) < 2:
            raise ValueError(
                f"CompositeAdapter requires at least 2 adapters, got {len(adapters)}. "
                "Use compose_adapters() to handle the single-adapter case."
            )
        self._adapters = list(adapters)

        self.domain_id: str = "+".join(a.domain_id for a in self._adapters)
        self.api_version: int = CURRENT_API_VERSION

        self.qualifiers: frozenset[str] = frozenset().union(
            *(a.qualifiers for a in self._adapters)
        )

        merged_prefixes: dict[str, str] = {}
        for a in self._adapters:
            merged_prefixes.update(a.ontology_prefixes)
        self.ontology_prefixes: dict[str, str] = merged_prefixes

    def extraction_context(self) -> str:
        """Concatenate all adapters' extraction contexts with a blank line between."""
        return "\n\n".join(a.extraction_context() for a in self._adapters)

    def enrich_claim(self, claim: dict) -> dict:
        """Chain all adapters' enrich_claim() sequentially.

        Each adapter receives the output of the previous one. Input is never
        mutated — the first adapter in the chain gets a shallow copy.
        """
        result = dict(claim)   # shallow copy so the original is never mutated
        for a in self._adapters:
            result = a.enrich_claim(result)
        return result

    def shacl_shapes(self) -> rdflib.Graph:
        """Merge SHACL shapes from all adapters that implement shacl_shapes().

        Adapters that do not have a ``shacl_shapes()`` method are silently
        skipped. Returns an empty Graph if no adapter provides shapes.
        """
        import rdflib as _rdflib
        g: _rdflib.Graph = _rdflib.Graph()
        for a in self._adapters:
            if isinstance(a, SHACLProvider):
                g = g + a.shacl_shapes()
        return g


def compose_adapters(adapters: list[DomainAdapter]) -> DomainAdapter:
    """Return a single DomainAdapter representing all given adapters.

    - 0 adapters → raises ``ValueError``.
    - 1 adapter  → returned unchanged (no wrapping overhead).
    - 2+ adapters → returns a ``CompositeAdapter``.
    """
    if not adapters:
        raise ValueError(
            "compose_adapters() requires at least one adapter; got an empty list."
        )
    if len(adapters) == 1:
        return adapters[0]
    return CompositeAdapter(adapters)


__all__ = ["CompositeAdapter", "compose_adapters"]
