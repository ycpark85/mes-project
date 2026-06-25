# Project Operations

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
