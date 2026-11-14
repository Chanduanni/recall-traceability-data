# recall-traceability-data

# Recall Traceability: Synthetic Data Generator

A Python tool that generates a synthetic supply-chain dataset (supplier → raw lot → production → finished lot → shipment → customer delivery), plants labelled anomalies, traces affected lots downstream for product recalls, and validates the result against a separate ground-truth file.

Fixed seed: **20261022**. Standard library only, no external data, no dependencies.

## What problem this solves
A supplier ships a bad raw material lot. That lot goes into production orders, becomes finished lots, is shipped to warehouses and delivered to customers. This project builds the data for that whole chain, traces which customers are affected by a recall, simulates the recall actions (notified, quarantined, recovered), and measures how complete the recall was.

## Requirements
- Python 3.10 or newer (developed and tested on Python 3.14, Windows)
- No packages to install

## How to run
Windows (PowerShell):

````
py -m venv venv
.\venv\Scripts\Activate.ps1
py generate_data.py
py validate_data.py
py export_sql.py
py verify_reproducibility.py
````

On macOS or Linux use `python3` instead of `py`, and `source venv/bin/activate` to activate.

| Command | What it does |
|---|---|
| `py generate_data.py` | Full-size dataset into `data/` and `ground_truth/` |
| `py validate_data.py` | Integrity checks, anomaly comparison, writes `docs/VALIDATION_SUMMARY.md` |
| `py export_sql.py` | Writes `data/seed.sql` (schema with primary and foreign keys, plus data) |
| `py verify_reproducibility.py` | Runs the generator twice, compares row counts and SHA-256, writes `docs/REPRODUCIBILITY.md` |

Generator options: `--scale 0.1` (shrinks all volumes together, for a quick test), `--seed`, `--out`, `--truth-out`. The starter and full datasets use the same generator. The generator takes about 10 to 30 seconds at full scale.

## Volumes (default, scale 1.0)
| Entity | Rows |
|---|---|
| Suppliers | 500 |
| Raw material lots | 10,000 |
| Production orders | 5,000 |
| Finished lots | 8,000 |
| Deliveries | 20,000 |
| Customers | 1,000 |

Other tables (BOM, consumption, shipments, recall cases and actions, status events) are derived from these. Exact counts are in `docs/SOURCE_MANIFEST.md`.

## How the data is built
1. Master data first: Supplier, Product, BOM, Customer.
2. Raw lots with IDs like `RAWLOT-S017-2026-000001`. Some suppliers deliver more than others.
3. Production orders consume raw lots according to the BOM (bridge table `production_consumption`). Produced quantity is **derived** from the kg actually consumed, never drawn randomly.
4. Each order yields 1 or more finished lots. Each lot ships in 1 or 2 shipments. Each shipment is split exactly into customer deliveries.
5. Recalls: 0.5% of used raw lots (contamination) and 0.2% of finished lots (quality defect) are planted as sources. The generator traces downstream (raw lot → work orders → finished lots → shipments → deliveries), opens `REC-2026-xxxxxx` cases, and creates `NOTIFY`, `QUARANTINE` and `RECOVER` actions with affected and recovered quantities.
6. Status changes are stored as append-only rows in `lot_status_events`. History is never overwritten.
7. Edge cases are injected after the clean data is built, and each one is recorded in `ground_truth/ground_truth.csv`.

IDs: `RAWLOT-<supplier-id>-2026-000001`, `WO-2026-000001`, `FINLOT-2026-000001`, `SHP-2026-000001`, `REC-2026-000001` (plus `DEL-`, `ACT-`, `CON`, `EVT` for the supporting tables).

## Relationships
| Parent | Child | Cardinality |
|---|---|---|
| Supplier | MaterialLot | 1 : N |
| Product | BOM, ProductionOrder | 1 : N |
| ProductionOrder and MaterialLot | production_consumption (bridge) | N : M |
| ProductionOrder | FinishedLot | 1 : N |
| FinishedLot | Shipment | 1 : N |
| Shipment | Delivery | 1 : N |
| Customer | Delivery | 1 : N |
| RecallCase | RecallAction | 1 : N |
| Delivery | RecallAction | 1 : N |

Lifecycle states: raw lot `RECEIVED → CONSUMED → RECALLED`; finished lot `CREATED → SHIPPED → RECALLED`. Full field definitions are in `docs/DATA_DICTIONARY.md`.

## Planted edge cases (labelled in ground truth)
| issue_type | Meaning |
|---|---|
| MISSING_INPUT_LOT | A consumption row points to a raw lot that does not exist |
| DELIVERED_EXCEEDS_PRODUCED | A delivery quantity is inflated so a lot's deliveries exceed its produced quantity |
| RECALLED_STILL_AVAILABLE | Recalled, quarantined stock is flipped back to `AVAILABLE_FOR_SALE` |
| RECALL_MISSED_CUSTOMER | A downstream delivery's recall actions are removed (the customer is never notified) |
| CONTAMINATED_SOURCE_LOT | The planted contaminated lots that trigger the recalls |

`ground_truth/ground_truth.csv` is read only by `validate_data.py` to score detection. The generator's normal logic and the integrity checks never use it.

## How I know it works
`validate_data.py` runs 75 integrity checks: primary-key uniqueness, foreign keys, ID formats, allowed values, positive quantities, date ordering, quantity reconciliation, lifecycle transitions and duplicates. It then finds the planted anomalies on its own and compares them with the ground truth. It exits with code 0 only if every check passes and every planted anomaly is found, so it also serves as the project's test.

Results on the full dataset:

| Result | Value |
|---|---|
| Integrity checks | 75 run, 0 failed |
| Planted anomalies | 146 planted, 146 matched, 0 missed, 0 false alarms |
| Recall cases | 66 |
| Deliveries in recall scope | 430, across 344 customers |
| Deliveries with a notification | 410 (95.3%); the rest are the planted missed-customer cases |
| Affected quantity (units) | 44,616 |
| Recovered or quarantined (units) | 34,605 (77.6%) |
| Recall cases closed | 9 |

The full report is in `docs/VALIDATION_SUMMARY.md`.

## Reproducibility
`verify_reproducibility.py` generates the full dataset twice with seed 20261022 and compares row counts and SHA-256 checksums. Result: all 14 files are identical (see `docs/REPRODUCIBILITY.md`).

## Repository layout
````
generate_data.py            generator, recall trace, recall actions, edge-case injection
validate_data.py            integrity checks, anomaly detection vs ground truth, recall metrics
export_sql.py               builds data/seed.sql with primary and foreign keys
verify_reproducibility.py   two-run checksum comparison
data/                       CSV files and seed.sql
ground_truth/              ground_truth.csv (labels for planted anomalies)
docs/                       DATA_DICTIONARY, ASSUMPTIONS, SOURCE_MANIFEST, VALIDATION_SUMMARY, REPRODUCIBILITY
ai_usage/                   PROMPT_HISTORY and AI_USAGE_NOTE
````

## Data provenance
No external or public data is used. All records are synthetic and generated by the code in this repository, so there are no licensing or personal-data concerns. See `docs/SOURCE_MANIFEST.md`.

## AI use
I used Claude (a chat assistant) to help plan and write the code. All prompts are in `ai_usage/PROMPT_HISTORY.md`, and what AI did versus what I checked myself is in `ai_usage/AI_USAGE_NOTE.md`.

## Limitations
Assumptions, design decisions and known limitations are in `docs/ASSUMPTIONS.md`.