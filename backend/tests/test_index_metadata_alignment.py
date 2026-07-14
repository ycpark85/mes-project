from __future__ import annotations

import unittest

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.order_line_plan_history import OrderLinePlanHistory
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


class IndexMetadataAlignmentTests(unittest.TestCase):
    def test_drawing_current_revision_foreign_key_breaks_ddl_cycle(self) -> None:
        foreign_key = next(iter(Drawing.__table__.c.current_revision_id.foreign_keys))

        self.assertEqual("fk_drawing__current_revision_id", foreign_key.constraint.name)
        self.assertTrue(foreign_key.use_alter)
        self.assertEqual("SET NULL", foreign_key.ondelete)

    def test_latest_plan_history_index_matches_query_order(self) -> None:
        index = next(
            item
            for item in OrderLinePlanHistory.__table__.indexes
            if item.name == "ix_order_line_plan_history__order_line_latest"
        )

        expressions = [str(expression) for expression in index.expressions]
        self.assertEqual(
            [
                "order_line_plan_history.order_line_id",
                "order_line_plan_history.created_at DESC",
                "order_line_plan_history.plan_history_id DESC",
            ],
            expressions,
        )

    def test_active_instruction_item_index_is_partial_and_unique(self) -> None:
        index = next(
            item
            for item in OutsourceWorkInstructionItem.__table__.indexes
            if item.name == "uq_owi_item__active_process_lot"
        )

        self.assertTrue(index.unique)
        self.assertEqual(
            "is_active = true",
            str(index.dialect_options["postgresql"]["where"]),
        )
        self.assertEqual(
            "is_active = 1",
            str(index.dialect_options["sqlite"]["where"]),
        )

    def test_inactive_instruction_can_be_replaced_but_active_duplicate_is_blocked(
        self,
    ) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            engine,
            tables=[OutsourceWorkInstructionItem.__table__],
        )
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        db = SessionLocal()

        try:
            first = OutsourceWorkInstructionItem(
                outsource_work_instruction_item_id=1,
                outsource_work_instruction_id=1,
                lot_id=1,
                process_type="CUT",
                is_active=True,
            )
            db.add(first)
            db.commit()

            db.add(
                OutsourceWorkInstructionItem(
                    outsource_work_instruction_item_id=2,
                    outsource_work_instruction_id=2,
                    lot_id=1,
                    process_type="CUT",
                    is_active=True,
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

            first.is_active = False
            db.add(
                OutsourceWorkInstructionItem(
                    outsource_work_instruction_item_id=3,
                    outsource_work_instruction_id=3,
                    lot_id=1,
                    process_type="CUT",
                    is_active=True,
                )
            )
            db.commit()
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
