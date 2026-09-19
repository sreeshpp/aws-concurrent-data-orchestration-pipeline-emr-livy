"""Optional live sync from AWS EC2 APIs (requires credentials)."""

from __future__ import annotations

from typing import Any

from .models import Coordinates, InfrastructureNode


def _ec2_client(region_name: str = "us-east-1"):
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("boto3 is required for AWS sync") from exc
    return boto3.client("ec2", region_name=region_name)


def list_commercial_regions(ec2=None) -> list[dict[str, Any]]:
    client = ec2 or _ec2_client()
    resp = client.describe_regions(AllRegions=True)
    out = []
    for region in resp.get("Regions", []):
        name = region["RegionName"]
        # Skip gov/cn partitions exposed via wrong endpoints
        if name.startswith("us-gov-") or name.startswith("cn-"):
            continue
        out.append(
            {
                "code": name,
                "opt_in_status": region.get("OptInStatus"),
                "endpoint": region.get("Endpoint"),
            }
        )
    return out


def describe_zones_for_region(region_code: str) -> list[InfrastructureNode]:
    client = _ec2_client(region_code)
    resp = client.describe_availability_zones(AllAvailabilityZones=True)
    nodes: list[InfrastructureNode] = []
    for zone in resp.get("AvailabilityZones", []):
        ztype = zone.get("ZoneType") or "availability-zone"
        code = zone["ZoneName"]
        parent = zone.get("RegionName") or region_code
        opt_in = zone.get("OptInStatus")
        opt_in_required = opt_in in {"not-opted-in", "opted-in"} and ztype != "availability-zone"
        if ztype == "availability-zone":
            node_type = "az"
            capability = "availability_zone"
            node_id = f"az:{code}"
        elif ztype == "local-zone":
            node_type = "local_zone"
            capability = "local_zone_compute"
            node_id = f"local_zone:{code}"
            opt_in_required = True
        elif ztype == "wavelength-zone":
            node_type = "wavelength"
            capability = "mec_5g"
            node_id = f"wavelength:{code}"
            opt_in_required = True
        else:
            continue

        nodes.append(
            InfrastructureNode(
                id=node_id,
                type=node_type,  # type: ignore[arg-type]
                code=code,
                display_name=zone.get("GroupLongName") or code,
                parent_region_id=f"region:{parent}",
                country_codes=[],
                coordinates=None,
                opt_in_required=opt_in_required,
                partition="aws",
                capabilities=[capability],
                metadata={
                    "zone_id": zone.get("ZoneId"),
                    "group": zone.get("GroupName"),
                    "network_border_group": zone.get("NetworkBorderGroup"),
                    "state": zone.get("State"),
                    "opt_in_status": opt_in,
                    "parent_zone_name": zone.get("ParentZoneName"),
                    "parent_zone_id": zone.get("ParentZoneId"),
                    "live": True,
                },
            )
        )
    return nodes


def sync_zones(region_codes: list[str] | None = None) -> list[InfrastructureNode]:
    """Fetch AZs / Local Zones / Wavelength for each region. Needs AWS credentials."""
    if region_codes is None:
        region_codes = [r["code"] for r in list_commercial_regions()]
    all_nodes: list[InfrastructureNode] = []
    errors: list[str] = []
    for code in region_codes:
        try:
            all_nodes.extend(describe_zones_for_region(code))
        except Exception as exc:  # noqa: BLE001 — collect per-region failures
            errors.append(f"{code}: {exc}")
    if errors and not all_nodes:
        raise RuntimeError("AWS sync failed for all regions:\n" + "\n".join(errors))
    # Attach sync errors as empty; caller can log
    for node in all_nodes[:1]:
        node.metadata.setdefault("sync_errors", errors)
    return all_nodes


# Silence unused import warning for Coordinates re-export convenience
_ = Coordinates
