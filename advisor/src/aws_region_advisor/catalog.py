"""Load seed files and assemble a unified infrastructure catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Catalog, CatalogMeta, Coordinates, InfrastructureNode, utc_now_iso

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_DIR = PACKAGE_ROOT / "data" / "seed"
DEFAULT_CATALOG_PATH = PACKAGE_ROOT / "data" / "catalog.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _coords(lat: float | None, lon: float | None) -> Coordinates | None:
    if lat is None or lon is None:
        return None
    return Coordinates(lat=float(lat), lon=float(lon))


def _region_nodes(rows: list[dict[str, Any]]) -> list[InfrastructureNode]:
    nodes: list[InfrastructureNode] = []
    for row in rows:
        code = row["code"]
        nodes.append(
            InfrastructureNode(
                id=f"region:{code}",
                type="region",
                code=code,
                display_name=row["name"],
                parent_region_id=None,
                country_codes=list(row.get("country_codes", [])),
                coordinates=_coords(row.get("lat"), row.get("lon")),
                opt_in_required=bool(row.get("opt_in_required", False)),
                partition="aws",
                compliance_tags=list(row.get("compliance_tags", [])),
                privacy_buckets=list(row.get("privacy_buckets", [])),
                capabilities=["full_region", "multi_az"],
                metadata={
                    "geography": row.get("geography"),
                    "city": row.get("city"),
                    "az_count": row.get("az_count"),
                },
            )
        )
        # Synthetic AZ placeholders when live sync is unavailable
        az_count = int(row.get("az_count") or 0)
        for idx in range(az_count):
            letter = chr(ord("a") + idx)
            az_code = f"{code}{letter}"
            nodes.append(
                InfrastructureNode(
                    id=f"az:{az_code}",
                    type="az",
                    code=az_code,
                    display_name=f"{row['name']} AZ {letter}",
                    parent_region_id=f"region:{code}",
                    country_codes=list(row.get("country_codes", [])),
                    coordinates=_coords(row.get("lat"), row.get("lon")),
                    opt_in_required=bool(row.get("opt_in_required", False)),
                    partition="aws",
                    compliance_tags=list(row.get("compliance_tags", [])),
                    privacy_buckets=list(row.get("privacy_buckets", [])),
                    capabilities=["availability_zone"],
                    metadata={"synthetic": True, "letter": letter},
                )
            )
    return nodes


def _zone_nodes(
    rows: list[dict[str, Any]],
    *,
    node_type: str,
    capability: str,
) -> list[InfrastructureNode]:
    nodes: list[InfrastructureNode] = []
    for row in rows:
        code = row["code"]
        parent = row["parent_region"]
        nodes.append(
            InfrastructureNode(
                id=f"{node_type}:{code}",
                type=node_type,  # type: ignore[arg-type]
                code=code,
                display_name=row.get("name") or code,
                parent_region_id=f"region:{parent}",
                country_codes=list(row.get("country_codes", [])),
                coordinates=_coords(row.get("lat"), row.get("lon")),
                opt_in_required=True,
                partition="aws",
                capabilities=[capability],
                metadata={
                    "group": row.get("group"),
                    "city": row.get("city"),
                    "carrier": row.get("carrier"),
                },
            )
        )
    return nodes


def _edge_nodes(rows: list[dict[str, Any]]) -> list[InfrastructureNode]:
    nodes: list[InfrastructureNode] = []
    for row in rows:
        code = row["code"]
        nodes.append(
            InfrastructureNode(
                id=f"edge_pop:{code}",
                type="edge_pop",
                code=code,
                display_name=f"{row['city']} Edge PoP",
                parent_region_id=None,
                country_codes=list(row.get("country_codes", [])),
                coordinates=_coords(row.get("lat"), row.get("lon")),
                opt_in_required=False,
                partition="aws",
                capabilities=list(
                    row.get(
                        "capabilities",
                        ["edge_cdn", "edge_dns", "edge_waf", "lambda_at_edge"],
                    )
                ),
                metadata={
                    "city": row.get("city"),
                    "pop_count": row.get("pop_count"),
                },
            )
        )
    return nodes


def _rec_nodes(rows: list[dict[str, Any]]) -> list[InfrastructureNode]:
    nodes: list[InfrastructureNode] = []
    for row in rows:
        code = row["code"]
        parent = row.get("parent_region")
        nodes.append(
            InfrastructureNode(
                id=f"regional_edge_cache:{code}",
                type="regional_edge_cache",
                code=code,
                display_name=row.get("name") or code,
                parent_region_id=f"region:{parent}" if parent else None,
                country_codes=list(row.get("country_codes", [])),
                coordinates=_coords(row.get("lat"), row.get("lon")),
                opt_in_required=False,
                partition="aws",
                capabilities=["regional_edge_cache"],
                metadata={"city": row.get("city")},
            )
        )
    return nodes


def build_catalog_from_seed(seed_dir: Path | None = None) -> Catalog:
    seed_dir = seed_dir or DEFAULT_SEED_DIR
    meta_raw = _load_json(seed_dir / "meta.json")
    nodes: list[InfrastructureNode] = []
    nodes.extend(_region_nodes(_load_json(seed_dir / "regions.json")))
    nodes.extend(
        _zone_nodes(
            _load_json(seed_dir / "local_zones.json"),
            node_type="local_zone",
            capability="local_zone_compute",
        )
    )
    nodes.extend(
        _zone_nodes(
            _load_json(seed_dir / "wavelength_zones.json"),
            node_type="wavelength",
            capability="mec_5g",
        )
    )
    nodes.extend(_edge_nodes(_load_json(seed_dir / "edge_pops.json")))
    nodes.extend(_rec_nodes(_load_json(seed_dir / "regional_edge_caches.json")))

    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.type] = counts.get(node.type, 0) + 1

    meta = CatalogMeta(
        version="0.1.0",
        generated_at=utc_now_iso(),
        partition=meta_raw.get("partition", "aws"),
        source=meta_raw.get("source", "curated-seed"),
        notes=meta_raw.get("notes", ""),
        sources=list(meta_raw.get("sources", [])),
        counts=counts,
    )
    return Catalog(meta=meta, nodes=nodes)


def merge_live_zones(catalog: Catalog, live_nodes: list[InfrastructureNode]) -> Catalog:
    """Replace seed local/wavelength zones with live EC2 DescribeAvailabilityZones results."""
    kept = [n for n in catalog.nodes if n.type not in {"local_zone", "wavelength", "az"}]
    # Keep synthetic AZs for regions not covered by live data; prefer live AZs when present
    live_types = {n.type for n in live_nodes}
    if "az" in live_types:
        # Drop synthetic AZs entirely when live AZs provided
        pass
    else:
        kept.extend([n for n in catalog.nodes if n.type == "az"])

    merged = kept + live_nodes
    counts: dict[str, int] = {}
    for node in merged:
        counts[node.type] = counts.get(node.type, 0) + 1
    meta = catalog.meta.model_copy(
        update={
            "generated_at": utc_now_iso(),
            "source": "curated-seed+aws-api",
            "counts": counts,
        }
    )
    return Catalog(meta=meta, nodes=merged)


def write_catalog(catalog: Catalog, path: Path | None = None) -> Path:
    path = path or DEFAULT_CATALOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(catalog.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def load_catalog(path: Path | None = None) -> Catalog:
    path = path or DEFAULT_CATALOG_PATH
    if not path.exists():
        catalog = build_catalog_from_seed()
        write_catalog(catalog, path)
        return catalog
    return Catalog.model_validate_json(path.read_text(encoding="utf-8"))
