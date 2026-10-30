"""Round-trip CI gate: every ``metadata.claims`` URI must resolve in indicium.

Called by ``asb-skill-collections`` release CI before a new collection is
tagged. Given a collection directory and an indicium graph (Turtle / JSON-LD
already parsed into rdflib), checks that every claim IRI referenced in every
SKILL.md frontmatter appears as a subject typed with indicium's Claim class
(``asb:Claim``, read from ``indicium.ASB_BASE``). Any miss is a release
blocker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

from indicium_adapters.asb.loader import load_collection
from indicium_adapters.asb.mapper import ASB_VOCAB


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

    def render(self) -> str:
        if self.ok:
            return (
                f"round-trip OK - {self.resolved_count} claim(s) resolved "
                f"in {self.skills_checked} skill(s)"
            )
        lines = ["round-trip FAIL - unresolved claim IRIs:"]
        for u in self.unresolved:
            lines.append(f"  - {u.skill_slug}: {u.claim_iri}")
        return "\n".join(lines)


def run_round_trip_check(
    collection_dir: Path | str,
    indicium_graph: rdflib.Graph,
    fail_on_missing: bool = False,
) -> RoundTripResult:
    """Walk every SKILL.md claim IRI; report or raise on dangling refs.

    ``fail_on_missing=True`` raises ``AssertionError`` with the rendered
    report. Otherwise returns a ``RoundTripResult`` and lets the caller
    decide.
    """
    coll = load_collection(collection_dir)
    known_claims = {
        str(s)
        for s, _, _ in indicium_graph.triples((None, RDF.type, ASB_VOCAB.Claim))
    }
    unresolved: list[UnresolvedClaim] = []
    resolved_count = 0
    for skill in coll.skills:
        for claim_iri in skill.claim_ids:
            if claim_iri not in known_claims:
                unresolved.append(
                    UnresolvedClaim(skill_slug=skill.slug, claim_iri=claim_iri)
                )
            else:
                resolved_count += 1
    result = RoundTripResult(
        ok=not unresolved,
        unresolved=unresolved,
        resolved_count=resolved_count,
        skills_checked=len(coll.skills),
    )
    if fail_on_missing and not result.ok:
        raise AssertionError(result.render())
    return result


__all__ = ["RoundTripResult", "UnresolvedClaim", "run_round_trip_check"]
