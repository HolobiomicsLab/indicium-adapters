"""Check a release tag, version and changelog before building or publishing."""

import argparse
import datetime
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = "indicium-adapters"


def release_notes(root, tag, allow_unreleased=False):
    """Return the notes of the tagged version; reject a mismatch or an undated release."""
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    if project["name"] != DIST or tag != f"v{version}":
        raise ValueError(f"Expected {DIST} tag v{version}; got {tag}")
    cff = (root / "CITATION.cff").read_text(encoding="utf-8")
    cited = re.search(r"^version:\s*\"?([^\"\n]+?)\"?\s*$", cff, re.MULTILINE)
    if cited is None or cited.group(1) != version:
        raise ValueError(f"CITATION.cff version is not {version}")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = re.search(rf"^## \[{re.escape(version)}\] - (\S+)\s*$", changelog, re.MULTILINE)
    if heading is None:
        raise ValueError(f"No changelog section '## [{version}] - <date>'")
    date = heading.group(1)
    if date != "YYYY-MM-DD" or not allow_unreleased:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise ValueError(f"Changelog date for {version} is not a date: {date}") from None
    notes = changelog[heading.end():].split("\n## ", 1)[0].strip().rstrip("-\n").strip()
    if not notes:
        raise ValueError("Release notes are empty")
    return notes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--allow-unreleased", action="store_true", help="Preparation only: allow the date placeholder"
    )
    parser.add_argument("--notes-output", type=Path)
    args = parser.parse_args()
    try:
        notes = release_notes(ROOT, args.tag, args.allow_unreleased)
    except ValueError as error:
        parser.exit(1, f"Release check failed: {error}\n")
    if args.notes_output:
        args.notes_output.write_text(notes + "\n", encoding="utf-8")
    print(f"Release metadata verified for {args.tag}")
