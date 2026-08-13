"""Pipeline tests. Expanded once ingest and the star-schema transform exist (Phase 1)."""

import importlib


def test_src_package_importable():
    assert importlib.import_module("src") is not None
