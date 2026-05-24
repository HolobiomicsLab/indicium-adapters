# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## 0.5.0 — 2026-05-24

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

## [0.4.0] — 2026-05-24

### Removed
- `MetabolomicsAdapter` and its `metabolomics.shapes.ttl` and associated tests.
  These have moved to the new `indicium-adapters-metabolomics` package, which
  ships richer enrichment (RefMet+BridgeDb compound index) and adds two sibling
  adapters: `MetaboKGAdapter` and `EMIAdapter`.
  Migration: `pip install indicium-adapters-metabolomics` — the
  `discover_adapters()["metabolomics"]` entry remains available, now sourced
  from the new package.

---

## [0.3.0] - 2026-05-23

### Added
- `CompositeAdapter` — combines 2+ `DomainAdapter` instances into one that satisfies both
  `DomainAdapter` and `SHACLProvider` protocols. Composition rules: `qualifiers` (union),
  `ontology_prefixes` (merged dict, later adapter wins on key conflict), `extraction_context()`
  (concatenated with double newline), `enrich_claim()` (sequential chain — each adapter
  enriches the output of the previous), `shacl_shapes()` (merged `rdflib.Graph`; adapters
  without `shacl_shapes()` are silently skipped; uses `isinstance(SHACLProvider)` check).
- `compose_adapters(adapters)` — factory function: returns the single adapter unchanged
  when `len(adapters) == 1` (no wrapping overhead); returns `CompositeAdapter` for 2+;
  raises `ValueError` for an empty list.
- Both `CompositeAdapter` and `compose_adapters` exported from the top-level
  `indicium_adapters` package.

---

## [0.2.0] - 2026-05-23

### Added
- `SHACLProvider` Protocol mixin — adapters that implement `shacl_shapes() -> rdflib.Graph` are
  automatically detected by `indicium.validate_graph()` and their shapes are merged into validation.
- `api_version: int` field on `DomainAdapter` Protocol and `CURRENT_API_VERSION` constant.
  `discover_adapters()` now skips adapters whose `api_version` does not match `CURRENT_API_VERSION`
  and emits a `RuntimeWarning` with upgrade instructions.
- `MetabolomicsAdapter.shacl_shapes()` — returns the bundled `metabolomics.shapes.ttl` graph
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
- `discover_adapters()` — entry-point discovery function resolving all `indicium.adapters`
  entry points at import time; returns a `dict[str, DomainAdapter]` keyed by `domain_id`.
- `MetabolomicsAdapter` with:
  - `enrich_claim()` — annotates `subject` / `object` / `qualifier` slots with CHEBI CURIEs from
    a static compound lookup table (live network lookup planned for a future `[network]` extra).
  - `domain_context` string injected into LLM extraction prompts for metabolomics-aware extraction.
