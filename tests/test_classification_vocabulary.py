"""Conformance tests for the classification-vocabulary contract.

Two things are proven here: adapters that DECLARE the vocabulary are read
correctly, and adapters that declare NOTHING keep working exactly as before —
the five-member class must still satisfy the Protocol and still load without a
UserWarning, because the contract was added without an api_version bump.

Every adapter used here carries invented, science-free names: the contract
mechanism lives in this package, the vocabulary lives in adapter packages.
"""
import warnings
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest

from indicium_adapters import (
    CURRENT_API_VERSION,
    ClassificationVocabularyProvider,
    DomainAdapter,
    classification_vocabulary,
    discover_adapters,
)


class _LegacyAdapter:
    """Pre-contract adapter: the five required members and nothing else."""

    domain_id = "legacy-probe"
    qualifiers = frozenset({"probe_q"})
    ontology_prefixes: ClassVar[dict[str, str]] = {"PRB": "http://probe.example.org/"}
    api_version = CURRENT_API_VERSION

    def extraction_context(self) -> str:
        return "Probe context."

    def enrich_claim(self, claim: dict) -> dict:
        return dict(claim)


class _DeclaringAdapter(_LegacyAdapter):
    """Adapter that declares the optional classification vocabulary."""

    domain_id = "declaring-probe"
    primary_domain = "probe-science"
    subdomains = ("probe-subfield",)
    techniques = ("probe-assay", "probe-readout")


class _VariantAdapter(_DeclaringAdapter):
    """Sibling variant sharing one science under its own identity."""

    domain_id = "variant-probe"
    subdomains = ("other-probe-subfield",)


class _MisdeclaredAdapter(_LegacyAdapter):
    """Adapter whose term collection is a bare string, not a collection."""

    domain_id = "misdeclared-probe"
    primary_domain = "probe-science"
    subdomains = "probe-subfield"


# ---------------------------------------------------------------------------
# Backwards compatibility — the contract must not break installed adapters
# ---------------------------------------------------------------------------

def test_api_version_not_bumped():
    """Adding optional members must not invalidate installed adapters."""
    assert CURRENT_API_VERSION == 1


def test_legacy_five_member_adapter_still_satisfies_protocol():
    """A class predating the contract still satisfies DomainAdapter."""
    assert isinstance(_LegacyAdapter(), DomainAdapter)


def test_legacy_adapter_loads_without_warning():
    """discover_adapters() must load a five-member adapter silently."""
    mock_ep = MagicMock()
    mock_ep.name = "legacy_probe"
    mock_ep.load.return_value = _LegacyAdapter

    with (
        patch("importlib.metadata.entry_points", return_value=[mock_ep]),
        warnings.catch_warnings(record=True) as caught,
    ):
        warnings.simplefilter("always")
        result = discover_adapters()

    assert "legacy-probe" in result
    assert [str(w.message) for w in caught] == []


def test_declaring_adapter_loads_without_warning():
    """An adapter carrying the optional members loads the same way."""
    mock_ep = MagicMock()
    mock_ep.name = "declaring_probe"
    mock_ep.load.return_value = _DeclaringAdapter

    with (
        patch("importlib.metadata.entry_points", return_value=[mock_ep]),
        warnings.catch_warnings(record=True) as caught,
    ):
        warnings.simplefilter("always")
        result = discover_adapters()

    assert "declaring-probe" in result
    assert [str(w.message) for w in caught] == []


# ---------------------------------------------------------------------------
# The opt-in Protocol — two-sided
# ---------------------------------------------------------------------------

def test_declaring_adapter_satisfies_provider_protocol():
    assert isinstance(_DeclaringAdapter(), ClassificationVocabularyProvider)


def test_legacy_adapter_does_not_satisfy_provider_protocol():
    """The lookalike negative: same five members, no vocabulary declared."""
    assert not isinstance(_LegacyAdapter(), ClassificationVocabularyProvider)


def test_provider_protocol_is_runtime_checkable():
    assert isinstance(object(), ClassificationVocabularyProvider) is False


# ---------------------------------------------------------------------------
# Reading the declaration
# ---------------------------------------------------------------------------

def test_reads_declared_vocabulary():
    vocab = classification_vocabulary(_DeclaringAdapter())
    assert vocab.primary_domain == "probe-science"
    assert vocab.subdomains == ("probe-subfield",)
    assert vocab.techniques == ("probe-assay", "probe-readout")


def test_undeclared_vocabulary_reports_none_not_domain_id():
    """An absent primary_domain is an explicit unknown, never the identity."""
    vocab = classification_vocabulary(_LegacyAdapter())
    assert vocab.primary_domain is None
    assert vocab.subdomains == ()
    assert vocab.techniques == ()


def test_variants_share_one_primary_domain_under_distinct_identities():
    """Several adapters may serve one science; domain_id stays their own."""
    parent, variant = _DeclaringAdapter(), _VariantAdapter()
    assert parent.domain_id != variant.domain_id
    assert (
        classification_vocabulary(parent).primary_domain
        == classification_vocabulary(variant).primary_domain
    )


def test_string_term_collection_is_rejected():
    """A bare string must raise, not explode into single-character terms."""
    with pytest.raises(TypeError, match="subdomains"):
        classification_vocabulary(_MisdeclaredAdapter())


def test_vocabulary_is_immutable():
    vocab = classification_vocabulary(_DeclaringAdapter())
    with pytest.raises(AttributeError):
        vocab.primary_domain = "other-probe-science"


# ---------------------------------------------------------------------------
# Conformance over whatever is actually installed (vacuous in isolated CI)
# ---------------------------------------------------------------------------

def test_installed_adapters_conform_to_the_contract():
    """Every installed adapter must be readable and must not echo its identity."""
    for name, adapter in discover_adapters().items():
        vocab = classification_vocabulary(adapter)
        assert vocab.primary_domain != adapter.domain_id or isinstance(
            adapter, ClassificationVocabularyProvider
        ), f"{name!r} reports domain_id as primary_domain without declaring it"
        assert all(isinstance(t, str) for t in vocab.subdomains)
        assert all(isinstance(t, str) for t in vocab.techniques)
