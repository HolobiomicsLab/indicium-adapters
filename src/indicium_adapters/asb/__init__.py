"""ASB → indicium adapter subpackage.

Maps ASB-Skill collection on-disk artifacts (collection.yaml, SKILL.md
frontmatter, tools/<slug>.yaml) onto indicium RDF triples wrapped in
PROV-O envelopes. Pure file-based — does not import asb-domain-core.
"""
from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

# Read from the installed distribution so it cannot drift from pyproject.
try:
    __version__ = version("indicium-adapters")
except PackageNotFoundError:  # imported from a checkout that is not installed
    __version__ = "0.0.0+unknown"


_EXPORT_MODULES = {
    "ASBAdapter": "indicium_adapters.asb.adapter",
    "ASBClaimRecord": "indicium_adapters.asb.models",
    "ASBCollection": "indicium_adapters.asb.models",
    "ASBEvidenceSpan": "indicium_adapters.asb.models",
    "ASBSkillRecord": "indicium_adapters.asb.models",
    "ASBSourcePaper": "indicium_adapters.asb.models",
    "ASBToolRecord": "indicium_adapters.asb.models",
    "RoundTripResult": "indicium_adapters.asb.round_trip",
    "UnresolvedClaim": "indicium_adapters.asb.round_trip",
    "load_collection": "indicium_adapters.asb.loader",
    "run_round_trip_check": "indicium_adapters.asb.round_trip",
}


def __getattr__(name: str):
    """Load ASB-extra exports only when a caller requests them."""
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    exported = getattr(import_module(module_name), name)
    globals()[name] = exported
    return exported


__all__ = [
    "ASBAdapter",
    "ASBClaimRecord",
    "ASBCollection",
    "ASBEvidenceSpan",
    "ASBSkillRecord",
    "ASBSourcePaper",
    "ASBToolRecord",
    "RoundTripResult",
    "UnresolvedClaim",
    "__version__",
    "load_collection",
    "run_round_trip_check",
]
