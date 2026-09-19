#!/usr/bin/env python3
"""Build catalog.json from seed data; optionally merge live AWS zone data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aws_region_advisor.catalog import (  # noqa: E402
    DEFAULT_CATALOG_PATH,
    DEFAULT_SEED_DIR,
    build_catalog_from_seed,
    merge_live_zones,
    write_catalog,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AWS infrastructure catalog")
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=DEFAULT_SEED_DIR,
        help="Directory containing seed JSON files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Output catalog.json path",
    )
    parser.add_argument(
        "--sync-aws",
        action="store_true",
        help="Merge live EC2 DescribeAvailabilityZones data (requires AWS credentials)",
    )
    parser.add_argument(
        "--regions",
        nargs="*",
        default=None,
        help="Optional region codes to sync (default: all commercial)",
    )
    args = parser.parse_args()

    catalog = build_catalog_from_seed(args.seed_dir)
    if args.sync_aws:
        from aws_region_advisor.sync_aws import sync_zones

        live = sync_zones(args.regions)
        catalog = merge_live_zones(catalog, live)

    path = write_catalog(catalog, args.out)
    counts = catalog.meta.counts
    print(f"Wrote {path}")
    print(f"source={catalog.meta.source} generated_at={catalog.meta.generated_at}")
    print("counts:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
