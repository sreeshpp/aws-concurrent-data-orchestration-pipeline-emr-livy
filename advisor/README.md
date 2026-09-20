# AWS Region & Edge Advisor

Phase 1 **infrastructure catalog**: Regions, Availability Zones, Local Zones, Wavelength Zones, CloudFront edge PoPs, and regional edge caches — with a read API and closest-node queries.

Scoring / questionnaire UI is Phase 2 (see [docs/aws-region-edge-advisor-plan.md](../docs/aws-region-edge-advisor-plan.md)).

## Quick start

```bash
cd advisor
pip install -r requirements.txt

# Build unified catalog from curated seed data
python scripts/build_catalog.py

# Run read API on :8080
python scripts/run_api.py
```

### Useful endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/v1/catalog/meta` | Version, as-of, counts |
| GET | `/v1/catalog` | Full catalog JSON |
| GET | `/v1/regions` | Commercial Regions |
| GET | `/v1/edge` | CloudFront edge PoP cities |
| GET | `/v1/nodes?type=local_zone` | Filter by type |
| GET | `/v1/closest?city=Mumbai&type=edge_pop&limit=5` | Nearest nodes |
| GET | `/v1/closest?lat=9.93&lon=76.27&type=region` | Nearest by coordinates |

Examples:

```bash
curl -s localhost:8080/v1/catalog/meta | python -m json.tool
curl -s 'localhost:8080/v1/closest?city=Kochi&type=edge_pop&limit=3' | python -m json.tool
curl -s 'localhost:8080/v1/nodes?type=region&country=IN' | python -m json.tool
```

## Data sources

| Layer | How it is populated |
|-------|---------------------|
| Regions + synthetic AZs | Curated seed from AWS Regions docs |
| Local Zones / Wavelength | Representative curated seed |
| Edge PoPs | Curated city list from CloudFront features page + coordinates |
| Regional edge caches | Representative REC list |
| Live AZs / Local / Wavelength | Optional: `python scripts/build_catalog.py --sync-aws` (needs AWS credentials) |

Compliance and privacy tags on Regions are **guidance only**, not legal certification. Edge locations are **city-level**, not physical street addresses.

## Layout

```
advisor/
  data/seed/          # curated JSON inputs
  data/catalog.json   # generated unified catalog
  src/aws_region_advisor/
  scripts/build_catalog.py
  scripts/run_api.py
  tests/
```

## Tests

```bash
cd advisor
PYTHONPATH=src pytest -q
```
