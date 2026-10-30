"""Pydantic v2 models that mirror on-disk ASB-Skill collection artifacts.

These models are deliberately decoupled from the Python dataclasses in
``asb-domain-core`` (``SciSkill`` / ``ASBSkill``, ``SciTool`` / ``ASBTool``).
The adapter reads YAML / Markdown frontmatter / JSON files written by ASB
release builds; the rename in Wave 2 does not affect us.
"""
from __future__ import annotations

from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

_MODEL_CONFIG = ConfigDict(
    extra="ignore",          # tolerate forward-compatible additions
    str_strip_whitespace=True,
    frozen=False,
)


# Current releases write a record's papers under ``derived_from``.
_SOURCE_PAPERS_KEYS = AliasChoices("source_papers", "derived_from")


class ASBEvidenceSpan(BaseModel):
    """A verbatim quotation supporting a skill or claim."""

    model_config = _MODEL_CONFIG

    quote: str = Field(min_length=1)
    eco_code: str = "eco:textual-quotation"
    source_doi: str | None = None
    paragraph_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_plain_quote(cls, value: Any) -> Any:
        """Accept a bare string, the form current releases write a span in."""
        return {"quote": value} if isinstance(value, str) else value


class ASBSourcePaper(BaseModel):
    """A paper that contributed to a skill / tool / claim."""

    model_config = _MODEL_CONFIG

    doi: str = Field(min_length=1)
    # Empty when the release could not resolve the title; the DOI identifies.
    title: str = ""

    @field_validator("doi", mode="before")
    @classmethod
    def _strip_doi_url(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        v = value.strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if v.lower().startswith(prefix):
                v = v[len(prefix):]
                break
        if not v:
            raise ValueError("doi must not be empty after normalisation")
        return v


class ASBToolRecord(BaseModel):
    """An entry from ``tools/<slug>.yaml``."""

    model_config = _MODEL_CONFIG

    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    canonical_url: str | None = None
    bio_tools_id: str | None = None
    edam_operation: str = ""
    edam_topics: list[str] = Field(default_factory=list)
    evidence_spans: list[ASBEvidenceSpan] = Field(default_factory=list)
    source_papers: list[ASBSourcePaper] = Field(
        default_factory=list, validation_alias=_SOURCE_PAPERS_KEYS
    )


class ASBClaimRecord(BaseModel):
    """A Bucur 5-slot SuperPattern claim extracted from passages."""

    model_config = _MODEL_CONFIG

    claim_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    qualifiers: list[str] = Field(default_factory=list)
    super_pattern: str | None = None
    evidence_spans: list[ASBEvidenceSpan] = Field(default_factory=list)
    source_papers: list[ASBSourcePaper] = Field(
        default_factory=list, validation_alias=_SOURCE_PAPERS_KEYS
    )


class ASBSkillRecord(BaseModel):
    """Frontmatter parsed from a SKILL.md plus its companion records."""

    model_config = _MODEL_CONFIG

    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    when_to_use: str = ""
    edam_operation: str = ""
    edam_topics: list[str] = Field(default_factory=list)
    related_tools: list[str] = Field(default_factory=list)
    evidence_spans: list[ASBEvidenceSpan] = Field(default_factory=list)
    source_papers: list[ASBSourcePaper] = Field(
        default_factory=list, validation_alias=_SOURCE_PAPERS_KEYS
    )
    claim_ids: list[str] = Field(default_factory=list)


class ASBCollection(BaseModel):
    """The parsed shape of one ``collections/<name>/<version>/`` directory."""

    model_config = _MODEL_CONFIG

    collection_iri: str = Field(min_length=1)
    version: str = Field(min_length=1)
    skills: list[ASBSkillRecord] = Field(default_factory=list)
    tools: list[ASBToolRecord] = Field(default_factory=list)
    claims: list[ASBClaimRecord] = Field(default_factory=list)


__all__ = [
    "ASBClaimRecord",
    "ASBCollection",
    "ASBEvidenceSpan",
    "ASBSkillRecord",
    "ASBSourcePaper",
    "ASBToolRecord",
]
