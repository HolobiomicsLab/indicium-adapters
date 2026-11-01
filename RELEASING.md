# Releasing indicium-adapters

The checklist for the first PyPI release, 0.6.0, and the steps that follow it. Run the
steps in order. The state recorded here was measured on 2026-11-01.

| | State on 2026-11-01 |
|---|---|
| Repository `HolobiomicsLab/indicium-adapters` | public; `fix/release-readiness-2026-10-30` was merged as #6 |
| Tags and GitHub releases | tag `v0.4.0`, no release; 0.5.0 was never tagged |
| PyPI and TestPyPI, `indicium-adapters` | 404 (name free) |
| `indicium-standard` 2.0.0 on PyPI | 404; CI keeps a temporary Git pin, while `release.yml` now stops until the PyPI version exists |
| GitHub environments | `pypi` with a tag-only deployment policy (`v*`); the required-reviewer rule is added after the public switch (step 4), the plan refuses it on a private repository |
| History scan (step 1) | private names: 0 over all refs; secret formats: 0 over all refs |
| GitHub Pages | none, and none needed: the repository has no documentation site |

Two steps cannot be undone: pushing the tag (step 6), which starts the PyPI upload, and
the upload itself. PyPI never accepts the same version twice.

## Before you start

`indicium-standard` 2.0.0 must be on PyPI first: until it is, `pip install
indicium-adapters` cannot resolve its dependency. Release indicium, then this package.

On `main`, with this branch merged, in a clean environment that mirrors CI:

```bash
uv venv --python 3.11 /tmp/adapters-check
uv pip install --python /tmp/adapters-check/bin/python --no-sources -e ".[dev,asb]"
/tmp/adapters-check/bin/ruff check .
/tmp/adapters-check/bin/pytest -q
/tmp/adapters-check/bin/python scripts/check_release.py --tag v0.6.0 --allow-unreleased
gh run list -R HolobiomicsLab/indicium-adapters --workflow ci.yml -L 1
```

Expected: `All checks passed!`; pytest reports no failure; `Release metadata verified
for v0.6.0`; the last CI run on `main` shows `success`.

## 1. Scan the history, then make the repository public

Every branch, tag and pull-request ref (`refs/pull/<n>/head`) becomes public. A
pull-request ref stays readable after its branch is deleted; only GitHub Support can
purge it. Delete the branches you do not want published, then scan a fresh mirror.

The private names are kept, one extended regular expression per line, in
`secrets/redaction-patterns.txt` of the maintainers' private hub. Set `PATTERNS` to
that file's path on your machine:

```bash
gh repo clone HolobiomicsLab/indicium-adapters adapters-audit.git -- --mirror
cd adapters-audit.git
PATTERNS=/path/to/secrets/redaction-patterns.txt
SECRETS='\b(gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10}|glpat-[A-Za-z0-9_-]{20}|pypi-AgEI[A-Za-z0-9_-]{20}|sk-[A-Za-z0-9_-]{20})|-----BEGIN [A-Z ]*PRIVATE KEY-----'
scan_text() {
  git log --all -p --format='%an %ae %cn %ce%n%B'
  git for-each-ref --format='%(refname) %(taggername) %(contents)'
}
test -s "$PATTERNS" && scan_text | grep -c -i -E -f "$PATTERNS"
scan_text | grep -c -E "$SECRETS"
```

Expected: both counts print `0`. The secret pattern does not match its own text, since
each bracket expression stands where a literal key character would. `test -s` stops
the first count when the pattern file is missing or empty, so an empty result there is
not a pass. If a count is not `0`, list the refs whose history matches, without
printing the matches:

```bash
for ref in $(git for-each-ref --format='%(refname)'); do
  n=$(git log -p --format='%an %ae %cn %ce%n%B' "$ref" | grep -c -i -E -f "$PATTERNS")
  [ "$n" -gt 0 ] && echo "$ref $n"
done
```

Delete every listed branch or tag, ask GitHub Support to purge every listed
`refs/pull/<n>`, and scan a fresh mirror again. Also check that the README and
`CHANGELOG.md` link no private repository. Then:

```bash
gh repo edit HolobiomicsLab/indicium-adapters --visibility public --accept-visibility-change-consequences
gh api repos/HolobiomicsLab/indicium-adapters --jq .visibility
```

Expected: `public`.

## 2. GitHub Pages

Not needed: the repository has no documentation site. The README is the PyPI page.

## 3. Create the PyPI pending publisher

On pypi.org, Account settings > Publishing (`https://pypi.org/manage/account/publishing/`)
> "Add a new pending publisher" > GitHub:

