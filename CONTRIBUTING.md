# Contributing to indicium-adapters

Thanks for your interest!

## Setup

```bash
git clone https://github.com/HolobiomicsLab/indicium-adapters
cd indicium-adapters
pip install -e .
pip install pytest pytest-cov ruff
```

## Development workflow

1. Create a feature branch from `main`.
2. Write tests first (TDD). The suite is `pytest`.
3. Run `ruff check . || true` and `pytest` before pushing.
4. Open a PR.

## Scope

This package is the Protocol-only core. Domain-specific adapters
(metabolomics, lipidomics, proteomics, ...) live in sibling
`indicium-adapters-<domain>` repositories. Don't add domain enrichment
logic here.

## Bumping CURRENT_API_VERSION

Bumping `CURRENT_API_VERSION` is a coordinated cross-repo release. Plan
with the maintainers of all known `indicium-adapters-*` consumers
(currently: indicium-adapters-metabolomics).
