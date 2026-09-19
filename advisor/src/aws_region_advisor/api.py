"""Read-only HTTP API for the infrastructure catalog."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from .catalog import DEFAULT_CATALOG_PATH, load_catalog
from .geo import closest, parse_limit, resolve_city
from .models import Catalog, InfrastructureNode, NodeType

app = FastAPI(
    title="AWS Region & Edge Advisor Catalog",
    description=(
        "Phase 1 read API: Regions, AZs, Local Zones, Wavelength Zones, "
        "CloudFront edge PoPs, and closest-node queries."
    ),
    version="0.1.0",
)


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return load_catalog(DEFAULT_CATALOG_PATH)


def reload_catalog() -> Catalog:
    get_catalog.cache_clear()
    return get_catalog()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/catalog/meta")
def catalog_meta() -> dict[str, Any]:
    return get_catalog().meta.model_dump()


@app.get("/v1/catalog")
def full_catalog() -> dict[str, Any]:
    return get_catalog().model_dump()


@app.get("/v1/nodes")
def list_nodes(
    type: NodeType | None = Query(default=None, description="Filter by node type"),
    country: str | None = Query(default=None, description="ISO country code filter"),
    region: str | None = Query(default=None, description="Parent region code filter"),
) -> list[dict[str, Any]]:
    nodes = get_catalog().nodes
    if type:
        nodes = [n for n in nodes if n.type == type]
    if country:
        cc = country.upper()
        nodes = [n for n in nodes if cc in n.country_codes]
    if region:
        rid = region if region.startswith("region:") else f"region:{region}"
        nodes = [
            n
            for n in nodes
            if n.parent_region_id == rid or (n.type == "region" and n.code == region)
        ]
    return [n.model_dump() for n in nodes]


@app.get("/v1/nodes/{node_id}")
def get_node(node_id: str) -> dict[str, Any]:
    node = get_catalog().get(node_id)
    if not node:
        # allow bare codes
        node = get_catalog().get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return node.model_dump()


@app.get("/v1/regions")
def list_regions() -> list[dict[str, Any]]:
    return [n.model_dump() for n in get_catalog().by_type("region")]


@app.get("/v1/edge")
def list_edge() -> list[dict[str, Any]]:
    return [n.model_dump() for n in get_catalog().by_type("edge_pop")]


@app.get("/v1/closest")
def closest_nodes(
    city: str | None = Query(default=None, description="Known city name"),
    lat: float | None = None,
    lon: float | None = None,
    type: NodeType = Query(default="edge_pop"),
    limit: int = Query(default=5, ge=1, le=25),
) -> dict[str, Any]:
    if lat is None or lon is None:
        if not city:
            raise HTTPException(
                status_code=400,
                detail="Provide city= or both lat= and lon=",
            )
        try:
            lat, lon = resolve_city(city)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    candidates = [
        n for n in get_catalog().by_type(type) if n.coordinates is not None
    ]
    ranked = closest(
        lat,
        lon,
        candidates,
        coord_of=lambda n: (n.coordinates.lat, n.coordinates.lon),  # type: ignore[union-attr]
        limit=parse_limit(limit),
    )
    return {
        "query": {"city": city, "lat": lat, "lon": lon, "type": type},
        "results": [
            {
                "distance_km": round(dist, 1),
                "node": node.model_dump(),
            }
            for node, dist in ranked
        ],
    }


@app.post("/v1/admin/reload")
def admin_reload() -> dict[str, Any]:
    catalog = reload_catalog()
    return {"reloaded": True, "meta": catalog.meta.model_dump()}
