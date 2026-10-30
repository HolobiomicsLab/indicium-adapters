"""Round-trip CI gate: every claim IRI a SKILL.md lists must resolve in indicium.

Called by ``asb-skill-collections`` release CI before a new collection is
tagged. Given a collection directory and an indicium graph (Turtle / JSON-LD
already parsed into rdflib), checks that every claim IRI listed in a
SKILL.md frontmatter appears as a subject typed with indicium's Claim class
(``asb:Claim``, read from ``indicium.ASB_BASE``). A dangling IRI, or a
listed skill the loader could not read, is a release blocker. The claim
IRIs of a skill that failed validation are still checked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

from indicium_adapters.asb.loader import load_collection
from indicium_adapters.asb.mapper import ASB_VOCAB
from indicium_adapters.asb.models import ASBSkippedSkill


@dataclass(frozen=True)
class UnresolvedClaim:
    """One dangling SKILL.md → indicium claim reference."""

    skill_slug: str
    claim_iri: str


@dataclass
class RoundTripResult:
    """Outcome of a single round-trip check."""

    ok: bool
    unresolved: list[UnresolvedClaim] = field(default_factory=list)
    resolved_count: int = 0
    # Skills read from disk: shows a pass that checked nothing.
    skills_checked: int = 0
    # Entries under ``skills`` in collection.yaml.
    skills_listed: int = 0
    # Listed skills the loader could not read; each blocks the release.
    skills_skipped: list[ASBSkippedSkill] = field(default_factory=list)
    # Skills declaring n_claims above 0 while listing no claim IRI.
    skills_with_unlisted_claims: int = 0

    def render(self) -> str:
        """Return the report ``verify-claims`` prints in its pretty format."""
        if self.ok:
            return (
                f"OK - {self.resolved_count} claim(s) resolved "
                f"in {self.skills_checked} skill(s); "
                f"{self.skills_listed} listed, {len(self.skills_skipped)} skipped."
            )
        lines = []
        if self.unresolved:
            lines.append(f"FAIL - {len(self.unresolved)} dangling claim URI(s):")
            lines.extend(f"  - {u.skill_slug}: {u.claim_iri}" for u in self.unresolved)
        if self.skills_skipped:
            lines.append(
                f"FAIL - {len(self.skills_skipped)} of {self.skills_listed} "
                "listed skill(s) skipped:"
            )
            lines.extend(f"  - {s.slug}: {s.reason}" for s in self.skills_skipped)
        return "\n".join(lines)


def run_round_trip_check(
    collection_dir: Path | str,
    indicium_graph: rdflib.Graph,
    fail_on_missing: bool = False,
) -> RoundTripResult:
    """Check every listed claim IRI; report or raise on a dangling or skipped one.

    The claim IRIs of read skills and of skills skipped for failing
    validation are checked alike. ``fail_on_missing=True`` raises
    ``AssertionError`` with the rendered report when the result is not
    ok. Otherwise returns a ``RoundTripResult`` and lets the caller decide.
    """
    coll = load_collection(collection_dir)
    known_claims = {
        str(s)
        for s, _, _ in indicium_graph.triples((None, RDF.type, ASB_VOCAB.Claim))
    }
    listed = [(s.slug, s.claim_ids) for s in [*coll.skills, *coll.skipped_skills]]
    unresolved = [
        UnresolvedClaim(skill_slug=slug, claim_iri=iri)
        for slug, iris in listed
        for iri in iris
        if iri not in known_claims
    ]
    result = RoundTripResult(
        ok=not unresolved and not coll.skipped_skills,
        unresolved=unresolved,
        resolved_count=sum(len(iris) for _, iris in listed) - len(unresolved),
        skills_checked=len(coll.skills),
        skills_listed=len(listed),
        skills_skipped=coll.skipped_skills,
        skills_with_unlisted_claims=sum(
            1 for s in coll.skills if (s.n_claims or 0) > 0 and not s.claim_ids
        ),
    )
    if fail_on_missing and not result.ok:
        raise AssertionError(result.render())
    return result


__all__ = ["RoundTripResult", "UnresolvedClaim", "run_round_trip_check"]
