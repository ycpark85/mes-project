# Database Architecture

## SQLAlchemy Metadata Source

The project uses one SQLAlchemy declarative metadata source.

- `app.db.base.Base` is the only declarative `Base` definition.
- Every model imports `Base` from `app.db.base`.
- `app.core.db` imports and re-exports the same `Base` while creating the engine and session factory.
- Alembic imports all models and uses `app.db.base.Base.metadata` as `target_metadata`.
- The `drawing.current_revision_id` foreign key uses `use_alter=True` and the existing constraint name `fk_drawing__current_revision_id`. This breaks the intentional `drawing` / `drawing_revision` DDL sort cycle without changing the database relationship.
- Do not introduce another `DeclarativeBase` or `declarative_base()` instance. A second metadata registry can cause Alembic autogenerate to miss tables or report false create/drop changes.
- Run `alembic check` after model or migration changes. A clean schema reports `No new upgrade operations detected`.

## Business Index Alignment

Business-critical indexes must be represented in both Alembic history and SQLAlchemy model metadata.

- `ix_order_line_plan_history__order_line_latest` indexes `order_line_id`, `created_at DESC`, and `plan_history_id DESC`. It supports latest-plan lookup and ordered plan timelines without relying on the ineffective former `created_at`-only index.
- `uq_owi_item__active_process_lot` is a partial unique index on `process_type` and `lot_id` where `is_active = true`. It is the database-level final defense against two active outsource instructions for the same process and LOT.
- Canceled instruction items remain stored with `is_active = false`, so the same process and LOT can be registered again after cancellation.
- The partial unique rule is also declared for SQLite tests, preventing the test environment from silently accepting data that PostgreSQL rejects.

Migration `29d3e4f5a6b7` replaces the plan-history index. Standard index creation briefly takes a write lock on that table, so production rollout should apply it during the planned V2 maintenance window. The local database had 159 plan-history rows when the migration was verified.

## Authentication Session Version

The `users.auth_version` column is the server-side version of a user's active authentication context.

- It is `NOT NULL`, starts at `1`, and is protected by `ck_users__auth_version_positive`.
- Every access token carries the version that was current when the token was issued.
- An authenticated request is accepted only when the token version matches the current user row.
- Password reset, actual user-role changes, vendor-access changes, account activation changes, and role permission/activation changes increment the affected users' versions.
- A user's own password change invalidates all earlier tokens and returns a replacement token for the current WPF session.
- Tokens issued before this column and claim exist are intentionally rejected after rollout, so the schema migration requires users to sign in once again.

No token blacklist table is used. This keeps revocation checks bounded to the existing user lookup performed for every authenticated request.

## Vendor Portal Access Tables

External vendor access is scoped through dedicated vendor-portal tables instead of exposing the internal MES authorization surface directly.

### `vendor_user_access`

Maps an active MES user account to a vendor partner for vendor-portal access.

Important columns:

- `user_id`: linked MES user account.
- `partner_id`: vendor partner the user is allowed to access.
- `is_active`: soft enable/disable flag for vendor access.

The table has a unique constraint on `user_id` and `partner_id` so the same vendor access grant cannot be duplicated.

Operational maintenance:

- Vendor access grants are maintained through the internal MES WPF 회원관리 menu.
- Checking `외주업체 계정` and selecting a VENDOR partner creates or reactivates one `vendor_user_access` row for the user.
- Other vendor access rows for that user are deactivated so a vendor account is scoped to one vendor partner at a time.
- Unchecking `외주업체 계정` deactivates the user's vendor access rows.
- The helper script for vendor account creation is limited to testing or emergency recovery.

### `vendor_portal_audit_log`

Append-only audit records for vendor-facing business actions.

Important columns:

- `user_id`: user who performed the action, retained as nullable if the user is later deleted.
- `partner_id`: vendor scope used for the action.
- `outsource_work_group_id`: affected Bohyun outsource work group when the action targets a work group.
- `action_type`: examples include `VIEW_LIST`, `INBOUND`, `WORK_DONE`, and `SHIP`.
- `before_status`, `after_status`: status transition context.
- `request_ip`, `user_agent`: external access trace context. `user_agent` uses `Text` so valid long client identifiers cannot fail the business transaction.
- `user_agent_truncated`: `true` when the server shortened an oversized User-Agent before storage.
- `remark`: optional action context, such as work-done remarks.

The login audit table `auth_audit_logs` uses the same User-Agent columns and normalization policy. Both audit paths limit stored User-Agent values to 2,000 characters, replace control characters with spaces, and preserve whether truncation occurred.

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

- `location_code`: unique business code, generated by the system when the UI does not provide one.
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

Stage 1 uses inbound, transfer, and adjustment. Stage 2 uses `CONSUME_OUT` when an outsource work instruction is saved with raw material allocations. `CONSUME_REVERSE` is used when a registered outsource work instruction is updated or canceled.

