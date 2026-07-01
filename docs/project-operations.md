# Project Operations

## WPF ClickOnce Deployment

The WPF client is published with `ClickOnceProfile`.

- The current staging folder is `C:\mes_publish_test\wpf\`.
- `PublishUrl` is the ClickOnce staging folder: `C:\mes_publish_test\wpf\`.
- `PublishDir` must remain the project-local ClickOnce intermediate folder: `bin\Release\net8.0-windows\win-x64\app.publish\`.
- Do not set `PublishDir` to the same folder as `PublishUrl`; doing so can mix raw publish files into the ClickOnce root.
- The ClickOnce root should contain only `Application Files`, `Mes.Wpf.application`, `setup.exe`, and other ClickOnce bootstrap files.
- `InstallUrl` and `UpdateUrl` point to `\\172.30.1.240\mes_wpf\`.
- If a publish prompt asks to overwrite an older deployment version, check for stale ClickOnce manifests under `bin\Release\net8.0-windows\win-x64\app.publish` and clean the build output before publishing again.
- The ClickOnce deployment version is controlled by `ApplicationVersion` and `ApplicationRevision` in the publish profile.

## Raw Material Inventory Management

Raw material inventory is managed separately from product inventory.

- Product items remain in `product`.
- Raw material items are managed in `raw_material`.
- Raw material stock is tracked by raw material, location, and raw material LOT.
- Raw material locations are user-configurable and are not hard-coded to a specific warehouse or outsource vendor.
- A raw material location can represent an internal warehouse, an outsource vendor holding location, or another controlled location.
- Outsource-vendor locations can be linked to `partner` through `partner_id`.
- Raw material location codes are system-generated when the user creates a location without entering a code.
- In the WPF raw material master, users select a partner by searching partner name; the selected partner name is copied to the location name by default while the internal `partner_id` is stored separately.

Raw material inventory quantity rules:

- Physical raw material stock is stored at `raw_material_inventory.current_qty` by material and location.
- LOT-level stock is stored at `raw_material_inventory_lot.current_qty`.
- Inbound, transfer, adjustment, and outsource consumption are recorded in `raw_material_inventory_movement`.
- Transfers create paired `TRANSFER_OUT` and `TRANSFER_IN` movement rows with the same `transfer_key`.
- Inventory movement rows are not overwritten for correction. Correction, cancel, and registered-work-instruction update flows use opposite movements such as `CONSUME_REVERSE` or adjustment movements.
- Raw material movement history should be reviewed primarily by raw material and LOT number, not only by the internal inventory-lot row id, because a transfer can create or update separate location-level LOT rows for the same physical raw material LOT.
- Movement history includes the original `INBOUND` row, later `TRANSFER_OUT` and `TRANSFER_IN` rows, adjustment rows, and outsource consumption rows when queried by raw material and LOT number.

Stage 1 scope:

- Raw material item management.
- Raw material location management.
- Raw material LOT inventory inquiry.
- Raw material inbound.
- Raw material location transfer.
- Raw material LOT adjustment.
- Raw material movement history.

Stage 2 scope:

- Outsource work instruction raw material allocation.
- The WPF outsource work instruction detail panel keeps the existing layout and adds a raw-material allocation button and allocation summary/list.
- Before saving, allocation rows are held only in the screen state and are used as temporary reservations so another draft in the same batch cannot reuse the same available quantity.
- On final outsource work instruction save, raw material LOT stock and material-location stock are reduced in the same database transaction.
- Final save creates `CONSUME_OUT` rows in `raw_material_inventory_movement` and stores allocation snapshots in `outsource_work_group_raw_material_allocation`.

Outsource work instruction list, update, and cancel rules:

- Outsource work instruction list is managed by `outsource_work_group`, because work grouping, raw material allocation, Bohyun outsource management, and later cost flows are group-based.
- Registered work groups can be updated only before vendor receipt and before a purchase order group is created.
- The first update scope allows `sheet_qty`, `length_m`, `sheet_cut_count`, `fabric_lot_no`, `remark`, and raw material allocation changes. Work LOT composition, process type, and partner changes remain cancel-and-recreate flows.
- Update reason is required. Each update writes before/after snapshots to `outsource_work_group_change_log`.
- Updating raw material allocations does not overwrite existing movement rows. The system creates `CONSUME_REVERSE` rows for currently consumed allocations, marks those allocation rows `REVERSED`, then creates new `CONSUME_OUT` rows and consumed allocation snapshots.
- A registered work group has `status IS NULL` and is displayed as `REGISTERED` or "지시등록".
- Canceling a work group sets `outsource_work_group.status` to `CANCELED` and records `canceled_at` and `canceled_reason`.
- Canceling does not delete the work instruction, work group, raw material allocation, or movement history.
- Raw material consumption is reversed with `CONSUME_REVERSE` movement rows, and consumed allocation rows are marked `REVERSED`.
- The related active `outsource_work_instruction_item` rows are deactivated so the same LOT and process can be registered again.
- Candidate LOT lookup excludes only active, non-canceled work groups. Therefore canceled work instructions allow their LOTs to appear again in the outsource-work-instruction candidate list.
- Bohyun outsource management and purchase-order target lists exclude canceled work groups.
- Cancel is blocked once the work group or connected purchase-order group is at vendor-received, work-done, or shipped status.

Outsource purchase order connection rules:

- Purchase-order targets are grouped by `outsource_work_group`, not only by instruction number, because one instruction can contain multiple work groups.
- Printed-product routing keeps the primary outsource work instruction as `PRINT`, but purchase-order targets expose both `CUT` and `PRINT` because the operational flow is cutting, printing, then Bohyun die-cut management.
- Creating an outsource purchase order writes both LOT-level `outsource_purchase_order_item` rows and work-group-level `outsource_purchase_order_group` rows.
- All LOTs in the same outsource work group must be purchase ordered together.
- A work group already connected to `outsource_purchase_order_group` for the same purchase-order process is excluded from that process target list; any purchase-order group link blocks registered-work-instruction updates.

Out of current scope:

- Work-in-process ledger.
- Monthly or quarterly closing.
- Manufacturing overhead allocation.

Cost/closing preparation:

- Raw material LOTs can store `unit_cost`.
- Movement rows store unit-cost and amount snapshots.
- These snapshots are retained so future WIP and closing features can calculate raw material inventory amount and raw-material component of WIP amount without depending on later master-data changes.

## Outsource Work Group Representative Product

Bundle outsource work groups have one representative LOT.

- Single-LOT work groups use the only LOT as the representative automatically.
- Bundle work groups require the user to select one LOT and click the representative product button before saving.
- The representative product is used as the display product name in Bohyun outsource management, outsource shipment lists, purchase order forms, and outsource processing cost targets.
- Cost allocation remains LOT-level. The representative product affects display and vendor-facing identification, not allocation math.

## Bohyun Outsource Management

Bohyun outsource management is an operational inbound, work-done, and shipment menu, not a cost-process menu.

- All outsource work instruction groups for coated Tyvek products flow into Bohyun outsource management, whether the product is blank or printed.
- Bohyun management uses the existing outsource work group as the operational unit.
- A separate `DIECUT` outsource work group is not required for Bohyun operations.
- Process filters in Bohyun management are limited to the operational outsource instruction processes (`CUT`, `PRINT`).

## Inspection Result Quantity Rules

Inspection result quantities separate internal receiving control from quality judgment.

- `good_qty`: good quantity confirmed by inspection.
- `defect_ship_qty`: defective quantity allowed to ship as-is.
- `defect_qty`: defective quantity not allowed to ship.
- `uninspected_qty`: quantity not inspected after the shipment requirement is met. It is tracked separately for uninspected disposal statistics.
- `discard_qty`: sellable quantity disposal used by shipment/inventory settlement. It is not the same as `uninspected_qty`.
- Total disposal quantity for operational review is `discard_qty + uninspected_qty`.

Quality statistics use only inspected quantities:

- `inspected_qty = good_qty + defect_ship_qty + defect_qty`
- good rate and defect rate use `inspected_qty` as the denominator.
- `uninspected_qty` is excluded from good/defect quality statistics.
- Disposal statistics can include `uninspected_qty`, but quality statistics must not.

Internal official received quantity is calculated from inspection results:

- `received_qty = good_qty + defect_ship_qty + defect_qty + uninspected_qty`
- outsource process loss should compare calculated output quantity against this internal `received_qty`, not against vendor-reported work-done quantity.
- vendor work-done quantity remains an operational reference value.

## Inventory Availability and Order Planning

Order planning separates physical inventory from available inventory.

- Physical inventory is `product_inventory.current_qty`.
- Reserved inventory is stock shipment quantity in `shipment_line` where `source_type = STOCK` and `status = WAITING`.
- Available inventory is physical inventory minus reserved inventory.
- Automatic order planning must use available inventory, not physical inventory.

Stock usage rules:

- Stock-only shipment and close: when the processing plan is confirmed, stock shipment lines are created and immediately confirmed. Inventory is deducted at that point because no production LOT or inspection result follows.
- Partial stock plus production: when the processing plan is confirmed, stock shipment lines remain in `WAITING` status as reserved inventory. The reserved quantity is excluded from availability for later orders.
- When inspection result is saved for partial stock plus production, the reserved stock shipment lines are consumed first and changed to `DONE`; only any remaining requested stock shipment quantity is allocated from FIFO available inventory.
- Unused stock reservations for the order line are canceled when final inspection settlement no longer uses them.

## Production Progress Status

The Production Management menu includes `생산진행현황` (`Production Progress Status`).

This menu is an operational progress view, not a completed-history report.

- The screen reads from `production_progress_snapshot`, a production progress read model.
- Source tables remain the system of record. The snapshot is regenerated from source data when needed.
- Run `python scripts/rebuild_production_progress_snapshots.py` from the backend directory after introducing the table to existing data, after bulk data repair, or when snapshot drift is suspected.
- When an order line due date is changed from the order list or order detail screen, the order due date, not-yet-started LOT due dates, and `production_progress_snapshot.due_date` are updated in the same transaction.
- Inspection schedule dates, inspection results, shipment results, and inventory movements are not automatically changed by an order due-date change.
- Default status filter is `IN_PROGRESS`.
- `IN_PROGRESS` means inspection result registration is not completed.
- `COMPLETED` means inspection result registration is completed.
- Shipment and delivery status are outside this menu's completion rule.
- Default sort order is due-date urgency:
  - overdue due dates first
  - D-DAY
  - D-1, D-2, D-3
  - later due dates in ascending due-date order

Top filters:

- partner
- product
- status (`IN_PROGRESS`, `COMPLETED`)

Grid columns:

- due date
- due slack
- partner
- product
- order quantity
- available inventory
- production quantity
- work type
- current process
- progress rate

Due slack display:

- `D-4` or more: relaxed, green text.
- `D-3` through `D-1`: imminent, orange text.
- `D-DAY` and overdue (`D+N`): urgent, red text.

Current process has seven display states:

- `LOT_CREATED`: LOT created.
- `OUTSOURCE_ORDERED`: outsource work instruction is registered.
- `DIECUT_RECEIVED`: Bohyun/vendor inbound is completed.
- `OUTSOURCE_DONE`: Bohyun/vendor work is completed.
- `INSPECTION_WAITING`: company inbound is completed and inspection is waiting.
- `INSPECTION_IN_PROGRESS`: inspection is in progress.
- `COMPLETED`: inspection result registration is completed.

Work type display:

- `BASIC`: 기본작업
- `REWORK`: 재작업

Rework LOTs can be created only after the original LOT work is completed. Therefore, original LOTs and rework LOTs are not expected to progress at the same time. If a rework LOT exists and is still active, production progress status displays the rework LOT's current process. If rework was completed, completed rows display `REWORK` so users can identify that the order was completed through rework.

For order lines with multiple LOTs in the same work type, the current process is the earliest unfinished bottleneck process among those LOTs.

## Product History Monitoring

Product history monitoring is a product-to-LOT trace view.

- The product search can filter by product keyword and partner keyword.
- Partner keyword filtering uses historical order lines. It returns products that have active order line history for matching partner names or business numbers.
- After selecting a product, the user loads the latest LOT history for that product.

## Outsource Processing Cost Management

The Production Management menu includes `Outsource Processing Cost Management`.

### Scope

- Manage standard processing cost and actual processing cost separately.
- Manage supply amount only. VAT and tax invoices are outside this feature.
- Register costs by process:
  - `CUT`: cutting cost
  - `PRINT`: printing cost
  - `DIECUT`: die-cutting cost
- The cost process is a cost category, not necessarily the same as the operational outsource work group process.
- `CUT` and `DIECUT` cost targets include all outsource work groups.
- `PRINT` cost targets include only `PRINT` outsource work groups.
- Use a cost group as the settlement unit.
- Register cost targets by outsource work group for all processes.
- Allow multiple outsource work groups to be combined into one cost group for SCM settlement.
- Use manually selected settlement month as the monthly closing basis.
- For bundle targets, display the representative LOT and representative product name in the target list while keeping all LOTs available for allocation and detail review.
- Target selection shows LOT-level allocation basis preview even before a cost group is saved. Standard and actual allocated amounts are filled after cost registration.

### Allocation Rules

- `CUT`: allocate by area, calculated as product width x product length x instructed output quantity.
- `PRINT`: allocate by area, calculated as product width x product length x instructed output quantity.
- `DIECUT`: allocate by area, calculated as product width x product length x instructed output quantity.

All allocation inputs are saved as snapshots when a cost group is created:

- LOT number
- product code/name/spec
- product width and length
- cuts per sheet
- sheet quantity
- instructed output quantity
- allocation basis type and value
- allocation ratio
- standard allocated amount
- actual allocated amount

### Closing Rules

- `DRAFT`: editable.
- `CLOSED`: monthly closed. Normal edits are blocked.
- `CANCELED`: canceled. Data remains for auditability.
- Actual processing cost must be entered before monthly closing.
- A cost variance is a review item, not a closing blocker. If standard cost and actual cost differ, the user can still close the group after confirming the variance.
- `COST_VARIANCE` is a query-only status for open variance review. It returns `DRAFT` groups where standard cost and actual cost are both entered and differ.
- Closed groups can be reopened by users with write permission.

### Permissions

- `OUTSOURCE_PROCESSING_COSTS.VIEW`: view menu and data.
- `OUTSOURCE_PROCESSING_COSTS.WRITE`: create, update, close, reopen, and cancel cost groups.
