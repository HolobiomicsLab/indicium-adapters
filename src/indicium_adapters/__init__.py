"""indicium-adapters — shared domain knowledge layer for the indicium ecosystem.

Defines the DomainAdapter structural Protocol, the SHACLProvider and
ClassificationVocabularyProvider opt-in mixins, and the discover_adapters()
entry-point discovery function.

An adapter package is the ONE legitimate home for domain-specific vocabulary:
qualifiers, ontology prefixes, and the classification terms declared through
ClassificationVocabularyProvider. This package holds the mechanism only and
names no science anywhere — consumers must read declarations off the adapter,
never branch on a domain name.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

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

    ``primary_domain`` / ``subdomains`` / ``techniques`` are OPTIONAL members
    documented on :class:`ClassificationVocabularyProvider`. They are declared
    there, not here, on purpose: a runtime-checkable Protocol has no notion of
    an optional member, so listing them above would make every adapter that
    omits them fail ``isinstance(obj, DomainAdapter)``. Read them with
    :func:`classification_vocabulary`.
    """

    domain_id: str
    """Unique identifier, lowercase, hyphen-separated. e.g. "metabolomics"."""

    qualifiers: frozenset[str]
    """Domain-specific qualifiers, unioned into Perspicacité's LLM extraction
    prompt alongside the base 20-term Bucur set.

    Each value MUST be snake_case matching ``^[a-z][a-z0-9_]*$`` — at RDF time
    Perspicacité routes any qualifier that is NOT one of the closed Bucur
    SuperPattern terms onto the open ``asb:domainQualifier`` slot (a domain term
    that happens to equal a Bucur term, e.g. ``interacts_with``, rides the closed
    ``asb:qualifier`` instead). This keeps the published Bucur enum pristine while
    letting domain vocabularies validate; see indicium#1 / indicium 1.7.0. Any
    SHACL shape this adapter ships for a domain qualifier must therefore key on
    ``asb:domainQualifier``, not ``asb:qualifier``."""

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
        e.g. ``{"subject": "CHEBI:14321"}``. Must be a pure function (no I/O).

        **Optional companion map — ontology_term_justifications**

        An adapter MAY also set ``ontology_term_justifications: dict[str, str]``
        on the returned claim, using the same slot keys as ``ontology_terms``
        (e.g. ``"subject"``, ``"object"``).  Each value is a SEMAPV justification
        CURIE that describes *how* the ontology term was resolved, for example:

        * ``semapv:CompositeMatching``  — curated / rule-based identifier lookup
        * ``semapv:LexicalMatching``    — name or synonym string match
        * ``semapv:ManualMappingCuration`` — hand-curated assignment

        Downstream SSSOM emitters (e.g. Perspicacité) turn ``ontology_terms``
        into first-class ``sssom:MappingSet`` rows and use
        ``ontology_term_justifications`` as the ``mapping_justification``
        predicate value.  When the key is absent the emitter defaults to
        ``semapv:CompositeMatching``."""
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


@runtime_checkable
class ClassificationVocabularyProvider(DomainAdapter, Protocol):
    """Optional mixin: adapters that declare curated classification vocabulary.

    Implement this in addition to DomainAdapter to say which SCIENCE the adapter
    serves and which terms belong to it. All three members are CURATED by a
    domain expert and versioned with the adapter — declarations, never data
    derived from a corpus, a tool registry or a model.

    Declaring nothing is legitimate: an ancillary adapter (a knowledge-graph or
    infrastructure helper) serves no science of its own and must stay silent
    rather than inject its own name as one.

    Consumers read the triple through :func:`classification_vocabulary` and
    treat every term as opaque; the consuming mechanism stays domain-neutral.
    """

    primary_domain: str
    """The science this adapter serves — the field a paper would be filed under.

    SEVERAL adapters MAY share one ``primary_domain``: variants of a single
    science (differing in assay, scale or platform) declare the same value, so
    the science enters the vocabulary once and the variants do not surface as
    top-level sciences.

    Distinct from ``domain_id``, which remains the adapter's OWN identity — one
    per installed package, and the discover_adapters() key. A consumer that
    falls back to ``domain_id`` when ``primary_domain`` is missing publishes an
    adapter name as though it were a science; declare ``primary_domain``
    instead of relying on such a fallback."""

    subdomains: tuple[str, ...]
    """Curated sub-fields OF ``primary_domain``, one granularity below it.

    Kebab-case terms. A subdomain narrows the science; it never names another
    science, and never names a technique."""

    techniques: tuple[str, ...]
    """Curated experimental or analytical techniques used within the science.

    Kebab-case terms naming HOW work is done (instruments, assays, methods),
    as opposed to WHAT is studied."""


@dataclass(frozen=True)
class ClassificationVocabulary:
    """What one adapter declares for classification, reported honestly.

    ``primary_domain is None`` is the explicit "this adapter declared no
    science" status. It is NOT a licence to substitute the adapter's
    ``domain_id``, and it is not the same as an adapter that declared one.
    """

    primary_domain: str | None
    subdomains: tuple[str, ...]
    techniques: tuple[str, ...]


def _declared_terms(declared: object, member: str) -> tuple[str, ...]:
    """Normalise one declared term collection to a tuple of strings."""
    if not declared:
        return ()
    if isinstance(declared, str):
        raise TypeError(f"{member} must be a collection of terms, not a str")
    return tuple(str(term) for term in declared)


def classification_vocabulary(adapter: DomainAdapter) -> ClassificationVocabulary:
    """Read the classification vocabulary an adapter declares, if any.

    Domain-neutral: reads the declaration off the adapter, invents no terms,
    and never substitutes ``domain_id`` for an absent ``primary_domain``.
    Raises TypeError if a term collection is declared as a bare string.
    """
    primary = getattr(adapter, "primary_domain", None)
    return ClassificationVocabulary(
        primary_domain=str(primary) if primary else None,
        subdomains=_declared_terms(getattr(adapter, "subdomains", None), "subdomains"),
        techniques=_declared_terms(getattr(adapter, "techniques", None), "techniques"),
    )


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
    "CURRENT_API_VERSION",
    "ASBAdapter",
    "ClassificationVocabulary",
    "ClassificationVocabularyProvider",
    "CompositeAdapter",
    "DomainAdapter",
    "SHACLProvider",
    "classification_vocabulary",
    "compose_adapters",
    "discover_adapters",
]


if __name__ == "__main__":  # offline smoke check
    class _Probe:
        """Five-member adapter that declares no classification vocabulary."""

        domain_id = "probe-adapter"
        qualifiers = frozenset()
        ontology_prefixes: ClassVar[dict[str, str]] = {}
        api_version = CURRENT_API_VERSION

        def extraction_context(self) -> str:
            return ""

        def enrich_claim(self, claim: dict) -> dict:
            return dict(claim)

    _probe = _Probe()
    assert isinstance(_probe, DomainAdapter)
    assert not isinstance(_probe, ClassificationVocabularyProvider)
    _vocab = classification_vocabulary(_probe)
    assert _vocab.primary_domain is None
    assert _vocab.subdomains == () and _vocab.techniques == ()
    print("indicium_adapters smoke: ok")
