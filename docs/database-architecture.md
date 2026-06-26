# Database Architecture

## Raw Material Inventory Tables

Raw materials are modeled separately from products so product inventory and raw material inventory can evolve independently.

### `raw_material`

Raw material item master.

Important columns:

- `material_code`: unique business code.
- `material_name`, `material_spec`, `width_mm`, `material_type`, `uom`.
- `standard_unit_cost`: optional default unit cost used as a fallback for inbound lots.
- `is_active`: soft-deactivation flag.

### `raw_material_location`

User-configurable raw material stock location.

Important columns:

- `location_code`: unique business code.
- `location_type`: `INTERNAL_WAREHOUSE`, `OUTSOURCE_VENDOR`, or `OTHER`.
- `partner_id`: optional link to `partner` for outsource-vendor holding locations.
- `is_active`: soft-deactivation flag.

Warehouse and vendor names such as Shinheung warehouse or Korea Label are not hard-coded. They are rows in this table.

### `raw_material_inventory`

Current stock by raw material and location.

- Unique key: `raw_material_id`, `raw_material_location_id`.
- `current_qty` is the physical location-level quantity.

### `raw_material_inventory_lot`

Current stock by raw material, location, and raw material LOT.

- Unique key: `raw_material_id`, `raw_material_location_id`, `lot_no`.
- The same raw material LOT number can exist in multiple locations after transfer.
- `unit_cost` and `received_at` are retained for future inventory amount and WIP calculations.

### `raw_material_inventory_movement`

Raw material stock ledger.

Movement types:

- `INBOUND`
- `TRANSFER_OUT`
- `TRANSFER_IN`
- `ADJUST_IN`
- `ADJUST_OUT`
- `CONSUME_OUT`
- `CONSUME_REVERSE`

Stage 1 uses inbound, transfer, and adjustment. `CONSUME_OUT` and `CONSUME_REVERSE` are reserved for the next outsource-work-instruction allocation step.

Important columns:

- `qty`: signed movement quantity.
- `balance_after`: material-location balance after the movement.
- `unit_cost_snapshot`, `amount_snapshot`: cost snapshots for future closing and auditability.
- `transfer_key`: groups paired transfer-out and transfer-in rows.

## Production Progress Snapshot Read Model

### `production_progress_snapshot`

Production progress status uses a read model table instead of recalculating current progress from all source tables on every screen query.

The source of truth remains the operational tables:

- `order_line`
- `lot`
- `outsource_work_group`
- `outsource_work_group_item`
- `inspection_schedule`
- `inspection_result`
- `product_inventory`
- `shipment_line`

Important columns:

- `order_line_id`: unique business key for one production progress row per order line.
- order, partner, and product display snapshots: used for fast grid rendering and keyword search.
- `status`: `IN_PROGRESS` or `COMPLETED`.
- `work_type`: `BASIC` or `REWORK`.
- `current_process`: one of the production progress process states.
- `current_process_order`: numeric order for bottleneck sorting.
- `progress_rate`: display progress from 0 to 100.
- `order_qty`, `available_inventory_qty`, `production_qty`.
- `lot_count`, `target_lot_count`, `completed_lot_count`, `lot_nos_text`.

Due slack (`D-3`, `D-DAY`, `D+1`) is not stored because it changes every day. The application calculates it from `due_date` at query time.

Update policy:

- The application refreshes the affected order line snapshot when LOT, outsource, inspection, or stock-reservation events change production progress.
- Existing or repaired data can be rebuilt from source tables by running the production progress snapshot rebuild script.
- If the snapshot and source tables ever disagree, source tables win and the snapshot must be regenerated.

## Inspection Result Quantity Extension

### `inspection_result`

The inspection result stores `uninspected_qty` separately from inspected quality quantities.

- `inspected_qty` remains calculated as `good_qty + defect_ship_qty + defect_qty`.
- `uninspected_qty` is `NOT NULL`, defaults existing rows to `0`, and is constrained to be non-negative.
- Official internal received quantity is calculated by the application as `inspected_qty + uninspected_qty`.
- `discard_qty` remains the shipment/inventory settlement disposal quantity and is not reused for uninspected disposal statistics.

## Existing Outsource Work Group Extension

### `outsource_work_group`

The outsource work group stores `representative_lot_id`.

- It points to the LOT used as the representative product for bundle outsource work.
- Single-LOT work groups are saved with their only LOT as the representative.
- Application service validation ensures the representative LOT belongs to the work group items.
- Older rows without a representative use the first work group item as a display fallback until they are recreated or corrected.

## Outsource Processing Cost Tables

### `outsource_processing_cost_group`

Settlement header for outsource processing costs.

Important columns:

- `cost_group_no`: unique business number.
- `settlement_month`: user-selected monthly settlement basis. Stored as the first day of the month.
- `process_type`: `CUT`, `PRINT`, or `DIECUT`.
- `status`: `DRAFT`, `CLOSED`, or `CANCELED`.
- `standard_amount`: standard processing supply amount.
- `actual_amount`: actual processing supply amount from vendor monthly statement.
- `actual_billing_month`: vendor billing month.
- `closed_at`, `canceled_at`: status timestamps.

### `outsource_processing_cost_work_group`

Join table between a cost group and existing outsource work groups.

Used by `CUT`, `PRINT`, and `DIECUT`. Cost registration targets are outsource work groups, and multiple work groups may be combined into one cost group for SCM settlement.

### `outsource_processing_cost_allocation`

LOT-level allocation snapshot.

Important columns:

- `lot_id`
- optional `outsource_work_group_id`
- optional `outsource_work_group_item_id`
- product and LOT snapshots
- `basis_type`: currently `AREA` for outsource processing cost allocation
- `basis_value`
- `basis_area_sqm`
- `allocation_ratio`
- `standard_allocated_amount`
- `actual_allocated_amount`

The allocation snapshot prevents historical monthly closing data from changing when product specs or LOT data are later modified.
