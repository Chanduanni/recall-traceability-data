"""Validation for the recall-traceability dataset (standard library only).

Reads the CSV files, runs integrity checks, then compares the anomalies it
DETECTS with the separate ground_truth.csv. The truth file is used only here,
never by the generator's normal logic."""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

TABLES = ["suppliers", "products", "bom", "customers", "material_lots",
          "production_orders", "production_consumption", "finished_lots",
          "shipments", "deliveries", "recall_cases", "recall_actions",
          "lot_status_events"]

KEYS = {
    "suppliers": "supplier_id", "products": "product_id", "bom": "bom_id",
    "customers": "customer_id", "material_lots": "raw_lot_id",
    "production_orders": "work_order_id", "production_consumption": "consumption_id",
    "finished_lots": "finished_lot_id", "shipments": "shipment_id",
    "deliveries": "delivery_id", "recall_cases": "recall_id",
    "recall_actions": "action_id", "lot_status_events": "event_id",
}

MATS = {f"MAT{i:02d}" for i in range(1, 11)}
ENUMS = [
    ("suppliers", "country", {"IN", "US", "DE", "CN", "MX"}),
    ("suppliers", "status", {"ACTIVE", "SUSPENDED"}),
    ("products", "unit", {"EA"}),
    ("bom", "material_code", MATS),
    ("customers", "region", {"NORTH", "SOUTH", "EAST", "WEST"}),
    ("material_lots", "material_code", MATS),
    ("material_lots", "status", {"RECEIVED", "CONSUMED", "QUARANTINED", "RECALLED"}),
    ("production_orders", "status", {"COMPLETED", "CANCELLED"}),
    ("finished_lots", "status", {"CREATED", "SHIPPED", "RECALLED"}),
    ("shipments", "warehouse", {"WH-A", "WH-B", "WH-C"}),
    ("deliveries", "sale_status", {"AVAILABLE_FOR_SALE", "BLOCKED", "SOLD"}),
    ("recall_cases", "trigger_type", {"RAW_LOT", "FINISHED_LOT"}),
    ("recall_cases", "reason", {"CONTAMINATION", "QUALITY_DEFECT"}),
    ("recall_cases", "status", {"OPEN", "CLOSED"}),
    ("recall_actions", "action_type", {"NOTIFY", "QUARANTINE", "RECOVER"}),
    ("recall_actions", "disposition", {"RECOVERED", "PARTIAL", "PENDING"}),
]

ID_FORMATS = [
    ("material_lots", "raw_lot_id", r"RAWLOT-S\d{3}-2026-\d{6}"),
    ("production_orders", "work_order_id", r"WO-2026-\d{6}"),
    ("finished_lots", "finished_lot_id", r"FINLOT-2026-\d{6}"),
    ("shipments", "shipment_id", r"SHP-2026-\d{6}"),
    ("recall_cases", "recall_id", r"REC-2026-\d{6}"),
    ("deliveries", "delivery_id", r"DEL-2026-\d{6}"),
    ("recall_actions", "action_id", r"ACT-2026-\d{6}"),
]

POSITIVE = [
    ("material_lots", "quantity_kg"), ("bom", "qty_per_unit_kg"),
    ("production_consumption", "qty_consumed_kg"), ("finished_lots", "produced_qty"),
    ("shipments", "shipped_qty"), ("deliveries", "delivered_qty"),
    ("recall_actions", "affected_qty"),
]

FOREIGN_KEYS = [
    ("bom", "product_id", "products"),
    ("material_lots", "supplier_id", "suppliers"),
    ("production_orders", "product_id", "products"),
    ("production_consumption", "work_order_id", "production_orders"),
    ("finished_lots", "work_order_id", "production_orders"),
    ("finished_lots", "product_id", "products"),
    ("shipments", "finished_lot_id", "finished_lots"),
    ("deliveries", "shipment_id", "shipments"),
    ("deliveries", "customer_id", "customers"),
    ("recall_actions", "recall_id", "recall_cases"),
    ("recall_actions", "delivery_id", "deliveries"),
]

