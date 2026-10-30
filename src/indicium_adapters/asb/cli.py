"""Console entry point for the ASB → indicium round-trip verifier.

Designed to be called by ``asb-skill-collections`` CI as a release-blocking
gate. Exits 0 when every claim IRI a SKILL.md lists (frontmatter
``claims``, or ``metadata.claims``) resolves in the supplied indicium graph
and every listed skill was read; exits 1 (with diagnostics on stdout) when
an IRI dangles or a listed skill was skipped.

## CI integration contract

``asb-skill-collections`` CI calls this script as:

    pip install indicium-adapters
    verify-claims --collection <path-to-collection> \\
                  --indicium-graph <path-to-graph.ttl> \\
                  --format json

Exit codes:
- 0: all claim URIs resolve and every listed skill was read; release may
  proceed.
- 1: one or more URIs dangle, or a listed skill has no SKILL.md or fails
  validation; release blocked. JSON stdout lists them.
- 2: invocation error (missing file, bad args).

JSON stdout carries ``unresolved`` (``skill_slug`` and ``claim_iri`` per
dangling reference), ``resolved_count``, ``skills_listed`` (entries under
``skills`` in collection.yaml), ``skills_checked`` (skills read from disk),
``skills_skipped`` (``skill_slug`` and ``reason`` per skill not read) and
``skills_with_unlisted_claims``. A pass with ``skills_checked`` at 0
checked nothing.

A skill whose frontmatter declares ``n_claims`` above 0 but lists no claim
IRI has nothing to check. Such skills do not fail the gate; their count is
printed as a warning on stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rdflib import Graph

from indicium_adapters.asb.round_trip import RoundTripResult, run_round_trip_check


def _load_graph(path: Path) -> Graph:
    g = Graph()
    g.parse(str(path), format="turtle")
    return g


def _emit_json(result: RoundTripResult) -> None:
    json.dump(
        {
            "unresolved": [
                {"skill_slug": u.skill_slug, "claim_iri": u.claim_iri}
                for u in result.unresolved
            ],
            "resolved_count": result.resolved_count,
            "skills_listed": result.skills_listed,
            "skills_checked": result.skills_checked,
            "skills_skipped": [
                {"skill_slug": s.slug, "reason": s.reason}
                for s in result.skills_skipped
            ],
            "skills_with_unlisted_claims": result.skills_with_unlisted_claims,
        },
        sys.stdout,
    )


def _warn_unlisted_claims(result: RoundTripResult) -> None:
    """Say on stderr how many skills count claims the gate cannot check."""
    if result.skills_with_unlisted_claims:
        print(
            f"WARNING - {result.skills_with_unlisted_claims} skill(s) declare "
            "n_claims above 0 but list no claim IRI; their claims are not checked.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify-claims",
        description=(
            "Verify that every claim IRI listed in a SKILL.md (frontmatter "
            "`claims`, or `metadata.claims`) of an ASB skill collection is "
            "typed asb:Claim in an indicium graph. "
            "Release-blocking CI gate for asb-skill-collections."
        ),
    )
    parser.add_argument(
        "--collection", required=True, type=Path,
        help="Path to the collection directory (collection.yaml plus "
             "leaves/<slug>/SKILL.md, or skills/<slug>/SKILL.md in the "
             "earlier layout).",
    )
    parser.add_argument(
        "--indicium-graph", required=True, type=Path,
        help="Path to the indicium graph fixture (Turtle).",
    )
    parser.add_argument(
        "--format", choices=("pretty", "json"), default="pretty",
        help="Output format. CI should use 'json' for machine parsing.",
    )
    args = parser.parse_args(argv)

    if not args.collection.exists():
        print(f"error: collection not found: {args.collection}", file=sys.stderr)
        return 2
    if not args.indicium_graph.exists():
        print(f"error: graph not found: {args.indicium_graph}", file=sys.stderr)
        return 2

    graph = _load_graph(args.indicium_graph)
    result = run_round_trip_check(args.collection, graph)

    if args.format == "json":
        _emit_json(result)
    else:
        print(result.render())
    _warn_unlisted_claims(result)

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
