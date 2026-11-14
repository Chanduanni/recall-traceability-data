# Reproducibility Check

Generator run twice with seed 20261022. Row counts and SHA-256 checksums compared.

| File | Rows (run 1) | Rows (run 2) | SHA-256 run 1 | SHA-256 run 2 | Match |
|---|---|---|---|---|---|
| bom.csv | 59 | 59 | b9c0e7e9933edbc8 | b9c0e7e9933edbc8 | YES |
| customers.csv | 1000 | 1000 | e67832b64ef5df44 | e67832b64ef5df44 | YES |
| deliveries.csv | 20000 | 20000 | 831a005be120f3de | 831a005be120f3de | YES |
| finished_lots.csv | 8000 | 8000 | 632746aa329a4d8c | 632746aa329a4d8c | YES |
| ground_truth.csv | 146 | 146 | 07967d6bb6abb09b | 07967d6bb6abb09b | YES |
| lot_status_events.csv | 33478 | 33478 | a0f73cdebe8e04c9 | a0f73cdebe8e04c9 | YES |
| material_lots.csv | 10000 | 10000 | c41a6e68f8b07bfb | c41a6e68f8b07bfb | YES |
| production_consumption.csv | 14758 | 14758 | 5f4fbcb49d55ceca | 5f4fbcb49d55ceca | YES |
| production_orders.csv | 5000 | 5000 | 175e2b65ab4ccfd7 | 175e2b65ab4ccfd7 | YES |
| products.csv | 20 | 20 | cffef765b6eaa961 | cffef765b6eaa961 | YES |
| recall_actions.csv | 820 | 820 | ed5deb84a0531d7c | ed5deb84a0531d7c | YES |
| recall_cases.csv | 66 | 66 | fef56cc795c1b4ff | fef56cc795c1b4ff | YES |
| shipments.csv | 9538 | 9538 | d41dcf3f7ff7916b | d41dcf3f7ff7916b | YES |
| suppliers.csv | 500 | 500 | 965f1a2d46bf84ee | 965f1a2d46bf84ee | YES |

Result: 14 of 14 files identical. REPRODUCIBLE
