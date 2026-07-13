from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material_location import RawMaterialLocation
from app.schemas.raw_material import (
    RawMaterialAdjustmentIn,
    RawMaterialCreate,
    RawMaterialInboundIn,
    RawMaterialLocationCreate,
    RawMaterialLocationUpdate,
    RawMaterialTransferIn,
    RawMaterialUpdate,
)
from app.services.raw_material_inventory_service import (
    adjust_raw_material_in_session,
    inbound_raw_material_in_session,
    transfer_raw_material_in_session,
)
from app.services.raw_material_master_service import (
    create_raw_material_in_session,
    create_raw_material_location_in_session,
    deactivate_raw_material_in_session,
    deactivate_raw_material_location_in_session,
    update_raw_material_in_session,
    update_raw_material_location_in_session,
)
from app.services.raw_material_query import (
    list_raw_material_inventory_lots_for_grid,
    list_raw_material_locations_for_grid,
    list_raw_material_movements_for_grid,
    list_raw_materials_for_grid,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "raw_material",
    "raw_material_location",
    "raw_material_inventory",
    "raw_material_inventory_lot",
    "raw_material_inventory_movement",
]


class RawMaterialQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_raw_materials()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_list_raw_materials_filters_active_and_sums_inventory(self) -> None:
        result = list_raw_materials_for_grid(self.db, q="rm-a")

        self.assertEqual(1, result.total)
        self.assertEqual("RM-A", result.items[0].material_code)
        self.assertEqual(Decimal("15.00"), result.items[0].current_qty)

    def test_list_locations_returns_partner_name_and_current_qty(self) -> None:
        result = list_raw_material_locations_for_grid(self.db, q="vendor")

        self.assertEqual(1, result.total)
        self.assertEqual("VEN-A", result.items[0].location_code)
        self.assertEqual("Vendor A", result.items[0].partner_name)
        self.assertEqual(Decimal("5.00"), result.items[0].current_qty)

    def test_list_inventory_lots_filters_positive_lots_and_calculates_amount(self) -> None:
        result = list_raw_material_inventory_lots_for_grid(self.db, raw_material_id=1)

        self.assertEqual(2, result.total)
        self.assertEqual(["RMLOT-A1", "RMLOT-A2"], [item.lot_no for item in result.items])
        self.assertEqual(Decimal("25.00"), result.items[0].inventory_amount)
        self.assertEqual(Decimal("15.00"), result.items[1].inventory_amount)

    def test_list_movements_filters_type_and_orders_latest_first(self) -> None:
        result = list_raw_material_movements_for_grid(self.db, raw_material_id=1, movement_type="transfer_in")

        self.assertEqual(1, result.total)
        self.assertEqual("TRANSFER_IN", result.items[0].movement_type)
        self.assertEqual("RMLOT-A2", result.items[0].lot_no)
        self.assertEqual("Vendor Storage", result.items[0].location_name)

    def test_list_movements_filters_lot_keyword_and_date_range(self) -> None:
        result = list_raw_material_movements_for_grid(
            self.db,
            lot_no="a1",
            date_from=(self.now - timedelta(days=1)).date(),
            date_to=self.now.date(),
        )

        self.assertEqual(1, result.total)
        self.assertEqual("RMLOT-A1", result.items[0].lot_no)
        self.assertEqual("TRANSFER_OUT", result.items[0].movement_type)

    def test_movement_lot_search_index_compiles_as_partial_trigram_gin(self) -> None:
        index = next(
            index
            for index in RawMaterialInventoryMovement.__table__.indexes
            if index.name == "ix_raw_material_inventory_movement__lot_no_trgm"
        )

        ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

        self.assertIn("USING gin", ddl)
        self.assertIn("lot_no gin_trgm_ops", ddl)
        self.assertIn("WHERE lot_no IS NOT NULL", ddl)

    def test_inbound_creates_new_lot_inventory_and_movement(self) -> None:
        result = inbound_raw_material_in_session(
            self.db,
            RawMaterialInboundIn(
                raw_material_id=2,
                raw_material_location_id=1,
                lot_no=" rmlot-b1 ",
                qty=Decimal("7"),
                unit_cost=None,
                memo=" opening ",
            ),
        )
        self.db.commit()

        inventory = self.db.get(RawMaterialInventory, 3)
        inventory_lot = self.db.get(RawMaterialInventoryLot, 4)

        self.assertEqual("INBOUND", result.movement_type)
        self.assertEqual("RMLOT-B1", result.lot_no)
        self.assertEqual(Decimal("7.00"), inventory.current_qty)
        self.assertEqual(Decimal("7.00"), inventory_lot.current_qty)
        self.assertEqual(Decimal("1.0000"), inventory_lot.unit_cost)
        self.assertEqual(Decimal("7.00"), result.amount_snapshot)

    def test_transfer_moves_qty_between_locations_and_writes_two_movements(self) -> None:
        result = transfer_raw_material_in_session(
            self.db,
            RawMaterialTransferIn(raw_material_inventory_lot_id=1, to_location_id=2, qty=Decimal("4"), memo="move"),
        )
        self.db.commit()

        source_inventory = self.db.get(RawMaterialInventory, 1)
        target_inventory = self.db.get(RawMaterialInventory, 2)
        source_lot = self.db.get(RawMaterialInventoryLot, 1)
        target_lot = (
            self.db.execute(
                select(RawMaterialInventoryLot).where(
                    RawMaterialInventoryLot.raw_material_location_id == 2,
                    RawMaterialInventoryLot.lot_no == "RMLOT-A1",
                )
            )
            .scalars()
            .one()
        )

        self.assertEqual(2, result.total)
        self.assertEqual(["TRANSFER_OUT", "TRANSFER_IN"], [item.movement_type for item in result.items])
        self.assertEqual(Decimal("6.00"), source_inventory.current_qty)
        self.assertEqual(Decimal("9.00"), target_inventory.current_qty)
        self.assertEqual(Decimal("6.00"), source_lot.current_qty)
        self.assertEqual(Decimal("4.00"), target_lot.current_qty)
        self.assertEqual(result.items[0].transfer_key, result.items[1].transfer_key)

    def test_adjust_in_and_out_updates_lot_inventory_and_movement(self) -> None:
        in_result = adjust_raw_material_in_session(
            self.db,
            payload=RawMaterialAdjustmentIn(raw_material_inventory_lot_id=1, qty=Decimal("2"), memo="plus"),
            direction="IN",
        )
        out_result = adjust_raw_material_in_session(
            self.db,
            payload=RawMaterialAdjustmentIn(raw_material_inventory_lot_id=1, qty=Decimal("3"), memo="minus"),
            direction="out",
        )
        self.db.commit()

        inventory = self.db.get(RawMaterialInventory, 1)
        inventory_lot = self.db.get(RawMaterialInventoryLot, 1)

        self.assertEqual("ADJUST_IN", in_result.movement_type)
        self.assertEqual("ADJUST_OUT", out_result.movement_type)
        self.assertEqual(Decimal("9.00"), inventory.current_qty)
        self.assertEqual(Decimal("9.00"), inventory_lot.current_qty)
        self.assertEqual(Decimal("-3.00"), out_result.qty)

    def test_adjust_out_rejects_insufficient_inventory(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            adjust_raw_material_in_session(
                self.db,
                payload=RawMaterialAdjustmentIn(raw_material_inventory_lot_id=2, qty=Decimal("6"), memo="too much"),
                direction="OUT",
            )

        self.assertEqual(409, ctx.exception.status_code)
        self.assertEqual(Decimal("5.00"), self.db.get(RawMaterialInventoryLot, 2).current_qty)

    def test_create_and_update_raw_material_normalizes_fields(self) -> None:
        created = create_raw_material_in_session(
            self.db,
            RawMaterialCreate(
                material_code=" rm-d ",
                material_name=" Material D ",
                material_spec=" spec d ",
                uom=" kg ",
                standard_unit_cost=Decimal("2.34567"),
                memo=" memo ",
            ),
        )
        updated = update_raw_material_in_session(
            self.db,
            raw_material_id=created.raw_material_id,
            payload=RawMaterialUpdate(
                material_name=" Material D2 ",
                material_spec=" spec d2 ",
                uom=" roll ",
                standard_unit_cost=Decimal("3.1"),
                memo=" updated ",
            ),
        )
        self.db.commit()

        material = self.db.get(RawMaterial, created.raw_material_id)

        self.assertEqual("RM-D", created.material_code)
        self.assertEqual("Material D2", updated.material_name)
        self.assertEqual("ROLL", material.uom)
        self.assertEqual(Decimal("3.1000"), material.standard_unit_cost)
        self.assertEqual("updated", material.memo)

    def test_deactivate_raw_material_allows_zero_inventory_and_rejects_existing_inventory(self) -> None:
        result = deactivate_raw_material_in_session(self.db, 2)
        self.db.commit()

        self.assertFalse(result.is_active)
        self.assertFalse(self.db.get(RawMaterial, 2).is_active)

        with self.assertRaises(HTTPException) as ctx:
            deactivate_raw_material_in_session(self.db, 1)

        self.assertEqual(409, ctx.exception.status_code)
        self.assertTrue(self.db.get(RawMaterial, 1).is_active)

    def test_create_and_update_raw_material_location_normalizes_and_handles_partner(self) -> None:
        created = create_raw_material_location_in_session(
            self.db,
            RawMaterialLocationCreate(
                location_code=" loc-b ",
                location_name=" Location B ",
                location_type=" outsource_vendor ",
                partner_id=1,
                memo=" vendor memo ",
            ),
        )
        updated = update_raw_material_location_in_session(
            self.db,
            location_id=created.raw_material_location_id,
            payload=RawMaterialLocationUpdate(
                location_name=" Location B2 ",
                location_type=" other ",
                partner_id=None,
                memo=" updated location ",
            ),
        )
        self.db.commit()

        location = self.db.get(RawMaterialLocation, created.raw_material_location_id)

        self.assertEqual("LOC-B", created.location_code)
        self.assertEqual("OUTSOURCE_VENDOR", created.location_type)
        self.assertEqual("Location B2", updated.location_name)
        self.assertEqual("OTHER", location.location_type)
        self.assertIsNone(location.partner_id)
        self.assertEqual("updated location", location.memo)

    def test_deactivate_location_allows_zero_inventory_and_rejects_existing_inventory(self) -> None:
        created = create_raw_material_location_in_session(
            self.db,
            RawMaterialLocationCreate(
                location_code="EMPTY",
                location_name="Empty Location",
                location_type="INTERNAL_WAREHOUSE",
            ),
        )
        result = deactivate_raw_material_location_in_session(self.db, created.raw_material_location_id)
        self.db.commit()

        self.assertFalse(result.is_active)
        self.assertFalse(self.db.get(RawMaterialLocation, created.raw_material_location_id).is_active)

        with self.assertRaises(HTTPException) as ctx:
            deactivate_raw_material_location_in_session(self.db, 1)

        self.assertEqual(409, ctx.exception.status_code)
        self.assertTrue(self.db.get(RawMaterialLocation, 1).is_active)

    def _seed_raw_materials(self) -> None:
        self.now = datetime(2026, 7, 10, 9, 30)
        self.db.add_all(
            [
                Partner(partner_id=1, partner_type="VENDOR", name="Vendor A", business_no="100-00-00001"),
                RawMaterial(
                    raw_material_id=1,
                    material_code="RM-A",
                    material_name="Material A",
                    uom="M",
                    standard_unit_cost=Decimal("2.5000"),
                    is_active=True,
                ),
                RawMaterial(
                    raw_material_id=2,
                    material_code="RM-B",
                    material_name="Material B",
                    uom="M",
                    standard_unit_cost=Decimal("1.0000"),
                    is_active=True,
                ),
                RawMaterial(
                    raw_material_id=3,
                    material_code="RM-C",
                    material_name="Inactive Material",
                    uom="M",
                    is_active=False,
                ),
                RawMaterialLocation(
                    raw_material_location_id=1,
                    location_code="MAIN",
                    location_name="Main Warehouse",
                    location_type="INTERNAL_WAREHOUSE",
                    is_active=True,
                ),
                RawMaterialLocation(
                    raw_material_location_id=2,
                    location_code="VEN-A",
                    location_name="Vendor Storage",
                    location_type="OUTSOURCE_VENDOR",
                    partner_id=1,
                    is_active=True,
                ),
                RawMaterialInventory(
                    raw_material_inventory_id=1,
                    raw_material_id=1,
                    raw_material_location_id=1,
                    current_qty=Decimal("10.00"),
                ),
                RawMaterialInventory(
                    raw_material_inventory_id=2,
                    raw_material_id=1,
                    raw_material_location_id=2,
                    current_qty=Decimal("5.00"),
                ),
                RawMaterialInventoryLot(
                    raw_material_inventory_lot_id=1,
                    raw_material_id=1,
                    raw_material_location_id=1,
                    lot_no="RMLOT-A1",
                    current_qty=Decimal("10.00"),
                    unit_cost=Decimal("2.5000"),
                ),
                RawMaterialInventoryLot(
                    raw_material_inventory_lot_id=2,
                    raw_material_id=1,
                    raw_material_location_id=2,
                    lot_no="RMLOT-A2",
                    current_qty=Decimal("5.00"),
                    unit_cost=Decimal("3.0000"),
                ),
                RawMaterialInventoryLot(
                    raw_material_inventory_lot_id=3,
                    raw_material_id=2,
                    raw_material_location_id=1,
                    lot_no="RMLOT-B0",
                    current_qty=Decimal("0.00"),
                    unit_cost=Decimal("1.0000"),
                ),
                RawMaterialInventoryMovement(
                    raw_material_inventory_movement_id=1,
                    raw_material_id=1,
                    raw_material_location_id=1,
                    raw_material_inventory_lot_id=1,
                    lot_no="RMLOT-A1",
                    movement_type="INBOUND",
                    qty=Decimal("10.00"),
                    balance_after=Decimal("10.00"),
                    unit_cost_snapshot=Decimal("2.5000"),
                    amount_snapshot=Decimal("25.00"),
                    created_at=self.now - timedelta(days=2),
                ),
                RawMaterialInventoryMovement(
                    raw_material_inventory_movement_id=2,
                    raw_material_id=1,
                    raw_material_location_id=1,
                    raw_material_inventory_lot_id=1,
                    lot_no="RMLOT-A1",
                    movement_type="TRANSFER_OUT",
                    qty=Decimal("-5.00"),
                    balance_after=Decimal("5.00"),
                    unit_cost_snapshot=Decimal("2.5000"),
                    amount_snapshot=Decimal("12.50"),
                    transfer_key="RMTR-1",
                    created_at=self.now - timedelta(hours=1),
                ),
                RawMaterialInventoryMovement(
                    raw_material_inventory_movement_id=3,
                    raw_material_id=1,
                    raw_material_location_id=2,
                    raw_material_inventory_lot_id=2,
                    lot_no="RMLOT-A2",
                    movement_type="TRANSFER_IN",
                    qty=Decimal("5.00"),
                    balance_after=Decimal("5.00"),
                    unit_cost_snapshot=Decimal("3.0000"),
                    amount_snapshot=Decimal("15.00"),
                    transfer_key="RMTR-1",
                    created_at=self.now,
                ),
            ]
        )
        self.db.commit()
