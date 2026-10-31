"""PROV-O envelope attached to every adapter-emitted record.

The envelope answers three questions for an audit reader:

- *Who generated this?* ``prov:wasGeneratedBy`` → adapter-run IRI (a fresh
  ``urn:uuid:<uuid4>`` per ``ASBAdapter`` invocation).
- *Where did it come from?* ``prov:wasDerivedFrom`` → the ASB collection
  IRI (e.g. ``w3id.org/holobiomicslab/asb-skill/collection/metabolomics/v1``).
- *When?* ``prov:atTime`` → ISO 8601 UTC timestamp.
"""
from __future__ import annotations

from datetime import UTC, datetime

import rdflib
from pydantic import BaseModel, ConfigDict, Field
from rdflib.namespace import PROV, XSD


class ProvEnvelope(BaseModel):
    """Per-record provenance triple bundle."""

    model_config = ConfigDict(frozen=True)

    adapter_run_iri: str = Field(min_length=1)
    collection_iri: str = Field(min_length=1)
    at_time: datetime

    @classmethod
    def new(cls, adapter_run_iri: str, collection_iri: str) -> ProvEnvelope:
        """Build an envelope stamped with ``datetime.now(UTC)``."""
        return cls(
            adapter_run_iri=adapter_run_iri,
            collection_iri=collection_iri,
            at_time=datetime.now(UTC),
        )


def attach_prov(
    graph: rdflib.Graph, subject: rdflib.term.Node, envelope: ProvEnvelope
) -> None:
    """Add the three PROV triples for ``subject`` to ``graph``."""
    graph.add(
        (
            subject,
            PROV.wasGeneratedBy,
            rdflib.URIRef(envelope.adapter_run_iri),
        )
    )
    graph.add(
        (
            subject,
            PROV.wasDerivedFrom,
            rdflib.URIRef(envelope.collection_iri),
        )
    )
    graph.add(
        (
            subject,
            PROV.atTime,
            rdflib.Literal(envelope.at_time.isoformat(), datatype=XSD.dateTime),
        )
    )


__all__ = ["ProvEnvelope", "attach_prov"]
