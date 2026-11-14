"""Synthetic recall-traceability data generator (standard library only)."""
import argparse
import csv
import os
import random
from datetime import date, timedelta

SEED = 20261022

# Full-size volumes. --scale shrinks or grows all of them together.
BASE = {
    "suppliers": 500,
    "raw_lots": 10000,
    "orders": 5000,
    "finished_lots": 8000,
    "deliveries": 20000,
    "customers": 1000,
}

COUNTRIES = ["IN", "US", "DE", "CN", "MX"]
REGIONS = ["NORTH", "SOUTH", "EAST", "WEST"]
MATERIALS = [f"MAT{i:02d}" for i in range(1, 11)]


# ---- helpers ----
def rand_date(rng, start, end):
    return start + timedelta(days=rng.randint(0, (end - start).days))


def write_csv(folder, name, rows):
    if not rows:
        return
    path = os.path.join(folder, name + ".csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def add_event(events, lot_id, old_status, new_status, event_date):
    """History is only ever appended, never edited."""
    events.append({
        "event_id": f"EVT{len(events) + 1:06d}",
        "lot_id": lot_id,
        "old_status": old_status,
        "new_status": new_status,
        "event_date": event_date,
    })


# ---- master data ----
def build_master(rng, n_suppliers, n_customers):
    suppliers = []
    for i in range(1, n_suppliers + 1):
        suppliers.append({
            "supplier_id": f"S{i:03d}",
            "name": f"Supplier {i:03d} Ltd",
            "country": rng.choice(COUNTRIES),
            "status": rng.choices(["ACTIVE", "SUSPENDED"], weights=[95, 5])[0],
            "onboarded_date": rand_date(rng, date(2018, 1, 1), date(2025, 12, 31)).isoformat(),
        })

    products = []
    for i in range(1, 21):
        products.append({"product_id": f"P{i:03d}", "name": f"Product {i:03d}", "unit": "EA"})

    boms = []
    n = 0
    for p in products:
        for mat in rng.sample(MATERIALS, rng.randint(2, 4)):
            n += 1
            boms.append({
                "bom_id": f"BOM{n:04d}",
                "product_id": p["product_id"],
                "material_code": mat,
                "qty_per_unit_kg": round(rng.uniform(0.2, 2.0), 2),
                "effective_from": "2025-01-01",
                "effective_to": "",
            })

    customers = []
    for i in range(1, n_customers + 1):
        customers.append({
            "customer_id": f"C{i:04d}",
            "name": f"Customer {i:04d} Pvt Ltd",
            "region": rng.choice(REGIONS),
        })

    return suppliers, products, boms, customers


# ---- raw material lots ----
def build_raw_lots(rng, suppliers, n_lots, events):
    # Some suppliers deliver more often than others (realistic variation).
    weights = [rng.uniform(0.2, 3.0) for _ in suppliers]
    lots = []
    for i in range(1, n_lots + 1):
        s = rng.choices(suppliers, weights=weights)[0]
        received = rand_date(rng, date(2026, 1, 1), date(2026, 6, 30))
        lot = {
            "raw_lot_id": f"RAWLOT-{s['supplier_id']}-2026-{i:06d}",
            "supplier_id": s["supplier_id"],
            "material_code": rng.choice(MATERIALS),
            "received_date": received,
            "quantity_kg": round(rng.uniform(3000, 10000), 1),
            "status": "RECEIVED",
        }
        lots.append(lot)
        add_event(events, lot["raw_lot_id"], "", "RECEIVED", received)
    return lots


# ---- production ----
def pick_lot(rng, candidates, remaining, need):
    """Pick a raw lot of the right material that still has enough kg."""
    for _ in range(50):
        lot = rng.choice(candidates)
        if remaining[lot["raw_lot_id"]] >= need:
            return lot
    for lot in candidates:
        if remaining[lot["raw_lot_id"]] >= need:
            return lot
    raise RuntimeError("Not enough raw material. Use a larger raw-lot count.")


def build_production(rng, products, boms, raw_lots, n_orders, n_fin, events):
    bom_by_product = {}
    for b in boms:
        bom_by_product.setdefault(b["product_id"], []).append(b)

    lots_by_material = {}
    for lot in raw_lots:
        lots_by_material.setdefault(lot["material_code"], []).append(lot)
    for mat in MATERIALS:
        if mat not in lots_by_material:
            raise RuntimeError("No raw lots for " + mat + ". Use a larger --scale.")

    remaining = {lot["raw_lot_id"]: lot["quantity_kg"] for lot in raw_lots}
    first_use = {}

    # How many finished lots each order produces (at least 1).
    n_fin = max(n_fin, n_orders)
    lots_per_order = [1] * n_orders
    for _ in range(n_fin - n_orders):
        lots_per_order[rng.randrange(n_orders)] += 1

    orders, consumption, finished = [], [], []
    con_n = 0
    fin_n = 0

    for w in range(1, n_orders + 1):
        product = rng.choice(products)
        start = rand_date(rng, date(2026, 7, 1), date(2026, 9, 15))
        end = start + timedelta(days=rng.randint(1, 7))
        planned_units = rng.randint(100, 800)
        wo_id = f"WO-2026-{w:06d}"
        orders.append({
            "work_order_id": wo_id,
            "product_id": product["product_id"],
            "start_date": start,
            "end_date": end,
            "status": "COMPLETED",
        })

        # Consume raw lots according to the BOM.
        used = []  # (qty_per_unit_kg, kg_consumed)
        for b in bom_by_product[product["product_id"]]:
            need = round(planned_units * b["qty_per_unit_kg"], 2)
            lot = pick_lot(rng, lots_by_material[b["material_code"]], remaining, need)
            lot_id = lot["raw_lot_id"]
            remaining[lot_id] = round(remaining[lot_id] - need, 2)
            con_n += 1
            consumption.append({
                "consumption_id": f"CON{con_n:06d}",
                "work_order_id": wo_id,
                "raw_lot_id": lot_id,
                "qty_consumed_kg": need,
            })
            used.append((b["qty_per_unit_kg"], need))
            if lot_id not in first_use or start < first_use[lot_id]:
                first_use[lot_id] = start

        # Produced quantity is DERIVED from the kg actually consumed and the BOM.
        produced_total = min(int((kg + 0.005) / q) for q, kg in used)

        # Split into finished lots.
        k = lots_per_order[w - 1]
        cuts = sorted(rng.sample(range(1, produced_total), k - 1)) if k > 1 else []
        points = [0] + cuts + [produced_total]
        for a, z in zip(points, points[1:]):
            fin_n += 1
            produced_date = end + timedelta(days=rng.randint(0, 2))
            lot = {
                "finished_lot_id": f"FINLOT-2026-{fin_n:06d}",
                "work_order_id": wo_id,
                "product_id": product["product_id"],
                "produced_qty": z - a,
                "produced_date": produced_date,
                "status": "CREATED",
            }
            finished.append(lot)
            add_event(events, lot["finished_lot_id"], "", "CREATED", produced_date)

    # Raw lots that were used move to CONSUMED (history event is added).
    for lot in raw_lots:
        if lot["raw_lot_id"] in first_use:
            add_event(events, lot["raw_lot_id"], "RECEIVED", "CONSUMED", first_use[lot["raw_lot_id"]])
            lot["status"] = "CONSUMED"

    return orders, consumption, finished


# ---- MAIN ----
# ---- shipments and deliveries ----
WAREHOUSES = ["WH-A", "WH-B", "WH-C"]


def split_qty(rng, total, parts):
    """Split an integer into `parts` positive integers that add up exactly."""
    if parts <= 1:
        return [total]
    cuts = sorted(rng.sample(range(1, total), parts - 1))
    points = [0] + cuts + [total]
    return [b - a for a, b in zip(points, points[1:])]


def build_distribution(rng, finished, customers, n_deliveries, events):
    # Shipments: most finished lots ship once, about 20% ship in two parts.
    shipments = []
    ship_n = 0
    first_ship = {}
    for lot in finished:
        qty = lot["produced_qty"]
        parts = 2 if (qty >= 2 and rng.random() < 0.2) else 1
        for q in split_qty(rng, qty, parts):
            ship_n += 1
            ship_date = lot["produced_date"] + timedelta(days=rng.randint(0, 5))
            shipments.append({
                "shipment_id": f"SHP-2026-{ship_n:06d}",
                "finished_lot_id": lot["finished_lot_id"],
                "warehouse": rng.choice(WAREHOUSES),
                "ship_date": ship_date,
                "shipped_qty": q,
            })
            fid = lot["finished_lot_id"]
            if fid not in first_ship or ship_date < first_ship[fid]:
                first_ship[fid] = ship_date

    # How many deliveries each shipment gets (total = n_deliveries).
    n_ship = len(shipments)
    counts = [max(1, min(n_deliveries // n_ship, s["shipped_qty"])) for s in shipments]
    remainder = n_deliveries - sum(counts)
    tries = 0
    while remainder > 0 and tries < n_deliveries * 20:
        i = rng.randrange(n_ship)
        if counts[i] < shipments[i]["shipped_qty"]:
            counts[i] += 1
            remainder -= 1
        tries += 1

    # Deliveries: the shipped quantity is split exactly across the deliveries.
    cust_weights = [rng.uniform(0.2, 3.0) for _ in customers]
    deliveries = []
    del_n = 0
    for s, c in zip(shipments, counts):
        for q in split_qty(rng, s["shipped_qty"], c):
            del_n += 1
            deliveries.append({
                "delivery_id": f"DEL-2026-{del_n:06d}",
                "shipment_id": s["shipment_id"],
                "customer_id": rng.choices(customers, weights=cust_weights)[0]["customer_id"],
                "delivery_date": s["ship_date"] + timedelta(days=rng.randint(1, 10)),
                "delivered_qty": q,
                "sale_status": rng.choices(["SOLD", "AVAILABLE_FOR_SALE"], weights=[70, 30])[0],
            })

    # History: each finished lot moves CREATED -> SHIPPED.
    for lot in finished:
        add_event(events, lot["finished_lot_id"], "CREATED", "SHIPPED", first_ship[lot["finished_lot_id"]])
        lot["status"] = "SHIPPED"

    return shipments, deliveries


# ---- MAIN ----
# ---- recall: trace downstream, then act ----
RECALL_START = date(2026, 10, 10)
RECALL_END = date(2026, 10, 31)


def build_indexes(consumption, finished, shipments, deliveries):
    wo_by_raw = {}
    for c in consumption:
        wo_by_raw.setdefault(c["raw_lot_id"], set()).add(c["work_order_id"])
    fin_by_wo = {}
    for f in finished:
        fin_by_wo.setdefault(f["work_order_id"], []).append(f["finished_lot_id"])
    ship_by_fin = {}
    for s in shipments:
        ship_by_fin.setdefault(s["finished_lot_id"], []).append(s["shipment_id"])
    del_by_ship = {}
    for d in deliveries:
        del_by_ship.setdefault(d["shipment_id"], []).append(d)
    return wo_by_raw, fin_by_wo, ship_by_fin, del_by_ship


def trace_downstream(trigger_type, lot_id, idx):
    """Genealogy walk: raw lot -> work orders -> finished lots -> shipments -> deliveries."""
    wo_by_raw, fin_by_wo, ship_by_fin, del_by_ship = idx
    if trigger_type == "RAW_LOT":
        fin_ids = []
        for wo in sorted(wo_by_raw.get(lot_id, [])):
            fin_ids.extend(fin_by_wo.get(wo, []))
    else:
        fin_ids = [lot_id]
    scope = []
    for fid in fin_ids:
        for sid in ship_by_fin.get(fid, []):
            scope.extend(del_by_ship.get(sid, []))
    return fin_ids, scope


def build_recalls(rng, raw_lots, finished, consumption, shipments, deliveries, events):
    idx = build_indexes(consumption, finished, shipments, deliveries)
    raw_by_id = {l["raw_lot_id"]: l for l in raw_lots}
    fin_by_id = {f["finished_lot_id"]: f for f in finished}

    n_raw = max(3, int(len(raw_lots) * 0.005))
    n_fin = max(1, int(len(finished) * 0.002))

    # Planted contaminated sources: raw lots that were really used, plus a few finished lots.
    used_raw = [l for l in raw_lots if l["status"] == "CONSUMED"]
    triggers = [("RAW_LOT", l["raw_lot_id"]) for l in rng.sample(used_raw, n_raw)]

    in_scope = set()
    for _, lot_id in triggers:
        in_scope.update(trace_downstream("RAW_LOT", lot_id, idx)[0])
    free_fin = [f for f in finished if f["finished_lot_id"] not in in_scope]
    triggers += [("FINISHED_LOT", f["finished_lot_id"]) for f in rng.sample(free_fin, n_fin)]

    cases, actions, truth = [], [], []
    handled = set()  # a delivery is handled by the first recall that reaches it
    act_n = 0

    for r, (ttype, lot_id) in enumerate(triggers, start=1):
        rec_id = f"REC-2026-{r:06d}"
        opened = rand_date(rng, RECALL_START, RECALL_END)
        case = {
            "recall_id": rec_id,
            "trigger_type": ttype,
            "trigger_lot_id": lot_id,
            "reason": "CONTAMINATION" if ttype == "RAW_LOT" else "QUALITY_DEFECT",
            "opened_date": opened,
            "status": "OPEN",
        }
        cases.append(case)

        fin_ids, scope = trace_downstream(ttype, lot_id, idx)

        # Status changes are saved as history events.
        if ttype == "RAW_LOT":
            raw = raw_by_id[lot_id]
            add_event(events, lot_id, raw["status"], "RECALLED", opened)
            raw["status"] = "RECALLED"
        for fid in fin_ids:
            f = fin_by_id[fid]
            if f["status"] != "RECALLED":
                add_event(events, fid, f["status"], "RECALLED", opened)
                f["status"] = "RECALLED"

        all_done = True
        for d in scope:
            if d["delivery_id"] in handled:
                continue
            handled.add(d["delivery_id"])
            qty = d["delivered_qty"]
            first_date = opened + timedelta(days=rng.randint(0, 3))

            # Action 1: notify the customer.
            act_n += 1
            actions.append({
                "action_id": f"ACT-2026-{act_n:06d}",
                "recall_id": rec_id,
                "delivery_id": d["delivery_id"],
                "action_type": "NOTIFY",
                "affected_qty": qty,
                "recovered_qty": 0,
                "disposition": "PENDING",
                "action_date": first_date,
            })

            # Action 2: quarantine unsold stock, or try to recover sold stock.
            if d["sale_status"] == "AVAILABLE_FOR_SALE":
                kind, got = "QUARANTINE", qty
                d["sale_status"] = "BLOCKED"
            else:
                kind, got = "RECOVER", int(qty * rng.choice([1.0, 1.0, 0.8, 0.5, 0.0]))
            if got == qty:
                disp = "RECOVERED"
            elif got > 0:
                disp = "PARTIAL"
            else:
                disp = "PENDING"
            if disp != "RECOVERED":
                all_done = False
            act_n += 1
            actions.append({
                "action_id": f"ACT-2026-{act_n:06d}",
                "recall_id": rec_id,
                "delivery_id": d["delivery_id"],
                "action_type": kind,
                "affected_qty": qty,
                "recovered_qty": got,
                "disposition": disp,
                "action_date": first_date + timedelta(days=rng.randint(0, 5)),
            })

        case["status"] = "CLOSED" if all_done else "OPEN"
        truth.append({
            "record_id": lot_id,
            "table_name": "material_lots" if ttype == "RAW_LOT" else "finished_lots",
            "issue_type": "CONTAMINATED_SOURCE_LOT",
            "expected_decision": f"Recall all {len(scope)} downstream deliveries under {rec_id}",
        })

    return cases, actions, truth


# ---- MAIN ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="data")
    ap.add_argument("--truth-out", default="ground_truth")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    n = {k: max(1, int(v * args.scale)) for k, v in BASE.items()}
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.truth_out, exist_ok=True)

    events = []
    suppliers, products, boms, customers = build_master(rng, n["suppliers"], n["customers"])
    raw_lots = build_raw_lots(rng, suppliers, n["raw_lots"], events)
    orders, consumption, finished = build_production(
        rng, products, boms, raw_lots, n["orders"], n["finished_lots"], events)
    shipments, deliveries = build_distribution(
        rng, finished, customers, n["deliveries"], events)
    recall_cases, recall_actions, truth = build_recalls(
        rng, raw_lots, finished, consumption, shipments, deliveries, events)

    tables = [
        ("suppliers", suppliers), ("products", products), ("bom", boms),
        ("customers", customers), ("material_lots", raw_lots),
        ("production_orders", orders), ("production_consumption", consumption),
        ("finished_lots", finished), ("shipments", shipments),
        ("deliveries", deliveries), ("recall_cases", recall_cases),
        ("recall_actions", recall_actions), ("lot_status_events", events),
    ]
    for name, rows in tables:
        write_csv(args.out, name, rows)
        print(f"{name}: {len(rows)} rows")

    write_csv(args.truth_out, "ground_truth", truth)
    print(f"ground_truth: {len(truth)} rows")


if __name__ == "__main__":
    main()