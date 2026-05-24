"""ASB → indicium adapter subpackage.

Maps ASB-Skill collection on-disk artifacts (collection.yaml, SKILL.md
frontmatter, tools/<slug>.yaml) onto indicium RDF triples wrapped in
PROV-O envelopes. Pure file-based — does not import asb-domain-core.
"""
from __future__ import annotations

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

__version__ = "0.5.0"

__all__ = [
    "ASBAdapter",
    "ASBClaimRecord",
    "ASBCollection",
    "ASBEvidenceSpan",
    "ASBSkillRecord",
    "ASBSourcePaper",
    "ASBToolRecord",
    "__version__",
    "load_collection",
]
