"""MetabolomicsAdapter — built-in adapter for metabolomics domain claims.

Ships a static compound→CHEBI lookup (~10 entries in v0.1; no network dep).
Subsequent versions will expand _COMPOUNDS and optionally add live ChEBI lookups
via the [metabolomics] optional extra.
"""
from __future__ import annotations


class MetabolomicsAdapter:
    """Domain adapter for metabolomics: qualifiers, CHEBI-prefixed ontology
    terms, and static compound name → CURIE enrichment."""

    domain_id = "metabolomics"

    qualifiers: frozenset[str] = frozenset({
        "identifies",            # mass-spec identification claim
        "quantifies",            # abundance / concentration measurement
        "is_biomarker_for",      # biomarker association
        "discriminates_between", # class-separation claim (e.g. disease vs. control)
        "metabolizes",           # enzyme/substrate relationship
    })

    ontology_prefixes: dict[str, str] = {
        "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        "HMDB":  "https://hmdb.ca/metabolites/",
        "MTBLS": "https://www.ebi.ac.uk/metabolights/",
    }

    # Static bundled lookup (~10 common metabolites at v0.1; no network dep).
    # Keys are lowercase canonical names; values are CHEBI CURIEs.
    # Expand CURIEs using ontology_prefixes, NOT indicium.expand_curie()
    # (which does not cover domain-specific namespaces like CHEBI).
    _COMPOUNDS: dict[str, str] = {
        "glutamate":   "CHEBI:14321",
        "glutamine":   "CHEBI:58359",
        "glucose":     "CHEBI:4167",
        "atp":         "CHEBI:15422",
        "nadh":        "CHEBI:16908",
        "acetyl-coa":  "CHEBI:15351",
        "pyruvate":    "CHEBI:15361",
        "lactate":     "CHEBI:24996",
        "citrate":     "CHEBI:16947",
        "succinate":   "CHEBI:15741",
    }

    def extraction_context(self) -> str:
        """Return domain context appended to the LLM extraction prompt."""
        return (
            "Domain: metabolomics. "
            "Extra qualifiers available: identifies, quantifies, is_biomarker_for, "
            "discriminates_between, metabolizes. "
            "Use standard compound names (CHEBI-compatible) for metabolite "
            "subjects and objects where possible."
        )

    def enrich_claim(self, claim: dict) -> dict:
        """Add ontology_terms CURIEs for known compound names in subject/object slots.

        Returns a new dict; never mutates the input.
        CURIEs use the CHEBI prefix defined in ontology_prefixes.
        """
        claim = dict(claim)  # never mutate input
        for slot in ("subject", "object"):
            name = claim.get(slot, "").strip().lower()
            if chebi := self._COMPOUNDS.get(name):
                claim.setdefault("ontology_terms", {})[slot] = chebi
        return claim
