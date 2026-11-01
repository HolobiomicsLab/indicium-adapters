"""The installed CLI explains how to enable its optional ASB support."""
from __future__ import annotations

import subprocess
import sys


def test_cli_imports_without_optional_dependencies_and_exits_with_hint() -> None:
    script = """
import sys

sys.modules["httpx"] = None
sys.modules["yaml"] = None

from indicium_adapters.asb import cli

print("module imported")
raise SystemExit(
    cli.main(["--collection", "unused", "--indicium-graph", "unused"])
)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == "module imported\n"
    assert result.stderr == (
        'error: missing ASB dependencies; install with '
        'pip install "indicium-adapters[asb]"\n'
    )
