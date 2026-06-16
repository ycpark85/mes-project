from __future__ import annotations


INSPECTION_ONLY_TEMPLATE_NAME = "\uAC80\uC218\uB9CC\uC9C4\uD589"


def normalize_routing_template_name(template_name: str | None) -> str:
    return "".join((template_name or "").split())


def is_inspection_only_template_name(template_name: str | None) -> bool:
    return normalize_routing_template_name(template_name) == INSPECTION_ONLY_TEMPLATE_NAME
