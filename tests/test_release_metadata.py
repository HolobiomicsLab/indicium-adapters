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


def test_security_policy_supports_the_declared_minor_line() -> None:
    """SECURITY.md must list the pyproject major.minor line as supported."""
    minor_line = ".".join(_pyproject_version().split(".")[:2])
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    supported = re.findall(r"^\|\s*(\S+)\s*\|\s*yes\s*\|$", security, re.MULTILINE)
    assert supported == [f"{minor_line}.x"]


def test_pyproject_declares_the_readme_as_long_description() -> None:
    """Without it the package index page of the distribution is empty."""
    with (ROOT / "pyproject.toml").open("rb") as fh:
        project = tomllib.load(fh)["project"]
    assert project.get("readme") == "README.md"
    assert (ROOT / "README.md").is_file()
