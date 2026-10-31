# Contributing to indicium-adapters

Thanks for your interest!

## Setup

Clone `indicium` and `indicium-adapters` side by side. `indicium-standard`
is not on PyPI yet, and `[tool.uv.sources]` points it at `../indicium`.

```bash
cd indicium-adapters
uv sync --extra dev --extra asb
```

## Development workflow

1. Create a feature branch from `main`.
2. Write tests first (TDD). The suite is `pytest`.
3. Run `uv run ruff check .` and `uv run pytest` before pushing. CI fails
   on any ruff finding.
4. Open a PR.

## Scope

This package is the Protocol-only core. Domain-specific adapters
(metabolomics, lipidomics, proteomics, ...) live in sibling
`indicium-adapters-<domain>` repositories. Don't add domain enrichment
logic here.

## Bumping CURRENT_API_VERSION

Bumping `CURRENT_API_VERSION` is a coordinated cross-repo release. Plan
it with the maintainers of every `indicium-adapters-*` package; the README
lists the ten known at 0.6.0.
