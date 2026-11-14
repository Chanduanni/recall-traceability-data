# Source Manifest

## External data
None. No public, third-party or confidential data is used. Every record is synthetic and created by `generate_data.py`.
Source URL, dataset version, retrieval date, license and transformations: not applicable.

## How the data was produced
- Generator command: `py generate_data.py` (full scale)
- Fixed seed: 20261022
- Language: Python (standard library only)
- Reproducibility: two runs gave identical files (see `REPRODUCIBILITY.md`)

## Generated files
| File | Rows |
|---|---|
| data/suppliers.csv | 500 |
| data/products.csv | 20 |
| data/bom.csv | 59 |
| data/customers.csv | 1000 |
| data/material_lots.csv | 10000 |
| data/production_orders.csv | 5000 |
| data/production_consumption.csv | 14758 |
| data/finished_lots.csv | 8000 |
| data/shipments.csv | 9538 |
| data/deliveries.csv | 20000 |
| data/recall_cases.csv | 66 |
| data/recall_actions.csv | 820 |
| data/lot_status_events.csv | 33478 |
| ground_truth/ground_truth.csv | 146 |
| data/seed.sql | schema and data for the 13 tables above |

## Personal data
None. Names such as "Supplier 017 Ltd" and "Customer 0042 Pvt Ltd" are generated placeholders.