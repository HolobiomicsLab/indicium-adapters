"""Console entry point for the ASB → indicium round-trip verifier.

Designed to be called by ``asb-skill-collections`` CI as a release-blocking
gate. Exits 0 when every ``metadata.claims`` URI in every SKILL.md resolves
in the supplied indicium graph; exits 1 (with diagnostics on stdout) when
any URI dangles.

## CI integration contract

``asb-skill-collections`` CI calls this script as:

    pip install indicium-adapters
    verify-claims --collection <path-to-collection> \\
                  --indicium-graph <path-to-graph.ttl> \\
                  --format json

Exit codes:
- 0: all claim URIs resolve; release may proceed.
- 1: one or more URIs dangle; release blocked. JSON stdout lists them.
- 2: invocation error (missing file, bad args).

JSON stdout carries ``unresolved`` (``skill_slug`` and ``claim_iri`` per
dangling reference), ``resolved_count`` and ``skills_checked``, the number
of skills read from disk. A pass with ``skills_checked`` at 0 checked
nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rdflib import Graph

from indicium_adapters.asb.round_trip import run_round_trip_check


def _load_graph(path: Path) -> Graph:
    g = Graph()
    g.parse(str(path), format="turtle")
    return g


def _emit_pretty(result) -> None:
    if result.unresolved:
        print(f"FAIL - {len(result.unresolved)} dangling claim URI(s):")
        for uri in result.unresolved:
            print(f"  - {uri}")
    else:
        print(
            f"OK - {result.resolved_count} claim(s) resolved "
            f"in {result.skills_checked} skill(s)."
        )


def _emit_json(result) -> None:
    json.dump(
        {
            "unresolved": [
                {"skill_slug": u.skill_slug, "claim_iri": u.claim_iri}
                for u in result.unresolved
            ],
            "resolved_count": result.resolved_count,
            "skills_checked": result.skills_checked,
        },
        sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify-claims",
        description=(
            "Verify that every metadata.claims URI in every SKILL.md of "
            "an ASB-Skill collection resolves in an indicium graph. "
            "Release-blocking CI gate for asb-skill-collections."
        ),
    )
    parser.add_argument(
        "--collection", required=True, type=Path,
        help="Path to the ASB-Skill collection directory (must contain "
             "collection.yaml + skills/<slug>/SKILL.md files).",
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
        _emit_pretty(result)

    return 1 if result.unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
