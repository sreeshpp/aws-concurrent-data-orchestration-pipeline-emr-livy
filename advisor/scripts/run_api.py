#!/usr/bin/env python3
"""Run the catalog read API (uvicorn)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import uvicorn


def main() -> None:
    uvicorn.run(
        "aws_region_advisor.api:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )


if __name__ == "__main__":
    main()
