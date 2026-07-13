import unittest

from app.services.routing_policy import (
    get_available_process_types,
    is_inspection_only_template_name,
)


class RoutingPolicyTests(unittest.TestCase):
    def test_inspection_only_has_no_outsource_processes(self):
        template_name = "\uac80\uc218\ub9cc\uc9c4\ud589"

        self.assertTrue(is_inspection_only_template_name(template_name))
        self.assertEqual([], get_available_process_types(template_name))

    def test_blank_product_uses_cut_only(self):
        self.assertEqual(["CUT"], get_available_process_types("\ubb34\uc9c0"))
        self.assertEqual(["CUT"], get_available_process_types("  \ubb34\uc9c0 \uc81c\ud488  "))

    def test_print_product_uses_cut_and_print(self):
        self.assertEqual(["CUT", "PRINT"], get_available_process_types("\uc778\uc1c4"))

    def test_unknown_defaults_to_cut(self):
        self.assertEqual(["CUT"], get_available_process_types("\uae30\ud0c0"))


if __name__ == "__main__":
    unittest.main()
