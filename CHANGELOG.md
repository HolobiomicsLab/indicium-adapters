# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

`pyproject.toml` declares 0.6.0. Neither 0.5.0 nor 0.6.0 was tagged: the last
tag is `v0.4.0`, and no version has been published to a package index.

### Added
- `ClassificationVocabularyProvider`, an opt-in protocol for an adapter that
  declares curated classification vocabulary: `primary_domain`, `subdomains` and
  `techniques`. `classification_vocabulary(adapter)` reads the three members into a
  `ClassificationVocabulary` and never substitutes `domain_id` for a missing
  `primary_domain`; an adapter that declares nothing reports `primary_domain=None`.
  (#5)
- Convention: `DomainAdapter.enrich_claim()` MAY set an
  `ontology_term_justifications: dict[str, str]` companion map alongside
  `ontology_terms`, mapping the same slot keys to SEMAPV justification CURIEs (e.g.
  `semapv:CompositeMatching`, `semapv:LexicalMatching`). Downstream SSSOM emitters
  (Perspicacité) use this as `mapping_justification`; absent keys default to
  `semapv:CompositeMatching`. Documented in the `enrich_claim` docstring and the
  README.
- `RoundTripResult.skills_checked`, also printed by `verify-claims` and returned
  under `skills_checked` in its JSON: the number of skills read from disk, so a pass
  that read no skill is visible.
- `RoundTripResult.skills_listed` and `skills_skipped`, also in the `verify-claims`
  JSON and pretty output: the entries under `skills` in `collection.yaml`, and the
  slug and reason of each listed skill that has no SKILL.md or fails validation.
  The loader keeps such skills in `ASBCollection.skipped_skills` (new model
  `ASBSkippedSkill`) instead of dropping them.
- `ASBClaimRecord.context`, the SuperPattern context slot. The mapper writes it as
  `asb:context`, which the indicium `asb:Claim` shape requires, when the record has
  one. An earlier entry and the body of commit 8ebaff0 said ASB claim records carry
  no context; ASB's own claims do, and it was this package's record that lacked the
  field.
- `RoundTripResult.skills_with_unlisted_claims`: skills whose frontmatter declares
  `n_claims` above 0 but lists no claim IRI. `verify-claims` returns it in its JSON
  and prints a warning on stderr; it does not fail the gate. `ASBSkillRecord` reads
  `n_claims`.
- `tests/test_release_metadata.py`: `CITATION.cff` and `pyproject.toml` carry the
  same version, `indicium_adapters.asb.__version__` is the installed distribution
  version, and this file has one Unreleased section.

### Changed
- **The dependency is the renamed `indicium-standard>=2.0.0`** (was `indicium>=1.7`),
  and the version moved to 0.6.0 in the same commit. The import name stays
  `indicium`.
- **`requires-python` lowered from `>=3.12` to `>=3.11`.** Nothing in the package
  needed 3.12: all 24 source and test modules parse under 3.11 (no PEP 695
  type-parameter syntax, no `type` alias statements), there is no 3.12-only stdlib
  API in use, and the only runtime dependency, `indicium-standard`, already declares
  `>=3.11`. At that commit the suite passed unchanged on 3.11: 73 passed, 4 skipped,
  90.31% coverage.

  The floor mattered because it made every `DomainAdapter` uninstallable in the
  AgenticScienceBuilder environment, which runs Python 3.11 and is where the
  classification vocabulary adapters feed is actually consumed. With the floor
  lowered, installing `indicium-adapters` plus `indicium-adapters-astronomy` into
  that environment takes ASB's controlled vocabulary from 17 primary domains to 18,
  adding `astronomy` along with its 11 subdomains and its techniques; previously an
  astronomy paper was classified as `other` no matter what.
- Dropped the `Programming Language :: Python :: 3.10` classifier. It advertised a
  version that could never resolve, since `indicium-standard` requires `>=3.11`.
- **The ASB mapper takes its vocabulary bases from indicium** (`ASB_BASE`,
  `INDICIUM_BASE`) instead of the hardcoded
  `https://w3id.org/holobiomicslab/indicium#`. A claim is typed `asb:Claim`; its
  subject, predicate and object fill `asb:subject`, `asb:relation` and `asb:object`,
  the terms the indicium `asb:Claim` shape declares. A qualifier rides
  `asb:qualifier` when it is a closed Bucur term and `asb:domainQualifier`
  otherwise, as the `DomainAdapter.qualifiers` contract states. The other mapper
  terms keep their local names under `INDICIUM_BASE`. No file in the current
  collections uses the old namespace, so it is not read as an alias.
- Skill and tool instance IRIs keep the `https://w3id.org/holobiomicslab/asb-skill/`
  and `.../asb-tool/` form that ASB's release code mints, now exported as
  `ASB_SKILL_BASE` and `ASB_TOOL_BASE`. `ASBAdapter` binds the `asb:` prefix to the
  vocabulary and `asbskill:` to the skill instances.
- `ASBSourcePaper.title` may be empty: current releases leave it empty when the
  title was not resolved, and the DOI identifies the paper. The mapper writes no
  empty title.
- A skill or tool record that fails validation is skipped with a warning; the
  loader no longer catches every exception, and `tools.lock.yaml` entries that fail
  are no longer dropped silently.
- `indicium_adapters.asb.__version__` reads the installed distribution version (it
  was a hardcoded `0.5.0`). `CITATION.cff` moves from 0.4.0 to 0.6.0, gains the
  author's ORCID and drops the `date-released` of 0.4.0, since 0.6.0 has no release.
- `SECURITY.md` writes its supported-versions table in plain text.
- CI tests Python 3.11, 3.12 and 3.13. `ruff check .` now fails the job on any
  finding; ruff is pinned to 0.17.3 in the `dev` extra because each release widens
  its default rule set. The extras install no longer falls back to a bare install.
  The `ORG_PAT` step stays until `indicium-standard` is on PyPI.
- `uv.lock` is refreshed: it still declared `requires-python = ">=3.12"`.

### Fixed
- **`verify-claims` raised `AttributeError: 'str' object has no attribute 'get'` on
  every current collection.** `load_collection()` read only the earlier layout,
  where `collection.yaml` lists skills as mappings. Current releases list skills and
  tools as slugs, keep leaf skills in `leaves/<slug>/SKILL.md`, put the collection
  IRI under `iri`, write evidence spans as plain strings and papers under
  `derived_from` or `provenance.source_papers`. The loader now reads both layouts.
- SKILL.md frontmatter was split on any `---`, so a quoted value containing it cut
  the YAML short. Only a fence line closes the block now.
- A tool slug containing the word `path` was indexed as a mapping and raised
  `TypeError`.
- The round-trip gate counted a claim as resolved only when typed with the
  hardcoded holobiomicslab `Claim` class. It now resolves claims typed with
  indicium's `asb:Claim`, the class ASB's indicium emitter writes.
- The pretty `verify-claims` FAIL report printed each dangling reference as a
  dataclass repr; it now prints `<skill slug>: <claim IRI>`.
- **The round-trip gate failed open.** A listed skill with no SKILL.md was dropped
  without a word, and one that failed validation was dropped with a warning, so
  `verify-claims` exited 0 without checking the claim IRIs it listed. Both now fail
  the gate (exit 1, `RoundTripResult.ok` false), and the claim IRIs a skipped
  skill's frontmatter lists are still checked. `RoundTripResult.render()` now
  returns the report `verify-claims` prints.
- The `verify-claims --help` text named only `metadata.claims` and the
  `skills/<slug>/SKILL.md` layout; it now names the frontmatter `claims` key and
  `leaves/<slug>/SKILL.md`.

### Known gaps
- Only claims use terms the indicium schema declares. Evidence, software, source
  and skill nodes and their properties use this mapper's local names under
  `INDICIUM_BASE` (for example `exactQuote`, where indicium declares
  `quote_exact`).
- A claims-file record without `context` maps to a claim without `asb:context`,
  which the `asb:Claim` shape requires, and the shape reports a violation. ASB's
  own claims carry a context; the mapper writes it when the record has one.
- Current tool records carry `repo_url`, not `canonical_url`, so the bio.tools
  resolver has nothing to look up for them.
- `uv lock` and `uv sync` need the indicium checkout beside this one:
  `[tool.uv.sources]` points `indicium-standard` at `../indicium`.

---

## [0.5.0] - 2026-05-24 (never tagged)

### Added

- New `indicium_adapters.asb` subpackage: maps ASB-Skill collection
  on-disk artifacts (collection.yaml, SKILL.md frontmatter,
  tools/<slug>.yaml) onto `indicium:Evidence`, `indicium:SoftwareEntity`,
  `indicium:Claim`, `indicium:InformationSource`, and SEPIO skill→claim
  assertions.
- PROV-O envelope (`prov:wasGeneratedBy`, `prov:wasDerivedFrom`,
  `prov:atTime`) attached to every typed node.
- `BioToolsResolver` with SQLite cache and `ASB_ADAPTER_OFFLINE` env
  hook for CI determinism.
- `run_round_trip_check()` CI gate that fails on any dangling
  `metadata.claims` URI in any SKILL.md.
- `verify-claims` console script for `asb-skill-collections` CI integration.

### Notes

- Subpackage requires the new optional extra: `pip install -e '.[asb]'`.
- The reverse (indicium → ASB-Skill hints) adapter is deferred to v1.1.
- The `SciSkill`→`ASBSkill` Python rename in ASB lands in Wave 2;
  this subpackage works against on-disk artifacts only and is unaffected.

---

## [0.4.0] - 2026-05-24

### Removed
- `MetabolomicsAdapter` and its `metabolomics.shapes.ttl` and associated tests.
  These have moved to the new `indicium-adapters-metabolomics` package, which
  ships richer enrichment (RefMet+BridgeDb compound index) and adds two sibling
  adapters: `MetaboKGAdapter` and `EMIAdapter`.
  Migration: `pip install indicium-adapters-metabolomics`; the
  `discover_adapters()["metabolomics"]` entry remains available, now sourced
  from the new package.

---

## [0.3.0] - 2026-05-23

### Added
- `CompositeAdapter`: combines 2+ `DomainAdapter` instances into one that satisfies both
  `DomainAdapter` and `SHACLProvider` protocols. Composition rules: `qualifiers` (union),
  `ontology_prefixes` (merged dict, later adapter wins on key conflict), `extraction_context()`
  (concatenated with double newline), `enrich_claim()` (sequential chain: each adapter
  enriches the output of the previous), `shacl_shapes()` (merged `rdflib.Graph`; adapters
  without `shacl_shapes()` are silently skipped; uses `isinstance(SHACLProvider)` check).
- `compose_adapters(adapters)`: factory function: returns the single adapter unchanged
  when `len(adapters) == 1` (no wrapping overhead); returns `CompositeAdapter` for 2+;
  raises `ValueError` for an empty list.
- Both `CompositeAdapter` and `compose_adapters` exported from the top-level
  `indicium_adapters` package.

---

## [0.2.0] - 2026-05-23

### Added
- `SHACLProvider` Protocol mixin: adapters that implement `shacl_shapes() -> rdflib.Graph` are
  automatically detected by `indicium.validate_graph()` and their shapes are merged into validation.
- `api_version: int` field on `DomainAdapter` Protocol and `CURRENT_API_VERSION` constant.
  `discover_adapters()` now skips adapters whose `api_version` does not match `CURRENT_API_VERSION`
  and emits a `RuntimeWarning` with upgrade instructions.
- `MetabolomicsAdapter.shacl_shapes()`: returns the bundled `metabolomics.shapes.ttl` graph
  containing CURIE-format constraints on `asb:subject_ontology_term` / `asb:object_ontology_term`.

### Fixed
- `metabolomics.shapes.ttl` shape target corrected from the inert `sh:targetSubjectsOf CHEBI:is_a`
  to `sh:targetClass asb:Claim` with property shapes on the `asb:{slot}_ontology_term` predicates
  emitted by `claims_to_graph()`.
- CURIE regex pattern in `metabolomics.shapes.ttl` broadened from `[A-Za-z0-9_]+` to
  `[A-Za-z0-9_.+-]+` in the local part, accommodating PubChem, InChIKey, and other identifiers
  that contain dots, hyphens, or plus signs.
- `rdflib>=7.0` added as an explicit runtime dependency (was only transitive via `indicium`).
- `indicium` dependency floor raised from `>=1.0` to `>=1.4`, which is the minimum version that
  provides the `extra_shapes` kwarg required by `SHACLProvider` injection.

---

## [0.1.0] - 2026-05-20

### Added
- `DomainAdapter` Protocol with `domain_id`, `domain_label`, and `api_version` fields.
- `discover_adapters()`: entry-point discovery function resolving all `indicium.adapters`
  entry points at import time; returns a `dict[str, DomainAdapter]` keyed by `domain_id`.
- `MetabolomicsAdapter` with:
  - `enrich_claim()`: annotates `subject` / `object` / `qualifier` slots with CHEBI CURIEs from
    a static compound lookup table (live network lookup planned for a future `[network]` extra).
  - `domain_context` string injected into LLM extraction prompts for metabolomics-aware extraction.
