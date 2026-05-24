"""ASB → indicium adapter subpackage.

Maps ASB-Skill collection on-disk artifacts (collection.yaml, SKILL.md
frontmatter, tools/<slug>.yaml) onto indicium RDF triples wrapped in
PROV-O envelopes. Pure file-based — does not import asb-domain-core.
"""
from __future__ import annotations

__version__ = "0.5.0"

__all__ = ["__version__"]
