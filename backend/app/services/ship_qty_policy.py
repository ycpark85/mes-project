import math
import re


DIRECT_SHIP_KEYWORDS = (
    "덴티움",
    "오스템임플란트",
    "네오바이오텍",
    "제이시스메디칼",
)

CAREGEN_KEYWORD = "케어젠"

STOCK_REPLENISHMENT_PARTNER_NAME = "세미산업"
STOCK_REPLENISHMENT_BUSINESS_NO = "1390178012"


def normalize_partner_name(name: str) -> str:
    if not name:
        return ""

    normalized = name.strip()
    normalized = normalized.replace("주식회사", "")
    normalized = normalized.replace("(주)", "")
    normalized = normalized.replace("㈜", "")
    normalized = re.sub(r"\s+", "", normalized)

    return normalized


def normalize_business_no(business_no: str | None) -> str:
    if not business_no:
        return ""

    return re.sub(r"[^0-9]", "", business_no)


def is_stock_replenishment_partner(
    partner_name: str | None,
    business_no: str | None,
) -> bool:
    normalized_name = normalize_partner_name(partner_name or "")
    normalized_business_no = normalize_business_no(business_no)

    return (
        normalized_name == STOCK_REPLENISHMENT_PARTNER_NAME
        and normalized_business_no == STOCK_REPLENISHMENT_BUSINESS_NO
    )


def calculate_ship_qty(partner_name: str, order_qty: int) -> int:
    normalized_name = normalize_partner_name(partner_name)

    if any(keyword in normalized_name for keyword in DIRECT_SHIP_KEYWORDS):
        return order_qty

    if CAREGEN_KEYWORD in normalized_name:
        return order_qty + 100

    return math.ceil(order_qty * 1.02)