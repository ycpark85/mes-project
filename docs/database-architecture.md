# Database Architecture

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
