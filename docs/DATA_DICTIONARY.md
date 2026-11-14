# Data Dictionary

Conventions: all dates are ISO `YYYY-MM-DD`. All IDs are immutable and zero-padded. Quantities are positive numbers. Seed: 20261022.
Each entity's primary key is its first field. FK means foreign key. Req = required (Y/N).

## Supplier  (1:N to MaterialLot)
| Field | Type | Req | Rules |
|---|---|---|---|
| supplier_id | string | Y | PK, unique, format `S001`..`S500` |
| name | string | Y | non-empty |
| country | string | Y | one of IN, US, DE, CN, MX |
| status | string | Y | ACTIVE, SUSPENDED |
| onboarded_date | date | Y | not in the future |

## Product  (1:N to BOM, ProductionOrder, FinishedLot)
| Field | Type | Req | Rules |
|---|---|---|---|
| product_id | string | Y | PK, unique, format `P001`..`P020` |
| name | string | Y | non-empty |
| unit | string | Y | always `EA` (each) |

## BOM  (bridge: Product N:M material code)
| Field | Type | Req | Rules |
|---|---|---|---|
| bom_id | string | Y | PK, unique |
| product_id | string | Y | FK to Product |
| material_code | string | Y | `MAT01`..`MAT10` |
| qty_per_unit_kg | float | Y | greater than 0, unit kg |
| effective_from | date | Y | |
| effective_to | date | N | empty = still effective; must be after effective_from |

## MaterialLot  (raw material lot; 1:N to ProductionConsumption)
| Field | Type | Req | Rules |
|---|---|---|---|
| raw_lot_id | string | Y | PK, unique, format `RAWLOT-<supplier_id>-2026-000001` |
| supplier_id | string | Y | FK to Supplier |
| material_code | string | Y | `MAT01`..`MAT10` |
| received_date | date | Y | in 2026 |
| quantity_kg | float | Y | greater than 0, unit kg |
| status | string | Y | RECEIVED, CONSUMED, QUARANTINED, RECALLED |

## ProductionOrder  (1:N to FinishedLot)
| Field | Type | Req | Rules |
|---|---|---|---|
| work_order_id | string | Y | PK, unique, format `WO-2026-000001` |
| product_id | string | Y | FK to Product |
| start_date | date | Y | |
| end_date | date | Y | on or after start_date |
| status | string | Y | COMPLETED, CANCELLED |

## ProductionConsumption  (bridge: ProductionOrder N:M MaterialLot)
| Field | Type | Req | Rules |
|---|---|---|---|
| consumption_id | string | Y | PK, unique |
| work_order_id | string | Y | FK to ProductionOrder |
| raw_lot_id | string | Y | FK to MaterialLot (edge case: may point to a missing lot) |
| qty_consumed_kg | float | Y | greater than 0; sum per raw lot must not exceed the lot quantity |

## FinishedLot  (1:N to Shipment)
| Field | Type | Req | Rules |
|---|---|---|---|
| finished_lot_id | string | Y | PK, unique, format `FINLOT-2026-000001` |
| work_order_id | string | Y | FK to ProductionOrder |
| product_id | string | Y | FK to Product, must match the work order's product |
| produced_qty | integer | Y | greater than 0, unit EA; derived from the kg consumed and BOM |
| produced_date | date | Y | on or after the work order end_date |
| status | string | Y | CREATED, SHIPPED, RECALLED |

## Customer  (1:N to Delivery)
| Field | Type | Req | Rules |
|---|---|---|---|
| customer_id | string | Y | PK, unique, format `C0001`..`C1000` |
| name | string | Y | non-empty |
| region | string | Y | NORTH, SOUTH, EAST, WEST |

## Shipment  (finished lot to warehouse; 1:N to Delivery)
| Field | Type | Req | Rules |
|---|---|---|---|
| shipment_id | string | Y | PK, unique, format `SHP-2026-000001` |
| finished_lot_id | string | Y | FK to FinishedLot |
| warehouse | string | Y | WH-A, WH-B, WH-C |
| ship_date | date | Y | on or after produced_date |
| shipped_qty | integer | Y | greater than 0; sum of deliveries should equal this |

## Delivery  (shipment to customer)
| Field | Type | Req | Rules |
|---|---|---|---|
| delivery_id | string | Y | PK, unique, format `DEL-2026-000001` |
| shipment_id | string | Y | FK to Shipment |
| customer_id | string | Y | FK to Customer |
| delivery_date | date | Y | on or after ship_date |
| delivered_qty | integer | Y | greater than 0; sum per finished lot must not exceed produced_qty |
| sale_status | string | Y | AVAILABLE_FOR_SALE, BLOCKED, SOLD |

## RecallCase  (1:N to RecallAction)
| Field | Type | Req | Rules |
|---|---|---|---|
| recall_id | string | Y | PK, unique, format `REC-2026-000001` |
| trigger_type | string | Y | RAW_LOT, FINISHED_LOT |
| trigger_lot_id | string | Y | raw_lot_id or finished_lot_id (matches trigger_type) |
| reason | string | Y | CONTAMINATION, QUALITY_DEFECT |
| opened_date | date | Y | |
| status | string | Y | OPEN, CLOSED |

## RecallAction  (what was done for each affected delivery)
| Field | Type | Req | Rules |
|---|---|---|---|
| action_id | string | Y | PK, unique, format `ACT-2026-000001` |
| recall_id | string | Y | FK to RecallCase |
| delivery_id | string | Y | FK to Delivery |
| action_type | string | Y | NOTIFY, QUARANTINE, RECOVER |
| affected_qty | integer | Y | greater than 0 |
| recovered_qty | integer | Y | 0 to affected_qty |
| disposition | string | Y | RECOVERED, PARTIAL, PENDING |
| action_date | date | Y | on or after opened_date |

## LotStatusEvent  (history; rows are never updated or deleted)
| Field | Type | Req | Rules |
|---|---|---|---|
| event_id | string | Y | PK, unique |
| lot_id | string | Y | raw_lot_id or finished_lot_id |
| old_status | string | N | empty for the first event |
| new_status | string | Y | must follow the lot's allowed status order |
| event_date | date | Y | |

## ground_truth (separate file, never used as input)
| Field | Type | Req | Rules |
|---|---|---|---|
| record_id | string | Y | ID of the affected row |
| table_name | string | Y | |
| issue_type | string | Y | MISSING_INPUT_LOT, DELIVERED_EXCEEDS_PRODUCED, RECALL_MISSED_CUSTOMER, RECALLED_STILL_AVAILABLE, CONTAMINATED_SOURCE_LOT |
| expected_decision | string | Y | what a correct system should do |