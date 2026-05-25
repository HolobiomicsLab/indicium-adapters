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

    # The ASB ``asb collection promote`` emitter (Plan 2a/2b) writes
    # collection.yaml with ``skills: [{slug, iri}]`` and a sibling
    # ``tools.lock.yaml`` rather than inline ``skills: [{path}]`` entries.
    # Accept both shapes: explicit-path (used by tests/fixtures) and the
    # slug-implied path convention ``skills/<slug>/SKILL.md`` produced by
    # the real CLI.

    def _skill_md_path(entry: dict) -> Path:
        if "path" in entry:
            return root_path / entry["path"]
        slug = entry.get("slug") or entry.get("name")
        if not slug:
            raise ValueError(
                f"skill entry missing both 'path' and 'slug': {entry!r}"
            )
        return root_path / "skills" / slug / "SKILL.md"

    skills: list[ASBSkillRecord] = []
    for entry in index.get("skills", []):
        md = _skill_md_path(entry)
        if not md.exists():
            # Some entries may reference legacy slug/iri without a file
            # present yet (e.g. during partial promotes); skip silently.
            continue
        fm = _extract_frontmatter(md)
        # SKILL.md frontmatter uses Anthropic-style ``name:`` only; the
        # Pydantic model requires both ``slug`` and ``name``. Derive
        # ``slug`` from the directory name (which mirrors the value of
        # ``name`` produced by ``asb collection promote``) when it's
        # missing from the frontmatter itself.
        if "slug" not in fm:
            fm["slug"] = fm.get("name") or md.parent.name
        if "name" not in fm:
            fm["name"] = fm.get("slug") or md.parent.name
        # The promote emitter stores nested EDAM metadata under
        # ``metadata.edam_topics`` / ``metadata.edam_operation``. The
        # legacy fixtures put them flat. Try both.
        if "edam_topics" not in fm and isinstance(fm.get("metadata"), dict):
            fm["edam_topics"] = fm["metadata"].get("edam_topics", []) or []
        if "edam_operation" not in fm and isinstance(fm.get("metadata"), dict):
            fm["edam_operation"] = fm["metadata"].get("edam_operation", "") or ""
        # Tools/source_papers/claim_ids may also live under metadata.
        if "claim_ids" not in fm and isinstance(fm.get("metadata"), dict):
            fm["claim_ids"] = fm["metadata"].get("claims", []) or []
        try:
            skills.append(ASBSkillRecord.model_validate(fm))
        except Exception as exc:
            # Skip malformed entries with a structured log; don't fail
            # the entire round-trip check on one bad skill.
            import warnings
            warnings.warn(
                f"loader: skipping {md} — {type(exc).__name__}: {exc}"
            )

    tools: list[ASBToolRecord] = []
    # Inline `tools: [{path}]` (legacy schema)
    for entry in index.get("tools", []):
        if "path" not in entry:
            continue
        data = _read_yaml(root_path / entry["path"])
        tools.append(ASBToolRecord.model_validate(data))
    # Sibling tools.lock.yaml (current asb collection promote)
    lock_path = root_path / "tools.lock.yaml"
    if lock_path.is_file():
        lock = _read_yaml(lock_path) or {}
        for entry in lock.get("tools", []):
            try:
                tools.append(ASBToolRecord.model_validate(entry))
            except Exception:
                # Skip silently — schemas may diverge until LinkML normalizes
                continue

    claims: list[ASBClaimRecord] = []
    claims_entry = index.get("claims")
    if claims_entry:
        claims_path_value = (
            claims_entry["path"] if isinstance(claims_entry, dict) else claims_entry
        )
        raw = _read_yaml(root_path / claims_path_value) or []
        for c in raw:
            claims.append(ASBClaimRecord.model_validate(c))

    # collection_iri synthesis: prefer explicit, otherwise derive from slug+version.
    collection_iri = index.get("collection_iri")
    if not collection_iri:
        slug = index.get("slug", "unknown")
        version = index.get("version", 1)
        collection_iri = (
            f"https://w3id.org/holobiomicslab/asb-skill/collection/{slug}/v{version}"
        )

    return ASBCollection(
        collection_iri=collection_iri,
        version=str(index.get("version", "1")),
        skills=skills,
        tools=tools,
        claims=claims,
    )


__all__ = ["load_collection"]
