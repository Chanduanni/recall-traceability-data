"""Load the CSV files into SQLite and export data/seed.sql (schema + data).
Foreign keys are declared but not enforced while loading, so the planted
MISSING_INPUT_LOT rows can exist; they are then reported by foreign_key_check."""
import csv
import os
import sqlite3

DATA = "data"
OUT = os.path.join(DATA, "seed.sql")

SCHEMA = """
CREATE TABLE suppliers (supplier_id TEXT PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL, status TEXT NOT NULL, onboarded_date TEXT NOT NULL);
CREATE TABLE products (product_id TEXT PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL);
CREATE TABLE bom (bom_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(product_id), material_code TEXT NOT NULL, qty_per_unit_kg REAL NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT);
CREATE TABLE material_lots (raw_lot_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id), material_code TEXT NOT NULL, received_date TEXT NOT NULL, quantity_kg REAL NOT NULL, status TEXT NOT NULL);
CREATE TABLE production_orders (work_order_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(product_id), start_date TEXT NOT NULL, end_date TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE production_consumption (consumption_id TEXT PRIMARY KEY, work_order_id TEXT NOT NULL REFERENCES production_orders(work_order_id), raw_lot_id TEXT NOT NULL REFERENCES material_lots(raw_lot_id), qty_consumed_kg REAL NOT NULL);
CREATE TABLE finished_lots (finished_lot_id TEXT PRIMARY KEY, work_order_id TEXT NOT NULL REFERENCES production_orders(work_order_id), product_id TEXT NOT NULL REFERENCES products(product_id), produced_qty INTEGER NOT NULL, produced_date TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE shipments (shipment_id TEXT PRIMARY KEY, finished_lot_id TEXT NOT NULL REFERENCES finished_lots(finished_lot_id), warehouse TEXT NOT NULL, ship_date TEXT NOT NULL, shipped_qty INTEGER NOT NULL);
CREATE TABLE deliveries (delivery_id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL REFERENCES shipments(shipment_id), customer_id TEXT NOT NULL REFERENCES customers(customer_id), delivery_date TEXT NOT NULL, delivered_qty INTEGER NOT NULL, sale_status TEXT NOT NULL);
CREATE TABLE recall_cases (recall_id TEXT PRIMARY KEY, trigger_type TEXT NOT NULL, trigger_lot_id TEXT NOT NULL, reason TEXT NOT NULL, opened_date TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE recall_actions (action_id TEXT PRIMARY KEY, recall_id TEXT NOT NULL REFERENCES recall_cases(recall_id), delivery_id TEXT NOT NULL REFERENCES deliveries(delivery_id), action_type TEXT NOT NULL, affected_qty INTEGER NOT NULL, recovered_qty INTEGER NOT NULL, disposition TEXT NOT NULL, action_date TEXT NOT NULL);
CREATE TABLE lot_status_events (event_id TEXT PRIMARY KEY, lot_id TEXT NOT NULL, old_status TEXT, new_status TEXT NOT NULL, event_date TEXT NOT NULL);
"""

ORDER = ["suppliers", "products", "customers", "bom", "material_lots",
         "production_orders", "production_consumption", "finished_lots",
         "shipments", "deliveries", "recall_cases", "recall_actions",
         "lot_status_events"]


def main():
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)

    for name in ORDER:
        with open(os.path.join(DATA, name + ".csv"), newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            marks = ",".join("?" * len(header))
            con.executemany(f"INSERT INTO {name} ({','.join(header)}) VALUES ({marks})", reader)
    con.commit()

    bad = con.execute("PRAGMA foreign_key_check").fetchall()

    with open(OUT, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")

    print(f"Tables loaded: {len(ORDER)}")
    print(f"Wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")
    print(f"Foreign key violations found: {len(bad)}")
    if bad:
        print("Tables with violations:", sorted({row[0] for row in bad}))


if __name__ == "__main__":
    main()