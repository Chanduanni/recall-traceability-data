# Assumptions, Decisions and Limitations

## Business assumptions
- **Time line (2026):** raw lots are received Jan to Jun; production runs Jul 1 to Sep 15; shipments and deliveries follow; recalls open Oct 10 to Oct 31.
- **BOM:** each of the 20 products uses 2 to 4 of 10 materials. One BOM version per product, effective from 2025-01-01, with no end date. BOM versioning is not simulated.
- **Production:** each work order consumes one raw lot per BOM material. A raw lot can feed several work orders. Produced units = the smallest whole number that every material's consumed kg supports (kg consumed / kg per unit). There is no scrap or yield loss.
- **Order status:** every generated order is COMPLETED. CANCELLED is allowed in the dictionary but not generated.
- **Distribution:** a work order makes 1 or more finished lots (8,000 lots from 5,000 orders). About 20% of finished lots ship in two parts. Each shipment is split exactly into one or more customer deliveries (20,000 in total). A warehouse is an attribute of the shipment; there is no separate inventory table.
- **Unequal volumes:** suppliers and customers have random weights, so some deliver or receive far more than others.

## Recall logic
- **Triggers:** 0.5% of used raw lots (contamination) and 0.2% of finished lots (quality defect) are chosen as planted sources, with a minimum of 3 raw lots and 1 finished lot.
- **Scope:** recalling a raw lot recalls every finished lot made in every work order that consumed it. This is conservative: the scope is the whole lot, not a proportion.
- **Overlap:** a delivery reached by two recalls is handled once, by the first recall.
- **Actions:** every affected delivery gets a NOTIFY action. Unsold stock (AVAILABLE_FOR_SALE) is QUARANTINED in full and set to BLOCKED. Sold stock gets a RECOVER action, with the recovered share drawn from 100%, 100%, 80%, 50% or 0%. A recall case is CLOSED only if every action is fully recovered.
- **History:** status changes (RECEIVED, CONSUMED, CREATED, SHIPPED, RECALLED) are written as append-only rows in `lot_status_events`. QUARANTINED is allowed for raw lots but the generator moves recalled lots straight to RECALLED.

## Edge cases (injected after clean data, always labelled)
- The count of each type is the larger of 2 and 0.25% of finished lots (20 at full scale).
- MISSING_INPUT_LOT replaces a consumption row's raw lot with a lot ID that does not exist; the original lot ID is kept in the ground-truth text.
- DELIVERED_EXCEEDS_PRODUCED inflates one delivery by at least 5 units or 10% of the lot.
- RECALLED_STILL_AVAILABLE flips quarantined stock back to AVAILABLE_FOR_SALE.
- RECALL_MISSED_CUSTOMER removes the NOTIFY and RECOVER actions for a delivery that is downstream of a recall.
- Ground truth is kept in a separate file and is used only by `validate_data.py`.

## Known limitations
- The recall case status (OPEN or CLOSED) is set before the edge cases are injected, so it is not recomputed for the two cases that lost actions to a planted anomaly.
- Injected anomalies change the data tables but do not add matching history events.
- Carriers and transport are not modelled; the warehouse is only a label on the shipment.
- Recovery percentages are simulated, not derived from any real behaviour.
- Notifications are stored as NOTIFY actions, not in a separate table.
- The generator was tested at scale 0.1 and 1.0. Very small scales can fail with a clear "not enough raw material" error.
- There is no automated test framework; `validate_data.py` (75 checks plus anomaly comparison) is the verification, and it exits non-zero on failure.
- No external or public data is used, so there are no licence issues.