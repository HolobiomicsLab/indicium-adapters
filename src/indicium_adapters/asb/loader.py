"""Read a collection directory from disk into Pydantic v2 models.

The on-disk layout is::

    <root>/
        collection.yaml            ← index
        tools/<slug>.yaml          ← tool ledger entries (one per slug)
        skills/<slug>/SKILL.md     ← markdown with YAML frontmatter
        claims.yaml                ← list of claim records (optional)

The loader is the only filesystem reader in the package. Mapper and
adapter code consume ``ASBCollection`` and never touch disk.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from indicium_adapters.asb.models import (
    ASBClaimRecord,
    ASBCollection,
    ASBSkillRecord,
    ASBToolRecord,
)

_FRONTMATTER_FENCE = "---"


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _extract_frontmatter(md_path: Path) -> dict[str, Any]:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith(_FRONTMATTER_FENCE):
        raise ValueError(f"{md_path}: missing YAML frontmatter fence")
    parts = text.split(_FRONTMATTER_FENCE, 2)
    if len(parts) < 3:
        raise ValueError(f"{md_path}: malformed frontmatter")
    raw = yaml.safe_load(parts[1]) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{md_path}: frontmatter must be a mapping")
    # "claims" in the frontmatter is a list of IRI strings; the model
    # field is named ``claim_ids`` to avoid shadowing the ClaimRecord
    # type.
    if "claims" in raw and "claim_ids" not in raw:
        raw["claim_ids"] = raw.pop("claims")
    return raw


def load_collection(root: Path | str) -> ASBCollection:
    """Read a collection directory and return a validated ``ASBCollection``.

    Raises ``FileNotFoundError`` if ``root`` does not exist or
    ``collection.yaml`` is missing. Raises ``ValueError`` (wrapping
    ``pydantic.ValidationError``) if any parsed record fails validation.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise FileNotFoundError(f"collection root not found: {root_path}")

    index_path = root_path / "collection.yaml"
    if not index_path.is_file():
        raise FileNotFoundError(f"missing collection.yaml in {root_path}")
    index = _read_yaml(index_path) or {}

    skills: list[ASBSkillRecord] = []
    for entry in index.get("skills", []):
        md = root_path / entry["path"]
        fm = _extract_frontmatter(md)
        skills.append(ASBSkillRecord.model_validate(fm))

    tools: list[ASBToolRecord] = []
    for entry in index.get("tools", []):
        data = _read_yaml(root_path / entry["path"])
        tools.append(ASBToolRecord.model_validate(data))

    claims: list[ASBClaimRecord] = []
    claims_entry = index.get("claims")
    if claims_entry:
        claims_path_value = (
            claims_entry["path"] if isinstance(claims_entry, dict) else claims_entry
        )
        raw = _read_yaml(root_path / claims_path_value) or []
        for c in raw:
            claims.append(ASBClaimRecord.model_validate(c))

    return ASBCollection(
        collection_iri=index["collection_iri"],
        version=index["version"],
        skills=skills,
        tools=tools,
        claims=claims,
    )


__all__ = ["load_collection"]
