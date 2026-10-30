"""Read a collection directory from disk into Pydantic v2 models.

Two on-disk layouts are read. Current ASB releases (SKILL.md
``schema_version`` 0.2.0) write::

    <root>/
        collection.yaml            ← index; ``skills`` and ``tools`` list slugs
        leaves/<slug>/SKILL.md     ← one leaf skill per listed slug
        skills/<name>/SKILL.md     ← router skills, not listed in the index
        tools/<slug>.yaml          ← one tool record per listed slug

The earlier layout, kept by the bundled fixture, lists mappings instead::

    <root>/
        collection.yaml            ← index; entries carry ``path`` or ``slug``
        skills/<slug>/SKILL.md     ← markdown with YAML frontmatter
        tools/<slug>.yaml          ← or a sibling tools.lock.yaml
        claims.yaml                ← list of claim records (optional)

The loader is the only filesystem reader in the package. Mapper and
adapter code consume ``ASBCollection`` and never touch disk.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from indicium_adapters.asb.mapper import ASB_SKILL_BASE
from indicium_adapters.asb.models import (
    ASBClaimRecord,
    ASBCollection,
    ASBSkillRecord,
    ASBToolRecord,
)

_FRONTMATTER_FENCE = "---"
# Where a listed slug's SKILL.md may live: current layout first.
_SKILL_DIRS = ("leaves", "skills")
# Index keys that may carry the collection IRI, most specific first.
_COLLECTION_IRI_KEYS = ("collection_iri", "iri", "@id")


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _extract_frontmatter(md_path: Path) -> dict[str, Any]:
    """Parse the YAML block between the first two ``---`` fence lines.

    Only a line that is exactly the fence closes the block, so a value
    that contains ``---`` (a quoted evidence span, say) stays intact.
    The frontmatter key ``claims`` is returned as ``claim_ids``, the
    model's name for the list of claim IRIs.
    """
    lines = md_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].rstrip() != _FRONTMATTER_FENCE:
        raise ValueError(f"{md_path}: missing YAML frontmatter fence")
    closing = [i for i, line in enumerate(lines[1:], 1) if line.rstrip() == _FRONTMATTER_FENCE]
    if not closing:
        raise ValueError(f"{md_path}: malformed frontmatter")
    raw = yaml.safe_load("\n".join(lines[1 : closing[0]])) or {}
    if not isinstance(raw, dict):
        raise TypeError(f"{md_path}: frontmatter must be a mapping")
    if "claims" in raw and "claim_ids" not in raw:
        raw["claim_ids"] = raw.pop("claims") or []
    return raw


def _nested(frontmatter: dict[str, Any], key: str) -> dict[str, Any]:
    value = frontmatter.get(key)
    return value if isinstance(value, dict) else {}


def _normalise_skill_frontmatter(fm: dict[str, Any], dir_name: str) -> dict[str, Any]:
    """Fill the model fields that a SKILL.md keeps elsewhere or omits.

    ``slug`` falls back to ``name``, then to the skill's directory name.
    EDAM terms and claim IRIs fall back to their copies under
    ``metadata``; source papers fall back to ``provenance.source_papers``
    when neither ``source_papers`` nor ``derived_from`` is present.
    Returns ``fm``, updated in place.
    """
    fm.setdefault("slug", fm.get("name") or dir_name)
    fm.setdefault("name", fm["slug"])
    metadata = _nested(fm, "metadata")
    fm.setdefault("edam_topics", metadata.get("edam_topics") or [])
    fm.setdefault("edam_operation", metadata.get("edam_operation") or "")
    fm.setdefault("claim_ids", metadata.get("claims") or [])
    if "source_papers" not in fm and "derived_from" not in fm:
        fm["source_papers"] = _nested(fm, "provenance").get("source_papers") or []
    return fm


def _validate_or_warn(model: type[BaseModel], data: Any, source: object) -> Any:
    """Validate one record; warn and return ``None`` when it does not fit.

    One malformed skill or tool must not hide the rest of the collection
    from the round-trip check, so it is reported and skipped, not raised.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        warnings.warn(f"loader: skipping {source}: {exc}", stacklevel=3)
        return None


