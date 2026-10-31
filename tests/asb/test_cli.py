"""Tests for the verify-claims console script."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "sample_collection"
GRAPH_OK = Path(__file__).parent / "fixtures" / "indicium_graph.ttl"
GRAPH_BROKEN = Path(__file__).parent / "fixtures" / "indicium_graph_broken.ttl"


def test_cli_exits_zero_when_all_claims_resolve() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(FIXTURE),
         "--indicium-graph", str(GRAPH_OK),
         "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["unresolved"] == []
    assert payload["resolved_count"] >= 1


def test_cli_exits_nonzero_when_a_claim_dangles() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(FIXTURE),
         "--indicium-graph", str(GRAPH_BROKEN),
         "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["unresolved"]


def test_cli_pretty_format_is_human_readable() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(FIXTURE),
         "--indicium-graph", str(GRAPH_OK)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "resolved" in result.stdout.lower()


SLUG_LIST = Path(__file__).parent / "fixtures" / "slug_list_collection"


def test_cli_reports_skills_checked_on_slug_list_collection() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(SLUG_LIST),
         "--indicium-graph", str(GRAPH_OK),
         "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "unresolved": [],
        "resolved_count": 1,
        "skills_listed": 2,
        "skills_checked": 2,
        "skills_skipped": [],
        "skills_with_unlisted_claims": 0,
        "shape_targeted_nodes": 2,
    }


def test_cli_pretty_format_names_skills_checked() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(SLUG_LIST),
         "--indicium-graph", str(GRAPH_OK)],
        capture_output=True, text=True, check=False,
    )
    assert result.stdout.strip() == (
        "OK - 1 claim(s) resolved in 2 skill(s); 2 listed, 0 skipped."
    )


def test_cli_pretty_format_lists_dangling_claims_by_slug_and_iri() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(SLUG_LIST),
         "--indicium-graph", str(GRAPH_BROKEN)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    claim = "https://w3id.org/holobiomicslab/asb-skill/skill-with-claim/claim/01"
    assert result.stdout.splitlines() == [
        "FAIL - 1 dangling claim URI(s):",
        f"  - skill-with-claim: {claim}",
        (
            "FAIL - the indicium graph types no node with a class an indicium "
            "SHACL shape targets; validating it would check nothing."
        ),
    ]


SKIPPED = Path(__file__).parent / "fixtures" / "skipped_skill_collection"
UNLISTED = Path(__file__).parent / "fixtures" / "unlisted_claims_collection"
SKIPPED_CLAIM = (
    "https://w3id.org/holobiomicslab/asb-skill/"
    "skill-with-claim-and-empty-span/claim/02"
)


def test_cli_exits_nonzero_on_a_skill_that_fails_validation() -> None:
    """The gate fails closed: a skipped skill blocks, its dangling claim shows."""
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(SKIPPED),
         "--indicium-graph", str(GRAPH_OK),
         "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["unresolved"] == [
        {"skill_slug": "skill-with-claim-and-empty-span", "claim_iri": SKIPPED_CLAIM}
    ]
    assert payload["skills_listed"] == 2
    assert payload["skills_checked"] == 0
    assert payload["skills_skipped"] == [
        {
            "skill_slug": "skill-with-claim-and-empty-span",
            "reason": "evidence_spans.0.quote: String should have at least 1 character",
        },
        {"skill_slug": "listed-but-not-promoted", "reason": "SKILL.md not found"},
    ]


def test_cli_pretty_format_lists_skipped_skills_by_slug_and_reason() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(SKIPPED),
         "--indicium-graph", str(GRAPH_OK)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "FAIL - 1 dangling claim URI(s):",
        f"  - skill-with-claim-and-empty-span: {SKIPPED_CLAIM}",
        "FAIL - 2 of 2 listed skill(s) skipped:",
        (
            "  - skill-with-claim-and-empty-span: "
            "evidence_spans.0.quote: String should have at least 1 character"
        ),
        "  - listed-but-not-promoted: SKILL.md not found",
    ]


def test_cli_warns_on_skills_that_declare_claims_they_do_not_list() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(UNLISTED),
         "--indicium-graph", str(GRAPH_OK),
         "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["skills_with_unlisted_claims"] == 1
    assert result.stderr.splitlines() == [
        (
            "WARNING - 1 skill(s) declare n_claims above 0 but list no claim IRI; "
            "their claims are not checked."
        )
    ]


def test_cli_exits_nonzero_on_a_graph_no_indicium_shape_targets() -> None:
    """A pass that checked no claim on a graph SHACL would not check is a failure."""
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(UNLISTED),
         "--indicium-graph", str(GRAPH_BROKEN),
         "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["unresolved"] == []
    assert payload["skills_skipped"] == []
    assert payload["shape_targeted_nodes"] == 0
