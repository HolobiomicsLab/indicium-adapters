<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/indicium-mark-dark.svg">
    <img src="docs/assets/brand/indicium-mark.svg" alt="Indicium mark: a record sheet with three claim lines bound by a round seal" width="96">
  </picture>
</p>

<h1 align="center">indicium-adapters</h1>

<p align="center"><em>The domain-adapter protocol of the Indicium standard: one structural interface, entry-point discovery and composition.</em></p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.6.0-00284b" alt="version 0.6.0">
  <img src="https://img.shields.io/badge/python-3.11%2B-00284b" alt="Python 3.11 or later">
  <img src="https://img.shields.io/badge/licence-MIT-04919a" alt="MIT licence">
</p>

---

## TL;DR

`indicium-adapters` defines how a science plugs into the Indicium claim standard. A domain adapter is any class with four attributes and two methods; two optional groups add SHACL shapes and a curated classification vocabulary. The package discovers installed adapters through an entry point, composes them, and names no science itself. Ten domain packages implement it, with 15 entry points between them. It also ships `indicium_adapters.asb`, which maps ASB skill-collection files to Indicium RDF, and the `verify-claims` release gate.

## The protocol

| Member | Kind | What it is |
|---|---|---|
| `domain_id` | required | the adapter's own id, lowercase and hyphenated; the `discover_adapters()` key |
| `qualifiers` | required | domain claim qualifiers, snake_case (`^[a-z][a-z0-9_]*$`); a qualifier that is not a closed Bucur term rides `asb:domainQualifier` |
| `ontology_prefixes` | required | prefix to base IRI, for expanding the CURIEs the adapter emits |
| `api_version` | required | must equal `CURRENT_API_VERSION` (1); other values are skipped with a warning |
| `extraction_context()` | required | short text appended to the claim-extraction prompt |
| `enrich_claim(claim)` | required | pure function; returns a new claim dict, may add `ontology_terms` and `ontology_term_justifications` |
| `shacl_shapes()` | optional, `SHACLProvider` | an `rdflib.Graph` of domain shapes |
| `primary_domain`, `subdomains`, `techniques` | optional, `ClassificationVocabularyProvider` | curated classification vocabulary, read with `classification_vocabulary()` |

Functions: `discover_adapters()` (entry-point group `indicium.adapters`), `compose_adapters()` (one adapter from several), `classification_vocabulary()` (reads the optional triple and never substitutes `domain_id` for a missing `primary_domain`).

Implementations, measured with all ten installed beside this package (15 entry points):

| Package | Entry points | `primary_domain` |
|---|---|---|
| `indicium-adapters-agentic-ai` | `agentic-ai` | `agentic-ai` |
| `indicium-adapters-astronomy` | `astronomy` | `astronomy` |
| `indicium-adapters-epigenomics` | `bulk-epigenomics`, `single-cell-epigenomics`, `methylation-array-epigenomics` | `epigenomics` |
| `indicium-adapters-genomics` | `genomics` | `genomics` |
| `indicium-adapters-metabarcoding` | `metabarcoding` | `metabarcoding` |
| `indicium-adapters-metabolomics` | `metabolomics`, `metabokg`, `emi` | `metabolomics` |
| `indicium-adapters-metagenomics` | `metagenomics` | `metagenomics` |
| `indicium-adapters-multi-omics` | `multi-omics` | `multi-omics` |
| `indicium-adapters-proteomics` | `proteomics` | `proteomics` |
| `indicium-adapters-transcriptomics` | `bulk-transcriptomics`, `single-cell-transcriptomics` | `transcriptomics` |

## Install

The package is not on PyPI yet, and neither is its one Indicium dependency, the standard itself (distribution `indicium-standard`, import `indicium`). Both repositories follow. Until then, clone them side by side and install from the parent directory (Python 3.11 or later):

```bash
uv venv --python 3.11
uv pip install ./indicium ./indicium-adapters
```

Add the `asb` extra for the ASB collection mapper and the `verify-claims` command: `uv pip install "./indicium-adapters[asb]"`.

Depend on `indicium-standard`, never on `indicium`. The PyPI name `indicium` belongs to an unrelated key-value-store package that ships a module with the same import name.

## Quick start