Important columns:

- `qty`: signed movement quantity.
- `balance_after`: material-location balance after the movement.
- `unit_cost_snapshot`, `amount_snapshot`: cost snapshots for future closing and auditability.
- `transfer_key`: groups paired transfer-out and transfer-in rows.
- Movement history queries should support raw material, LOT number, location, movement type, and date filters so the original inbound row and later location transfers can be reviewed together for the same raw material LOT.
- `source_type` and `source_id` identify the source operation. Outsource work-group consumption and self-use sheet jobs use different source types so their ledger histories remain distinguishable.
- LOT-number contains-search uses the PostgreSQL `pg_trgm` extension and a partial GIN index on non-null `lot_no` values. This keeps the existing `ILIKE '%keyword%'` search behavior usable as movement history grows.

### `outsource_work_group_raw_material_allocation`

Raw material LOT consumption snapshot for an outsource work group.

Important columns:

- `outsource_work_group_id`: work group consuming the raw material.
- `raw_material_id`, `raw_material_location_id`, `raw_material_inventory_lot_id`: raw material stock source at the time of save.
- `lot_no`: raw material LOT snapshot retained even if the inventory-lot row is later merged or archived.
- `qty`: consumed raw material quantity. Must be positive.
- `unit_cost_snapshot`, `amount_snapshot`: cost snapshots for future WIP and closing calculations.
- `raw_material_inventory_movement_id`: linked `CONSUME_OUT` ledger row.
- `status`: `CONSUMED` for active consumption snapshots and `REVERSED` for allocations restored by update or cancel flows.

## Self-Use Sheet Processing and Inventory Tables

Self-use sheets are processed inventory made from existing raw material LOT stock. They are kept separate from raw material stock because the input unit can be meters or another raw-material unit while the output is managed as sheet count.

### `self_use_sheet_job`

Header and state machine for one self-use sheet cutting operation.

- `use_no`: unique human-readable operation number.
- `purpose_type`: `PRINT_SETUP`, `SAMPLE`, `TEST_RND`, or `OTHER`. `OTHER` requires a memo.
- `execution_type`: `INTERNAL` or `OUTSOURCE`; outsource jobs require a vendor `partner_id`.
- `status`: `DRAFT`, `IN_PROGRESS`, `COMPLETED`, or `CANCELED`.
- Cutting dimensions, planned/actual output, scrap, expected/actual processing fee, actor snapshots, transition timestamps, and cancel reason are retained.
- `version` protects state transitions from stale concurrent writes.

### `self_use_sheet_raw_material_allocation`

Raw-material LOT allocation and cost snapshot for a self-use sheet job.

- Multiple input LOTs are supported, but every allocation in one job must belong to the same raw material.
- Original source location/LOT and processing-location LOT are stored separately so outsource dispatch and return can be traced.
- `planned_qty`, `actual_consumed_qty`, and `returned_qty` preserve the input reconciliation.
- Unit cost and amount snapshots retain the material-cost basis used when the self-use sheet LOT is completed.
- Status progresses from `PLANNED` to `ISSUED` to `CONSUMED`; cancellation uses `REVERSED`.

### `self_use_sheet_inventory_lot`

Current self-use sheet stock created by one completed job.

- One job creates at most one sheet LOT; both the job relation and `sheet_lot_no` are unique.
- `initial_qty` and `current_qty` are sheet counts and cannot be mixed with raw-material quantity units.
- `material_amount`, `processing_fee`, `total_cost`, and `unit_cost` retain the completion valuation.
- Status is `AVAILABLE`, `DEPLETED`, or `CANCELED`; `version` protects use and reversal writes.

### `self_use_sheet_inventory_movement`

Append-only self-use sheet inventory ledger.

- `PRODUCE_IN`: cutting completion and sheet LOT creation.
- `USE_OUT`: printing setup, sample production, test/R&D, or another documented use.
- `USE_REVERSE`: reversal of one `USE_OUT` movement. `source_movement_id` is unique so one usage cannot be reversed twice.
- `CANCEL_OUT`: cancellation of an unused completed job.
- `TRANSFER_OUT`/`TRANSFER_IN`: paired location movement with one transfer key; LOT total is unchanged.
- `WORK_USE_OUT`/`WORK_USE_REVERSE`: outsource work-instruction consumption and exact-location restoration.
- Signed quantity, LOT balance, location balance, location/counterpart, source operation, unit-cost/amount snapshots, actor, memo, and timestamp are retained.

### `self_use_sheet_inventory_balance`

Location-level current stock for one self-use sheet LOT.

