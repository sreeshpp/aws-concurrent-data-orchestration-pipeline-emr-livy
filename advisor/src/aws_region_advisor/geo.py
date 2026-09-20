"""Geo helpers for closest-node queries."""

from __future__ import annotations

import math
from typing import Iterable, Sequence, TypeVar

T = TypeVar("T")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def closest(
    lat: float,
    lon: float,
    nodes: Iterable[T],
    *,
    coord_of,
    limit: int = 5,
) -> list[tuple[T, float]]:
    """Return up to `limit` nodes sorted by distance (km) ascending."""
    ranked: list[tuple[T, float]] = []
    for node in nodes:
        nlat, nlon = coord_of(node)
        ranked.append((node, haversine_km(lat, lon, nlat, nlon)))
    ranked.sort(key=lambda item: item[1])
    return ranked[:limit]


def coords_from_mapping(node: dict) -> tuple[float, float]:
    return float(node["lat"]), float(node["lon"])


KNOWN_CITIES: dict[str, tuple[float, float]] = {
    "ashburn": (39.0438, -77.4874),
    "atlanta": (33.7490, -84.3880),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "bangkok": (13.7563, 100.5018),
    "berlin": (52.5200, 13.4050),
    "boston": (42.3601, -71.0589),
    "chicago": (41.8781, -87.6298),
    "dallas": (32.7767, -96.7970),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "dublin": (53.3498, -6.2603),
    "frankfurt": (50.1109, 8.6821),
    "hyderabad": (17.3850, 78.4867),
    "kochi": (9.9312, 76.2673),
    "london": (51.5074, -0.1278),
    "los angeles": (34.0522, -118.2437),
    "miami": (25.7617, -80.1918),
    "mumbai": (19.0760, 72.8777),
    "new york": (40.7128, -74.0060),
    "paris": (48.8566, 2.3522),
    "san francisco": (37.7749, -122.4194),
    "sao paulo": (-23.5558, -46.6396),
    "são paulo": (-23.5558, -46.6396),
    "seattle": (47.6062, -122.3321),
    "seoul": (37.5665, 126.9780),
    "singapore": (1.3521, 103.8198),
    "stockholm": (59.3293, 18.0686),
    "sydney": (-33.8688, 151.2093),
    "tokyo": (35.6762, 139.6503),
    "toronto": (43.6532, -79.3832),
    "trivandrum": (8.5241, 76.9366),
    "thiruvananthapuram": (8.5241, 76.9366),
    "washington": (38.9072, -77.0369),
    "zurich": (47.3769, 8.5417),
}


def resolve_city(name: str) -> tuple[float, float]:
    key = name.strip().lower()
    if key not in KNOWN_CITIES:
        raise KeyError(
            f"Unknown city '{name}'. Pass lat/lon query params or use a known city name."
        )
    return KNOWN_CITIES[key]


def parse_limit(raw: int | None, default: int = 5, maximum: int = 25) -> int:
    if raw is None:
        return default
    return max(1, min(int(raw), maximum))
