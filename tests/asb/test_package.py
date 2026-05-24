"""Smoke test: the asb subpackage imports cleanly."""
from __future__ import annotations


def test_asb_subpackage_importable() -> None:
    import indicium_adapters.asb as asb

    assert hasattr(asb, "__version__")
    assert asb.__version__ == "0.5.0"