```python
from indicium_adapters import (
    ClassificationVocabularyProvider,
    DomainAdapter,
    classification_vocabulary,
    discover_adapters,
)


class SoilAdapter:
    domain_id = "soil-science"
    qualifiers = frozenset({"sampled_from"})
    ontology_prefixes = {"ENVO": "http://purl.obolibrary.org/obo/ENVO_"}
    api_version = 1
    primary_domain = "soil-science"
    subdomains = ("soil-microbiology",)
    techniques = ("soil-respiration-assay",)

    def extraction_context(self) -> str:
        return "Soil science: name sampling sites with ENVO terms."

    def enrich_claim(self, claim: dict) -> dict:
        return dict(claim)


adapter = SoilAdapter()
print(isinstance(adapter, DomainAdapter), isinstance(adapter, ClassificationVocabularyProvider))
print(classification_vocabulary(adapter))
print(sorted(discover_adapters()))
```

Output with the ten domain packages installed:

```text
True True
ClassificationVocabulary(primary_domain='soil-science', subdomains=('soil-microbiology',), techniques=('soil-respiration-assay',))
['agentic-ai', 'astronomy', 'bulk-epigenomics', 'bulk-transcriptomics', 'emi', 'genomics', 'metabarcoding', 'metabokg', 'metabolomics', 'metagenomics', 'methylation-array-epigenomics', 'multi-omics', 'proteomics', 'single-cell-epigenomics', 'single-cell-transcriptomics']
```

`SoilAdapter` does not inherit from `DomainAdapter`: the protocol is structural, and `isinstance` checks the members. With no domain package installed, the last line prints `[]`.

## Claim-enrichment contract

`enrich_claim()` receives a 5-slot claim dict and returns an enriched copy. It may add:

- `ontology_terms`: slot name to CURIE, for example `{"subject": "CHEBI:17234"}`.
- `ontology_term_justifications`: the same slot keys, each mapped to a [SEMAPV](https://mapping-commons.github.io/semantic-mapping-vocabulary/) justification. SSSOM emitters such as Perspicacité use it as `mapping_justification`; an absent key means `semapv:CompositeMatching`.

| Justification | Use |
|---|---|
| `semapv:CompositeMatching` | identifier grammar or curated rule (default) |
| `semapv:LexicalMatching` | label or synonym match |
| `semapv:ManualMappingCuration` | hand-curated assignment |

Some domain packages add further keys of their own (`ontology_terms_unmatched`, `xrefs`, `ontology_term_branches`); their READMEs list them.

## ASB collections and `verify-claims`

`indicium_adapters.asb` (extra `asb`) reads an ASB skill collection from disk and maps it to Indicium RDF. `verify-claims` is the release gate for those collections: every claim IRI a SKILL.md lists must be typed `asb:Claim` in the Indicium graph passed to it.

```bash
verify-claims --collection <collection dir> --indicium-graph <graph.ttl> [--format json]
```

| Exit code | Meaning |
|---|---|
| 0 | every claim IRI resolves and every listed skill was read |
| 1 | a claim IRI dangles, or a listed skill has no SKILL.md or fails validation |
| 2 | invocation error: a missing path or a bad argument |

On the bundled fixture in the current collection layout:

```console
$ verify-claims --collection tests/asb/fixtures/slug_list_collection \
                --indicium-graph tests/asb/fixtures/indicium_graph.ttl
OK - 1 claim(s) resolved in 2 skill(s); 2 listed, 0 skipped.

$ verify-claims --collection tests/asb/fixtures/slug_list_collection \
                --indicium-graph tests/asb/fixtures/indicium_graph_broken.ttl
FAIL - 1 dangling claim URI(s):
  - skill-with-claim: https://w3id.org/holobiomicslab/asb-skill/skill-with-claim/claim/01
```

A listed skill the loader cannot read fails the gate. The claim IRIs of a skill that fails validation are still checked:

```console
$ verify-claims --collection tests/asb/fixtures/skipped_skill_collection \
                --indicium-graph tests/asb/fixtures/indicium_graph.ttl
FAIL - 1 dangling claim URI(s):
  - skill-with-claim-and-empty-span: https://w3id.org/holobiomicslab/asb-skill/skill-with-claim-and-empty-span/claim/02
FAIL - 2 of 2 listed skill(s) skipped:
  - skill-with-claim-and-empty-span: evidence_spans.0.quote: String should have at least 1 character
  - listed-but-not-promoted: SKILL.md not found
```

A skill whose frontmatter declares `n_claims` above 0 but lists no claim IRI has nothing to check. It does not fail the gate; `verify-claims` prints their count on stderr:

```console
$ verify-claims --collection tests/asb/fixtures/unlisted_claims_collection \
                --indicium-graph tests/asb/fixtures/indicium_graph.ttl
WARNING - 1 skill(s) declare n_claims above 0 but list no claim IRI; their claims are not checked.
OK - 0 claim(s) resolved in 1 skill(s); 1 listed, 0 skipped.
```

The loader reads two layouts. In the current one, `collection.yaml` lists skill and tool slugs, leaf skills sit in `leaves/<slug>/SKILL.md` and tools in `tools/<slug>.yaml`. In the earlier one, the index lists mappings with a `path` or a `slug`. The JSON output carries `unresolved`, `resolved_count`, `skills_listed` (entries under `skills` in `collection.yaml`), `skills_checked` (skills read), `skills_skipped` (slug and reason per skill not read) and `skills_with_unlisted_claims`; a pass with `skills_checked` at 0 read nothing.

Vocabulary bases come from `indicium` (`ASB_BASE`, `INDICIUM_BASE`), never from a copied string. A claim is typed `asb:Claim` with `asb:subject`, `asb:relation` and `asb:object`, plus `asb:context` when its record has a `context`; a qualifier rides `asb:qualifier` when it is a closed Bucur term and `asb:domainQualifier` otherwise. Skill and tool IRIs keep the `https://w3id.org/holobiomicslab/asb-skill/` and `.../asb-tool/` form that ASB mints.

## Scope

- The package holds the mechanism and names no science. Domain vocabulary lives only in the domain packages; a consumer reads declarations off the adapter and never branches on a domain name.
- `discover_adapters()` never raises. An adapter that fails to load, or declares another `api_version`, is skipped with a `UserWarning`. If two packages register the same `domain_id`, the last one loaded wins.
- Raising `CURRENT_API_VERSION` is a coordinated release across every domain package.

Known limitations of `indicium_adapters.asb`:

- Only claims use terms the indicium schema declares. Evidence, software, source and skill nodes use this mapper's own local names under `INDICIUM_BASE`, for example `exactQuote` where indicium declares `quote_exact`.
- A claims-file record without `context` maps to a claim without `asb:context`, which the `asb:Claim` shape requires; validation reports that violation. ASB's own claims carry a context, and the mapper writes it when the record has one.
- Current tool records carry `repo_url`, not `canonical_url`, so the bio.tools resolver has nothing to look up for them.
- No SKILL.md in the metabolomics v2 collection of [asb-skill-collections](https://github.com/HolobiomicsLab/asb-skill-collections) lists a claim IRI yet: `verify-claims` reads its 5859 skills and passes with 0 claims resolved.

## Writing a domain package

1. Implement the four required attributes and two methods on any class; the class does not need to import or inherit from this package.
2. Declare `primary_domain`, `subdomains` and `techniques` if the adapter serves a science. An ancillary adapter declares nothing rather than its own name.
3. Register the class on the entry point:

```toml
[project.entry-points."indicium.adapters"]
soil-science = "soil_adapters.soil:SoilAdapter"
```

4. Keep `enrich_claim()` pure: no network, no mutation of the input.

## Development

Clone `indicium` and `indicium-adapters` side by side: `[tool.uv.sources]` points `indicium-standard` at `../indicium`, so `uv lock` and `uv sync` fail in a lone clone.

```bash
cd indicium-adapters
uv sync --extra dev --extra asb
uv run pytest
uv run ruff check .
```

On this version: 106 passed, 4 skipped, on Python 3.11, 3.12 and 3.13. The four skipped tests need `indicium-adapters-metabolomics` installed. Coverage is 91% against the 85% gate; `asb/cli.py` is left out of the measure. CI runs the same three Python versions and fails on any ruff finding; ruff is pinned in the `dev` extra.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow and [`CHANGELOG.md`](CHANGELOG.md) for the history. Neither 0.5.0 nor 0.6.0 was tagged; the last tag is `v0.4.0`.

## Related projects

- Indicium standard (`indicium-standard`, import `indicium`): the claim and evidence model, its SHACL shapes and the `asb:` vocabulary base `https://w3id.org/asb#`. Repository follows.
- The ten domain packages in the table above. Repositories follow.
- [Perspicacité](https://github.com/HolobiomicsLab/Perspicacite-AI) unions every installed adapter's `qualifiers` and `extraction_context()` into its claim-extraction prompt.
- [ASB skill collections](https://github.com/HolobiomicsLab/asb-skill-collections): the registry whose collections `indicium_adapters.asb` maps to Indicium RDF and `verify-claims` gates.

## Citation

Cite the package with [`CITATION.cff`](CITATION.cff); GitHub shows it under "Cite this repository". It carries no DOI yet.

## Licence

MIT, see [`LICENSE`](LICENSE).
