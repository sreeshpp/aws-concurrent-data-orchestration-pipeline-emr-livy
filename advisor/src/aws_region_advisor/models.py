"""Pydantic models for the infrastructure catalog."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

NodeType = Literal[
    "region",
    "az",
    "local_zone",
    "wavelength",
    "edge_pop",
    "regional_edge_cache",
]


class Coordinates(BaseModel):
    lat: float
    lon: float


class InfrastructureNode(BaseModel):
    id: str
    type: NodeType
    code: str
    display_name: str
    parent_region_id: str | None = None
    country_codes: list[str] = Field(default_factory=list)
    coordinates: Coordinates | None = None
    opt_in_required: bool = False
    partition: str = "aws"
    compliance_tags: list[str] = Field(default_factory=list)
    privacy_buckets: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CatalogMeta(BaseModel):
    version: str
    generated_at: str
    partition: str = "aws"
    source: str
    notes: str = ""
    sources: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class Catalog(BaseModel):
    meta: CatalogMeta
    nodes: list[InfrastructureNode]

    def by_type(self, node_type: NodeType) -> list[InfrastructureNode]:
        return [n for n in self.nodes if n.type == node_type]

    def get(self, node_id: str) -> InfrastructureNode | None:
        for node in self.nodes:
            if node.id == node_id or node.code == node_id:
                return node
        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