def _skill_md_path(root: Path, entry: str | dict[str, Any]) -> Path | None:
    """Return the SKILL.md an index entry points at, or ``None`` if absent.

    A string entry is a slug. A mapping names its file with ``path`` or
    its slug with ``slug`` (or ``name``). A slug resolves to the first
    existing ``<dir>/<slug>/SKILL.md`` over ``_SKILL_DIRS``.
    """
    if isinstance(entry, dict) and "path" in entry:
        return root / entry["path"]
    slug = entry if isinstance(entry, str) else entry.get("slug") or entry.get("name")
    if not slug:
        raise ValueError(f"skill entry missing both 'path' and 'slug': {entry!r}")
    candidates = (root / d / slug / "SKILL.md" for d in _SKILL_DIRS)
    return next((md for md in candidates if md.is_file()), None)


def _load_skills(root: Path, index: dict[str, Any]) -> list[ASBSkillRecord]:
    """Load every listed skill whose SKILL.md exists.

    An entry without a file (a partial promote) is skipped silently.
    """
    skills = []
    for entry in index.get("skills") or []:
        md = _skill_md_path(root, entry)
        if md is None or not md.is_file():
            continue
        fm = _normalise_skill_frontmatter(_extract_frontmatter(md), md.parent.name)
        record = _validate_or_warn(ASBSkillRecord, fm, md)
        if record is not None:
            skills.append(record)
    return skills


def _tool_yaml_path(root: Path, entry: str | dict[str, Any]) -> Path | None:
    """Return where a tool index entry's record lives, or ``None``.

    A string entry is a slug, read from ``tools/<slug>.yaml``. A mapping
    names its file with ``path``; one without ``path`` is described by
    ``tools.lock.yaml`` instead.
    """
    if isinstance(entry, str):
        return root / "tools" / f"{entry}.yaml"
    return root / entry["path"] if "path" in entry else None


def _load_tools(root: Path, index: dict[str, Any]) -> list[ASBToolRecord]:
    """Load the listed tool records, then those of ``tools.lock.yaml``."""
    sources: list[tuple[object, Any]] = []
    for entry in index.get("tools") or []:
        path = _tool_yaml_path(root, entry)
        if path is not None and path.is_file():
            sources.append((path, _read_yaml(path)))
    lock_path = root / "tools.lock.yaml"
    if lock_path.is_file():
        lock = _read_yaml(lock_path) or {}
        sources.extend((lock_path, entry) for entry in lock.get("tools", []))
    tools = (_validate_or_warn(ASBToolRecord, data, src) for src, data in sources)
    return [tool for tool in tools if tool is not None]


def _load_claims(root: Path, index: dict[str, Any]) -> list[ASBClaimRecord]:
    """Load the claim records of an optional ``claims`` file; raise if invalid."""
    claims_entry = index.get("claims")
    if not claims_entry:
        return []
    claims_path = claims_entry["path"] if isinstance(claims_entry, dict) else claims_entry
    raw = _read_yaml(root / claims_path) or []
    return [ASBClaimRecord.model_validate(c) for c in raw]


def _collection_iri(index: dict[str, Any]) -> str:
    """Return the IRI the index declares, else the one ASB would mint."""
    declared = next((index[k] for k in _COLLECTION_IRI_KEYS if index.get(k)), None)
    if declared:
        return str(declared)
    slug = index.get("slug", "unknown")
    return f"{ASB_SKILL_BASE}collection/{slug}/v{index.get('version', 1)}"


def load_collection(root: Path | str) -> ASBCollection:
    """Read a collection directory and return a validated ``ASBCollection``.

    Raises ``FileNotFoundError`` if ``root`` does not exist or
    ``collection.yaml`` is missing, and ``pydantic.ValidationError`` if a
    claim record is invalid. A skill or tool record that fails
    validation is skipped with a warning.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise FileNotFoundError(f"collection root not found: {root_path}")
    index_path = root_path / "collection.yaml"
    if not index_path.is_file():
        raise FileNotFoundError(f"missing collection.yaml in {root_path}")
    index = _read_yaml(index_path) or {}
    return ASBCollection(
        collection_iri=_collection_iri(index),
        version=str(index.get("version", "1")),
        skills=_load_skills(root_path, index),
        tools=_load_tools(root_path, index),
        claims=_load_claims(root_path, index),
    )


__all__ = ["load_collection"]
