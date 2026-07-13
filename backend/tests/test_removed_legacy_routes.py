from __future__ import annotations

import unittest

from fastapi.routing import APIRoute

from app.main import app


class RemovedLegacyRouteTests(unittest.TestCase):
    def test_unused_legacy_write_routes_are_not_registered(self) -> None:
        registered_routes = {
            (method, route.path)
            for route in app.routes
            if isinstance(route, APIRoute)
            for method in route.methods
        }

        removed_routes = {
            ("POST", "/api/v1/lot-steps/{lot_step_id}/start"),
            ("POST", "/api/v1/lot-steps/{lot_step_id}/complete"),
            (
                "POST",
                "/api/v1/outsource-work-instructions/purchase-orders/items/"
                "{outsource_purchase_order_item_id}/vendor-receive",
            ),
            (
                "POST",
                "/api/v1/outsource-work-instructions/purchase-orders/items/"
                "{outsource_purchase_order_item_id}/work-done",
            ),
            (
                "POST",
                "/api/v1/outsource-work-instructions/purchase-orders/items/"
                "{outsource_purchase_order_item_id}/ship",
            ),
        }

        self.assertTrue(removed_routes.isdisjoint(registered_routes))

    def test_purchase_order_detail_route_remains_registered(self) -> None:
        detail_routes = {
            (method, route.path)
            for route in app.routes
            if isinstance(route, APIRoute)
            for method in route.methods
        }

        self.assertIn(
            (
                "GET",
                "/api/v1/outsource-work-instructions/purchase-orders/"
                "{outsource_purchase_order_id}",
            ),
            detail_routes,
        )


if __name__ == "__main__":
    unittest.main()
