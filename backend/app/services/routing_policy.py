from __future__ import annotations


INSPECTION_ONLY_TEMPLATE_NAME = "\uAC80\uC218\uB9CC\uC9C4\uD589"


def normalize_routing_template_name(template_name: str | None) -> str:
    return "".join((template_name or "").split())


def is_inspection_only_template_name(template_name: str | None) -> bool:
    return normalize_routing_template_name(template_name) == INSPECTION_ONLY_TEMPLATE_NAME


def get_available_process_types(template_name: str | None) -> list[str]:
    name = (template_name or "").strip()

    if is_inspection_only_template_name(name):
        return []

    if "\ubb34\uc9c0" in name:
        return ["CUT"]

    if "\uc778\uc1c4" in name:
        return ["CUT", "PRINT"]

    return ["CUT"]


def is_purchase_order_target_process(
    process_type: str,
    template_name: str | None,
) -> bool:
    return process_type in get_available_process_types(template_name)


def get_purchase_order_inbound_partner_name(
    process_type: str,
    template_name: str | None,
) -> str:
    available_process_types = get_available_process_types(template_name)
    is_print_product = "PRINT" in available_process_types

    if process_type == "CUT":
        return "\uc0c1\ub9bc" if is_print_product else "\ubcf4\ud604"

    if process_type == "PRINT":
        return "\uc0c1\ub9bc"

    return ""