- `(self_use_sheet_inventory_lot_id, raw_material_location_id)` is unique.
- `current_qty` is nonnegative and the sum of all location balances must equal the parent LOT `current_qty`.
- Row locks on the LOT and location balance protect concurrent use and transfer.

### `outsource_work_group_self_use_sheet_allocation`

Self-use sheet stock consumed by one outsource work group.

- Stores the sheet LOT, exact source location, quantity, cost snapshot, linked sheet movement, and `CONSUMED`/`REVERSED` status.
- Raw-roll and self-use-sheet allocations are mutually exclusive. Self-use allocations must total the work-group sheet quantity.

### `outsource_work_group_self_use_sheet_source_snapshot`

Immutable raw-material LOT provenance copied when a self-use sheet is allocated to a work group.

- Keeps source cutting allocation and original raw-material LOT references where available.
- Material code/name, raw-material LOT number, source location name, consumed quantity, unit cost, and amount are stored as snapshots.

## Outsource Work Instruction Cancel Support

### `outsource_work_group`

Cancel state is tracked at work-group level.

- `status` allows `CANCELED` in addition to operational progress states.
- `NULL` status remains the registered/waiting state for existing rows and is displayed by the application as `REGISTERED`.
- `canceled_at` and `canceled_reason` store cancellation audit context.
- Canceled work groups are excluded from Bohyun outsource-management and purchase-order target queries.

### `outsource_work_instruction_item`

The active uniqueness rule for work-instruction registration is based on active rows.

- `is_active` is `true` for active work-instruction LOT/process registrations.
- Canceling a work group sets related instruction items to `is_active = false`.
- The unique guard is a partial unique index on `process_type`, `lot_id` where `is_active = true`.
- This allows a canceled LOT/process to return to the outsource-work-instruction candidate list without deleting historical work-group or movement rows.

## Outsource Work Instruction Update Support

Registered work groups can be updated before vendor receipt and before a purchase order group is created.

### `outsource_purchase_order_group`

Outsource purchase orders keep a work-group-level link in addition to LOT-level purchase-order items.

- `outsource_work_group_id` identifies the work group represented by the purchase order row group.
- Purchase-order target queries exclude work groups that already have an `outsource_purchase_order_group` row for the requested purchase-order process.
- Registered work-group updates are blocked when this link exists, so purchase-order snapshots do not drift from the source work instruction.
- Existing LOT-level `outsource_purchase_order_item` rows remain for backward compatibility and item-level operational statuses.

### `outsource_work_group_change_log`

Work-group updates are append-only audit records.

Important columns:

- `outsource_work_group_id`: updated work group.
- `action_type`: currently `UPDATE`.
- `reason`: required user-entered update reason.
- `before_data`, `after_data`: JSONB snapshots of editable group fields, group items, and active raw material allocations.
- `created_at`, `created_by`: audit metadata.

Raw material allocation updates are ledger-based:

- Existing consumed allocation rows are marked `REVERSED`.
- Opposite `CONSUME_REVERSE` movement rows restore stock.
- New allocation rows and `CONSUME_OUT` movement rows are created for the updated allocation set.
- Work LOT composition, process type, and partner changes remain cancel-and-recreate flows in the first update scope.

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

## Business Search Policy

User-facing keyword searches follow the way operators identify master data and business numbers.

- Partner name, product name, and product code use case-insensitive substring search. PostgreSQL `pg_trgm` GIN indexes support these searches at scale.
- Product specification is displayed where needed but is excluded from the general product keyword search.
- Sales order numbers, customer purchase order numbers, and outsource purchase order numbers require an exact full-number match after trimming whitespace and normalizing letter case.
- Existing B-tree indexes on internal order numbers remain the primary path for exact-number lookup.

## LOT Status Integrity

The stored `lot.status` is protected by the `ck_lot__status_enum` database constraint.

- `WAITING`: LOT created or waiting for the next operational event.
- `RECEIVED`: company inbound completed and inspection is waiting.
- `IN_PROGRESS`: inspection is in progress.
- `PARTIAL_DONE`: a partial inspection result was saved.
- `DONE`: all active inspection schedules for the LOT are complete.
- `CANCELED`: the LOT was canceled.

The LOT management screen may derive a separate display status, such as showing an active outsource LOT as `IN_PROGRESS` while the stored status remains `WAITING`. Display-only values such as `CREATED` and `INSPECTION_DONE` are not stored in `lot.status` and are intentionally excluded from the constraint.

Rework LOTs use `parent_lot_id` and must preserve their creation reason in `lot.memo`.

- `ck_lot__rework_memo_required` allows an optional memo for primary LOTs but requires a non-blank trimmed memo whenever `parent_lot_id` is set.
- The migration audits existing rework rows and stops instead of silently inventing a reason when invalid legacy data exists.
- Application validation remains in both WPF and `lot_rework_service.py`; the database constraint is the final integrity boundary.
