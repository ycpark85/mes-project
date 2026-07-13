from __future__ import annotations

import unittest

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from app.models.partner import Partner
from app.models.product import Product


class BusinessSearchIndexTests(unittest.TestCase):
    def test_partial_search_fields_compile_as_trigram_gin_indexes(self) -> None:
        expected_indexes = (
            (Partner, "ix_partner__name_trgm", "name gin_trgm_ops"),
            (Product, "ix_product__product_code_trgm", "product_code gin_trgm_ops"),
            (Product, "ix_product__product_name_trgm", "product_name gin_trgm_ops"),
        )

        for model, index_name, expected_column_ddl in expected_indexes:
            with self.subTest(index=index_name):
                index = next(
                    index for index in model.__table__.indexes if index.name == index_name
                )
                ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

                self.assertIn("USING gin", ddl)
                self.assertIn(expected_column_ddl, ddl)


if __name__ == "__main__":
    unittest.main()
