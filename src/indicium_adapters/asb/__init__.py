"""ASB → indicium adapter subpackage.

Maps ASB-Skill collection on-disk artifacts (collection.yaml, SKILL.md
frontmatter, tools/<slug>.yaml) onto indicium RDF triples wrapped in
PROV-O envelopes. Pure file-based — does not import asb-domain-core.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from indicium_adapters.asb.adapter import ASBAdapter
from indicium_adapters.asb.loader import load_collection
from indicium_adapters.asb.models import (
    ASBClaimRecord,
    ASBCollection,
    ASBEvidenceSpan,
    ASBSkillRecord,
    ASBSourcePaper,
    ASBToolRecord,
)
from indicium_adapters.asb.round_trip import (
    RoundTripResult,
    UnresolvedClaim,
    run_round_trip_check,
)

# Read from the installed distribution so it cannot drift from pyproject.
try:
    __version__ = version("indicium-adapters")
except PackageNotFoundError:  # imported from a checkout that is not installed
    __version__ = "0.0.0+unknown"

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
