"""The version and changelog facts a release reads must agree."""
from __future__ import annotations

import re
import tomllib
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def test_citation_version_matches_pyproject() -> None:
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    declared = re.search(r"^version:\s*\"?([^\"\n]+)\"?$", cff, re.MULTILINE)
    assert declared is not None
    assert declared.group(1) == _pyproject_version()


def test_asb_version_is_the_distribution_version() -> None:
    from indicium_adapters import asb

    assert asb.__version__ == version("indicium-adapters")


def test_changelog_has_one_unreleased_section() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^## \[Unreleased\]", changelog, re.MULTILINE)) == 1
