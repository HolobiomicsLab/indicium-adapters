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

## Claim-enrichment contract

`enrich_claim()` receives a 5-slot claim dict and returns an enriched copy.
Adapters may add an `"ontology_terms"` sub-dict mapping slot names to CURIEs
(e.g. `{"subject": "CHEBI:14321", "object": "GO:0006096"}`).

**Optional: `ontology_term_justifications`**

Alongside `ontology_terms`, an adapter MAY add an `"ontology_term_justifications"`
sub-dict with the same slot keys, where each value is a
[SEMAPV](https://github.com/mapping-commons/SEMAPV) justification CURIE:

| CURIE | When to use |
|---|---|
| `semapv:CompositeMatching` | curated / rule-based identifier lookup (default) |
| `semapv:LexicalMatching` | name or synonym string match |
| `semapv:ManualMappingCuration` | hand-curated assignment |

Downstream SSSOM emitters (e.g. Perspicacité) use this as the
`mapping_justification` predicate when building `sssom:MappingSet` rows from
`ontology_terms`.  If a slot key is absent from `ontology_term_justifications`,
emitters default to `semapv:CompositeMatching`.

## Adding a third-party adapter

1. Implement the `DomainAdapter` structural Protocol (no import needed).
2. Register via `pyproject.toml`:

```toml
[project.entry-points."indicium.adapters"]
my_domain = "my_package.adapters:MyAdapter"
```