ALLOWED_TRANSITIONS = {
    ("", "RECEIVED"), ("RECEIVED", "CONSUMED"), ("RECEIVED", "RECALLED"),
    ("CONSUMED", "RECALLED"), ("", "CREATED"), ("CREATED", "SHIPPED"),
    ("CREATED", "RECALLED"), ("SHIPPED", "RECALLED"),
}

CHECKS = []     # (section, check, violations)
ANOMALIES = []  # (issue_type, planted, detected, matched, missed, false_alarms)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add(section, check, violations):
    CHECKS.append((section, check, violations))


def evaluate(label, detected, planted):
    ANOMALIES.append((label, len(planted), len(detected), len(detected & planted),
                      len(planted - detected), len(detected - planted)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--truth", default="ground_truth/ground_truth.csv")
    ap.add_argument("--report", default="docs/VALIDATION_SUMMARY.md")
    args = ap.parse_args()

    t = {name: read_csv(os.path.join(args.data, name + ".csv")) for name in TABLES}
    truth = read_csv(args.truth)

    # ---- 1. primary keys ----
    ids = {}
    for name in TABLES:
        seen, dups = set(), 0
        for r in t[name]:
            if r[KEYS[name]] in seen:
                dups += 1
            seen.add(r[KEYS[name]])
        ids[name] = seen
        add("Primary keys", f"{name}.{KEYS[name]} is unique", dups)

    # ---- 2. foreign keys ----
    for child, col, parent in FOREIGN_KEYS:
        bad = sum(1 for r in t[child] if r[col] not in ids[parent])
        add("Foreign keys", f"{child}.{col} -> {parent}", bad)
    all_lot_ids = ids["material_lots"] | ids["finished_lots"]
    bad = 0
    for c in t["recall_cases"]:
        parent = "material_lots" if c["trigger_type"] == "RAW_LOT" else "finished_lots"
        if c["trigger_lot_id"] not in ids[parent]:
            bad += 1
    add("Foreign keys", "recall_cases.trigger_lot_id -> its lot table", bad)
    add("Foreign keys", "lot_status_events.lot_id -> a lot",
        sum(1 for e in t["lot_status_events"] if e["lot_id"] not in all_lot_ids))
    order_by_id = {o["work_order_id"]: o for o in t["production_orders"]}
    add("Foreign keys", "finished lot product matches its work order product",
        sum(1 for f in t["finished_lots"]
            if f["product_id"] != order_by_id[f["work_order_id"]]["product_id"]))
    wo_with_consumption = {c["work_order_id"] for c in t["production_consumption"]}
    add("Foreign keys", "every finished lot's work order has consumption rows",
        sum(1 for f in t["finished_lots"] if f["work_order_id"] not in wo_with_consumption))
    # NOTE: production_consumption.raw_lot_id is checked in the anomaly section below.

    # ---- 3. ID formats ----
    for name, col, pattern in ID_FORMATS:
        add("ID formats", f"{name}.{col} matches {pattern}",
            sum(1 for r in t[name] if not re.fullmatch(pattern, r[col])))
    add("ID formats", "RAWLOT id supplier part equals supplier_id",
        sum(1 for r in t["material_lots"] if r["raw_lot_id"].split("-")[1] != r["supplier_id"]))

    # ---- 4. allowed values and positive numbers ----
    for name, col, allowed in ENUMS:
        add("Allowed values", f"{name}.{col} in allowed set",
            sum(1 for r in t[name] if r[col] not in allowed))
    for name, col in POSITIVE:
        add("Allowed values", f"{name}.{col} greater than 0",
            sum(1 for r in t[name] if float(r[col]) <= 0))
    add("Allowed values", "recall_actions recovered_qty between 0 and affected_qty",
        sum(1 for a in t["recall_actions"]
            if not (0 <= int(a["recovered_qty"]) <= int(a["affected_qty"]))))

    # ---- 5. date ordering ----
    raw_by_id = {r["raw_lot_id"]: r for r in t["material_lots"]}
    lot_by_id = {f["finished_lot_id"]: f for f in t["finished_lots"]}
    ship_by_id = {s["shipment_id"]: s for s in t["shipments"]}
    case_by_id = {c["recall_id"]: c for c in t["recall_cases"]}

    def date_check(name, pairs):
        add("Date ordering", name, sum(1 for earlier, later in pairs if later < earlier))

    date_check("production order: end_date >= start_date",
               [(o["start_date"], o["end_date"]) for o in t["production_orders"]])
    date_check("finished lot: produced_date >= work order end_date",
               [(order_by_id[f["work_order_id"]]["end_date"], f["produced_date"])
                for f in t["finished_lots"]])
    date_check("shipment: ship_date >= finished lot produced_date",
               [(lot_by_id[s["finished_lot_id"]]["produced_date"], s["ship_date"])
                for s in t["shipments"]])
    date_check("delivery: delivery_date >= ship_date",
               [(ship_by_id[d["shipment_id"]]["ship_date"], d["delivery_date"])
                for d in t["deliveries"]])
    date_check("recall action: action_date >= recall opened_date",
               [(case_by_id[a["recall_id"]]["opened_date"], a["action_date"])
                for a in t["recall_actions"]])
    date_check("raw lot received_date <= work order start_date (when consumed)",
               [(raw_by_id[c["raw_lot_id"]]["received_date"],
                 order_by_id[c["work_order_id"]]["start_date"])
                for c in t["production_consumption"] if c["raw_lot_id"] in raw_by_id])

    # ---- 6. reconciliation ----
    shipped_by_lot = defaultdict(int)
    for s in t["shipments"]:
        shipped_by_lot[s["finished_lot_id"]] += int(s["shipped_qty"])
    add("Reconciliation", "shipped quantity per lot equals produced_qty",
        sum(1 for f in t["finished_lots"]
            if shipped_by_lot[f["finished_lot_id"]] != int(f["produced_qty"])))

    delivered_by_lot = defaultdict(int)
    for d in t["deliveries"]:
        delivered_by_lot[ship_by_id[d["shipment_id"]]["finished_lot_id"]] += int(d["delivered_qty"])
    add("Reconciliation", "no lot has delivered quantity BELOW produced_qty",
        sum(1 for f in t["finished_lots"]
            if delivered_by_lot[f["finished_lot_id"]] < int(f["produced_qty"])))

    used_by_raw = defaultdict(float)
    for c in t["production_consumption"]:
        used_by_raw[c["raw_lot_id"]] += float(c["qty_consumed_kg"])
    add("Reconciliation", "raw lot kg consumed does not exceed quantity_kg",
        sum(1 for lot_id, kg in used_by_raw.items()
            if lot_id in raw_by_id and kg > float(raw_by_id[lot_id]["quantity_kg"]) + 0.05))

    bom_q = defaultdict(list)
    for b in t["bom"]:
        bom_q[b["product_id"]].append(float(b["qty_per_unit_kg"]))
    cons_kg = defaultdict(list)
    for c in t["production_consumption"]:
        cons_kg[c["work_order_id"]].append(float(c["qty_consumed_kg"]))
    produced_by_wo = defaultdict(int)
    for f in t["finished_lots"]:
        produced_by_wo[f["work_order_id"]] += int(f["produced_qty"])
    bad = 0
    for o in t["production_orders"]:
        qs, kgs = bom_q[o["product_id"]], cons_kg[o["work_order_id"]]
        if len(qs) != len(kgs):
            bad += 1
            continue
        expected = min(int((kg + 0.005) / q) for q, kg in zip(qs, kgs))
        if expected != produced_by_wo[o["work_order_id"]]:
            bad += 1
    add("Reconciliation", "produced_qty per work order equals the BOM-derived quantity", bad)

    # ---- 7. lifecycle ----
    chains = defaultdict(list)
    for e in t["lot_status_events"]:
        chains[e["lot_id"]].append(e)
    bad_trans = bad_dates = 0
    for evs in chains.values():
        prev = ""
        for e in evs:
            if e["old_status"] != prev or (e["old_status"], e["new_status"]) not in ALLOWED_TRANSITIONS:
                bad_trans += 1
            prev = e["new_status"]
        bad_dates += sum(1 for a, b in zip(evs, evs[1:]) if b["event_date"] < a["event_date"])
    add("Lifecycle", "every status change is an allowed transition", bad_trans)
    add("Lifecycle", "status event dates never go backwards", bad_dates)
    final = {lot: evs[-1]["new_status"] for lot, evs in chains.items()}
    add("Lifecycle", "lot table status equals the last history event",
        sum(1 for r in t["material_lots"] if final.get(r["raw_lot_id"]) != r["status"])
        + sum(1 for f in t["finished_lots"] if final.get(f["finished_lot_id"]) != f["status"]))

    # ---- 8. duplicates ----
    pairs = [(c["work_order_id"], c["raw_lot_id"]) for c in t["production_consumption"]]
    add("Duplicates", "no repeated (work order, raw lot) pair", len(pairs) - len(set(pairs)))
    trips = [(a["recall_id"], a["delivery_id"], a["action_type"]) for a in t["recall_actions"]]
    add("Duplicates", "no repeated (recall, delivery, action type)", len(trips) - len(set(trips)))

    # ---- 9. genealogy trace and anomaly detection (compared with ground truth) ----
    wo_by_raw = defaultdict(set)
    for c in t["production_consumption"]:
        wo_by_raw[c["raw_lot_id"]].add(c["work_order_id"])
    fin_by_wo = defaultdict(list)
    for f in t["finished_lots"]:
        fin_by_wo[f["work_order_id"]].append(f["finished_lot_id"])
    ship_by_fin = defaultdict(list)
    for s in t["shipments"]:
        ship_by_fin[s["finished_lot_id"]].append(s["shipment_id"])
    del_by_ship = defaultdict(list)
    for d in t["deliveries"]:
        del_by_ship[d["shipment_id"]].append(d["delivery_id"])

    scope = {}  # delivery_id -> recall_id (everything downstream of a recall trigger)
    for case in t["recall_cases"]:
        if case["trigger_type"] == "RAW_LOT":
            fins = [f for wo in sorted(wo_by_raw.get(case["trigger_lot_id"], []))
                    for f in fin_by_wo[wo]]
        else:
            fins = [case["trigger_lot_id"]]
        for fid in fins:
            for sid in ship_by_fin[fid]:
                for did in del_by_ship[sid]:
                    scope.setdefault(did, case["recall_id"])

    actions_by_delivery = defaultdict(list)
    for a in t["recall_actions"]:
        actions_by_delivery[a["delivery_id"]].append(a)

    planted = defaultdict(set)
    for row in truth:
        planted[row["issue_type"]].add(row["record_id"])

    evaluate("CONTAMINATED_SOURCE_LOT",
             {c["trigger_lot_id"] for c in t["recall_cases"]},
             planted["CONTAMINATED_SOURCE_LOT"])
    evaluate("MISSING_INPUT_LOT",
             {c["consumption_id"] for c in t["production_consumption"]
              if c["raw_lot_id"] not in ids["material_lots"]},
             planted["MISSING_INPUT_LOT"])
    evaluate("DELIVERED_EXCEEDS_PRODUCED",
             {f["finished_lot_id"] for f in t["finished_lots"]
              if delivered_by_lot[f["finished_lot_id"]] > int(f["produced_qty"])},
             planted["DELIVERED_EXCEEDS_PRODUCED"])
    recalled_lots = {f["finished_lot_id"] for f in t["finished_lots"] if f["status"] == "RECALLED"}
    evaluate("RECALLED_STILL_AVAILABLE",
             {d["delivery_id"] for d in t["deliveries"]
              if ship_by_id[d["shipment_id"]]["finished_lot_id"] in recalled_lots
              and d["sale_status"] == "AVAILABLE_FOR_SALE"},
             planted["RECALLED_STILL_AVAILABLE"])
    evaluate("RECALL_MISSED_CUSTOMER",
             {did for did in scope if not actions_by_delivery[did]},
             planted["RECALL_MISSED_CUSTOMER"])

    # ---- recall outcome metrics ----
    delivery_by_id = {d["delivery_id"]: d for d in t["deliveries"]}
    notified = sum(1 for did in scope
                   if any(a["action_type"] == "NOTIFY" for a in actions_by_delivery[did]))
    handled = [a for a in t["recall_actions"] if a["action_type"] != "NOTIFY"]
    affected = sum(int(a["affected_qty"]) for a in handled)
    recovered = sum(int(a["recovered_qty"]) for a in handled)
    customers = {delivery_by_id[did]["customer_id"] for did in scope}
    metrics = [
        ("Recall cases", len(t["recall_cases"])),
        ("Downstream deliveries in recall scope", len(scope)),
        ("Customers in recall scope", len(customers)),
        ("Deliveries with a notification", f"{notified} ({100 * notified / max(1, len(scope)):.1f}%)"),
        ("Affected quantity (units)", affected),
        ("Recovered / quarantined quantity (units)", recovered),
        ("Recovery rate", f"{100 * recovered / max(1, affected):.1f}%"),
        ("Recall cases CLOSED", sum(1 for c in t["recall_cases"] if c["status"] == "CLOSED")),
    ]

    # ---- print and write the report ----
    failed = [c for c in CHECKS if c[2] != 0]
    anomaly_bad = [a for a in ANOMALIES if a[4] or a[5]]

    lines = ["# Validation Summary", "",
             "Generated by `validate_data.py`. The ground truth file is used only for the anomaly comparison.", "",
             "## Integrity checks", "", "| Section | Check | Violations | Result |", "|---|---|---|---|"]
    for section, check, v in CHECKS:
        lines.append(f"| {section} | {check} | {v} | {'PASS' if v == 0 else 'FAIL'} |")
    lines += ["", "## Planted anomalies: detected vs ground truth", "",
              "| Issue type | Planted | Detected | Matched | Missed | False alarms |", "|---|---|---|---|---|---|"]
    for a in ANOMALIES:
        lines.append("| " + " | ".join(str(x) for x in a) + " |")
    lines += ["", "## Recall outcome metrics", "", "| Metric | Value |", "|---|---|"]
    for name, value in metrics:
        lines.append(f"| {name} | {value} |")
    lines += ["", "## Row counts", "", "| Table | Rows |", "|---|---|"]
    for name in TABLES:
        lines.append(f"| {name} | {len(t[name])} |")
    lines += ["", f"Overall: {'ALL CHECKS PASSED' if not failed and not anomaly_bad else 'VALIDATION FAILED'}"]

    os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Integrity checks run: {len(CHECKS)}, failed: {len(failed)}")
    for section, check, v in failed:
        print(f"  FAIL [{section}] {check}: {v}")
    print("Anomaly detection vs ground truth:")
    for label, p, d, m, miss, fa in ANOMALIES:
        print(f"  {label}: planted {p}, detected {d}, matched {m}, missed {miss}, false alarms {fa}")
    for name, value in metrics:
        print(f"  {name}: {value}")
    print("ALL CHECKS PASSED" if not failed and not anomaly_bad else "VALIDATION FAILED")
    sys.exit(0 if not failed and not anomaly_bad else 1)


if __name__ == "__main__":
    main()