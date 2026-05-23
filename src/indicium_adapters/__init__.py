"""indicium-adapters — shared domain knowledge layer for the indicium ecosystem.

Defines the DomainAdapter structural Protocol and the discover_adapters()
entry-point discovery function.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DomainAdapter(Protocol):
    """Structural protocol for domain-specific claim enrichment adapters.

    Third-party implementations do NOT need to import this class.
    Any class that has these four attributes satisfies
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


def discover_adapters() -> dict[str, "DomainAdapter"]:
    """Return all installed DomainAdapters, keyed by domain_id.

    Discovers via the 'indicium.adapters' entry-point group. If two packages
    register the same domain_id, the last one loaded wins (install order).

    Returns an empty dict when no adapters are installed (never raises).
    """
    from importlib.metadata import entry_points

    result: dict[str, DomainAdapter] = {}
    for ep in entry_points(group="indicium.adapters"):
        try:
            adapter: DomainAdapter = ep.load()()
        except Exception:
            # Skip entry-points that fail to load (e.g. class not yet implemented).
            continue
        result[adapter.domain_id] = adapter
    return result


__all__ = ["DomainAdapter", "discover_adapters"]
