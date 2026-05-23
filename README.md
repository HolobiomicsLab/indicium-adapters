# indicium-adapters

Community-extensible domain adapters for the [indicium](../indicium) knowledge standard.

## Install (local dev)

```bash
cd ~/git/indicium-adapters
uv sync --extra dev
```

## Usage

```python
from indicium_adapters import discover_adapters

adapters = discover_adapters()
metabolomics = adapters["metabolomics"]
enriched = metabolomics.enrich_claim({"subject": "glucose", "object": "brain", ...})
```

## Adding a third-party adapter

1. Implement the `DomainAdapter` structural Protocol (no import needed).
2. Register via `pyproject.toml`:

```toml
[project.entry-points."indicium.adapters"]
my_domain = "my_package.adapters:MyAdapter"
```
