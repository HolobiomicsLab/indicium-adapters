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
    assert payload == {"unresolved": [], "resolved_count": 1, "skills_checked": 2}


def test_cli_pretty_format_names_skills_checked() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "indicium_adapters.asb.cli",
         "--collection", str(SLUG_LIST),
         "--indicium-graph", str(GRAPH_OK)],
        capture_output=True, text=True, check=False,
    )
    assert result.stdout.strip() == "OK - 1 claim(s) resolved in 2 skill(s)."
