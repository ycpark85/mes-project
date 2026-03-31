import math
import re

DIRECT_SHIP_KEYWORDS = (
    "덴티움",
    "오스템임플란트",
    "네오바이오텍",
    "제이시스메디칼",
)

CAREGEN_KEYWORD = "케어젠"


def normalize_partner_name(name: str) -> str:
    if not name:
        return ""

    normalized = name.strip()
    normalized = normalized.replace("주식회사", "")
    normalized = normalized.replace("(주)", "")
    normalized = normalized.replace("㈜", "")
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def calculate_ship_qty(partner_name: str, order_qty: int) -> int:
    normalized_name = normalize_partner_name(partner_name)

    if any(keyword in normalized_name for keyword in DIRECT_SHIP_KEYWORDS):
        return order_qty

    if CAREGEN_KEYWORD in normalized_name:
        return order_qty + 100

    return math.ceil(order_qty * 1.02)