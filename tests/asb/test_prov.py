"""Tests for the PROV-O envelope helper."""
from __future__ import annotations

from datetime import UTC, datetime

import rdflib
from rdflib.namespace import PROV

from indicium_adapters.asb.prov import ProvEnvelope, attach_prov


def test_prov_envelope_defaults_to_utc_now() -> None:
    env = ProvEnvelope.new(
        adapter_run_iri="urn:uuid:00000000-0000-0000-0000-000000000001",
        collection_iri="https://w3id.org/holobiomicslab/asb-skill/collection/metabolomics/v1",
    )
    assert env.at_time.tzinfo is not None
    assert env.at_time.tzinfo.utcoffset(env.at_time).total_seconds() == 0


def test_attach_prov_adds_three_triples() -> None:
    env = ProvEnvelope(
        adapter_run_iri="urn:uuid:00000000-0000-0000-0000-000000000001",
        collection_iri="https://w3id.org/holobiomicslab/asb-skill/collection/metabolomics/v1",
        at_time=datetime(2026, 5, 24, 12, 0, 0, tzinfo=UTC),
    )
    g = rdflib.Graph()
    subject = rdflib.URIRef("urn:test:subject")
    attach_prov(g, subject, env)
    assert (subject, PROV.wasGeneratedBy, rdflib.URIRef(env.adapter_run_iri)) in g
    assert (subject, PROV.wasDerivedFrom, rdflib.URIRef(env.collection_iri)) in g
    # exactly one prov:atTime literal
    times = list(g.triples((subject, PROV.atTime, None)))
    assert len(times) == 1
    assert times[0][2].datatype == rdflib.XSD.dateTime
