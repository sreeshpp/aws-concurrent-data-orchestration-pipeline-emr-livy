"""Unit tests for catalog build and geo helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aws_region_advisor.catalog import build_catalog_from_seed, write_catalog
from aws_region_advisor.geo import closest, haversine_km, resolve_city


def test_build_catalog_has_expected_types(tmp_path: Path) -> None:
    catalog = build_catalog_from_seed()
    counts = catalog.meta.counts
    assert counts["region"] >= 30
    assert counts["edge_pop"] >= 90
    assert counts["local_zone"] >= 10
    assert counts["wavelength"] >= 8
    assert counts["az"] > counts["region"]
    out = write_catalog(catalog, tmp_path / "catalog.json")
    assert out.exists()
    assert catalog.get("us-east-1") is not None
    assert catalog.get("region:eu-central-1") is not None


def test_haversine_london_paris() -> None:
    # Roughly 340–350 km
    d = haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert 300 < d < 400


def test_closest_edge_to_mumbai() -> None:
    catalog = build_catalog_from_seed()
    edges = [n for n in catalog.by_type("edge_pop") if n.coordinates]
    lat, lon = resolve_city("Mumbai")
    ranked = closest(
        lat,
        lon,
        edges,
        coord_of=lambda n: (n.coordinates.lat, n.coordinates.lon),
        limit=3,
    )
    assert ranked[0][0].metadata["city"] == "Mumbai"
    assert ranked[0][1] < 50


def test_privacy_buckets_on_eu_region() -> None:
    catalog = build_catalog_from_seed()
    frankfurt = catalog.get("eu-central-1")
    assert frankfurt is not None
    assert "eu-data-residency" in frankfurt.privacy_buckets
    assert "gdpr" in frankfurt.compliance_tags