| Field | Value |
|---|---|
| PyPI Project Name | `indicium-adapters` |
| Owner | `HolobiomicsLab` |
| Repository name | `indicium-adapters` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Expected: the publisher is listed under "Pending publishers". No API token is created.

## 4. Check the GitHub environment `pypi`

```bash
gh api repos/HolobiomicsLab/indicium-adapters/environments --jq '.environments[].name'
gh api repos/HolobiomicsLab/indicium-adapters/environments/pypi/deployment-branch-policies --jq '.branch_policies[] | .name + " " + .type'
```

Expected: `pypi` and `v* tag`. Once the repository is public, make every upload wait for
your approval:

```bash
echo '{"reviewers":[{"type":"User","id":22830047}],"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}' | gh api -X PUT repos/HolobiomicsLab/indicium-adapters/environments/pypi --input -
```

Expected: the response lists one required reviewer.

## 5. Finish the dependency transition after the upload

Do this immediately after `indicium-standard` 2.0.0 appears on PyPI and before
tagging this repository:

1. Confirm `https://pypi.org/pypi/indicium-standard/2.0.0/json` returns 200.
   `release.yml` now makes this a hard gate, resolves the test environment from
   PyPI and installs the built wheel with its dependencies in a clean environment.
2. Remove the temporary `indicium-standard @ git+...` install from
   `.github/workflows/ci.yml`. The editable project install then resolves
   `indicium-standard>=2.0.0` from the index, matching public installations.
3. Remove `[tool.uv.sources]` from `pyproject.toml` and run `uv lock`. The sibling
   path exists for contributors with both checkouts; a lone public clone uses
   `uv sync --no-sources` until this lock refresh is committed.
4. Delete the repository secret `ORG_PAT`, which nothing uses any more.

The CI pin, uv source and lock remain unchanged in this preparation branch so CI
can stay green before the dependency upload. The release tag waits for this
follow-up to be merged.

## 6. Date the changelog, tag v0.6.0 and push the tag

The `## [0.6.0]` heading of `CHANGELOG.md` carries the placeholder `YYYY-MM-DD`, which
`scripts/check_release.py` rejects without `--allow-unreleased`. Replace only the
placeholder with the release date, then:

```bash
python scripts/check_release.py --tag v0.6.0
git commit -am "chore(release): date 0.6.0"
git push origin main
```

Expected: `Release metadata verified for v0.6.0`. Once CI on `main` is green:

```bash
git switch main && git pull --ff-only
git tag -a v0.6.0 -m "indicium-adapters 0.6.0"
git push origin v0.6.0
gh run watch -R HolobiomicsLab/indicium-adapters \
  "$(gh run list -R HolobiomicsLab/indicium-adapters --workflow release.yml -L 1 --json databaseId --jq '.[0].databaseId')"
```

Expected: job `build` checks the tag, the versions and the changelog date, runs lint
and tests, builds the sdist and the wheel, runs `twine check --strict` and imports the
installed wheel; job `publish` uploads to PyPI (after your approval, if step 4 set a
reviewer); job `github-release` creates the GitHub release. All three end green.

- If job `build` fails, nothing is published. Fix the cause, delete the tag on the
  remote and locally, and tag again.
- If job `publish` fails, for example on a mistyped publisher field, correct the
  publisher on PyPI and re-run the failed job: `gh run rerun <run-id> --failed`.
- If only job `github-release` fails, PyPI already has the version; re-run that job.

## 7. Verify the release

```bash
gh release view v0.6.0 -R HolobiomicsLab/indicium-adapters --json assets --jq '.assets[].name'
uv venv --python 3.11 /tmp/adapters-release
uv pip install --python /tmp/adapters-release/bin/python "indicium-adapters==0.6.0"
/tmp/adapters-release/bin/python -c "import indicium_adapters; from importlib.metadata import version; print(version('indicium-adapters'))"
```

Expected: `indicium_adapters-0.6.0-py3-none-any.whl` and `indicium_adapters-0.6.0.tar.gz`;
then `0.6.0`. The page `https://pypi.org/project/indicium-adapters/` shows 0.6.0.

## Later versions

A version lives in two files, `version` in `pyproject.toml` and `version:` in
`CITATION.cff`, and in a `CHANGELOG.md` section `## [X.Y.Z] - YYYY-MM-DD`.
`tests/test_release_metadata.py` fails while they disagree. Update the supported line in
`SECURITY.md` on a minor bump. Then run "Before you start" and steps 6 and 7.
