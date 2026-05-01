"""Service report parsing, aggregation, sorting, and pagination."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, NamedTuple, Sequence


class ServiceReportItem(NamedTuple):
    mode: str
    name: str
    price: float
    quantity: float


class ServiceReportRow(NamedTuple):
    name: str
    count: float
    revenue: float
    avg: float


class ProductReportRow(NamedTuple):
    name: str
    count: float
    revenue: float


class ServiceReportData(NamedTuple):
    services: tuple[ServiceReportRow, ...]
    products: tuple[ProductReportRow, ...]


class ServiceReportPage(NamedTuple):
    rows: tuple[Any, ...]
    page: int
    max_page: int
    total: int


def parse_service_report_item(segment: Any) -> ServiceReportItem | None:
    text = str(segment or "").strip()
    if not text:
        return None

    parts = [part.strip() for part in text.split("~")]
    if len(parts) == 4:
        try:
            mode = parts[0].lower()
            name = parts[1]
            price = float(parts[2])
            quantity = float(parts[3])
        except (TypeError, ValueError):
            return None
        if not name or quantity <= 0:
            return None
        return ServiceReportItem(mode, name, price, quantity)

    if ":" in text:
        name, price_text = text.rsplit(":", 1)
        try:
            price = float(price_text.strip())
        except (TypeError, ValueError):
            return None
        name = name.strip()
        if not name:
            return None
        return ServiceReportItem("services", name, price, 1.0)

    return None


def build_service_report_rows(
    rows: Sequence[dict[str, Any]],
    *,
    sort_col: str = "Revenue",
    sort_reverse: bool = True,
) -> ServiceReportData:
    services: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"count": 0.0, "revenue": 0.0})
    products: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"count": 0.0, "revenue": 0.0})

    for row in rows:
        for segment in str(row.get("items_raw", "") or "").split("|"):
            item = parse_service_report_item(segment)
            if item is None:
                continue
            bucket = services if item.mode == "services" else products
            bucket[item.name]["count"] += item.quantity
            bucket[item.name]["revenue"] += item.price * item.quantity

    service_rows = [
        ServiceReportRow(
            name,
            data["count"],
            data["revenue"],
            data["revenue"] / data["count"] if data["count"] else 0.0,
        )
        for name, data in services.items()
    ]
    sort_keys = {
        "Service": lambda row: row.name.lower(),
        "Count": lambda row: row.count,
        "Revenue": lambda row: row.revenue,
        "Avg": lambda row: row.avg,
    }
    service_rows.sort(key=sort_keys.get(sort_col, sort_keys["Revenue"]), reverse=sort_reverse)

    product_rows = [
        ProductReportRow(name, data["count"], data["revenue"])
        for name, data in products.items()
    ]
    product_rows.sort(key=lambda row: row.revenue, reverse=True)

    return ServiceReportData(tuple(service_rows), tuple(product_rows))


def max_service_report_page(total: int, page_size: int) -> int:
    if total <= 0 or page_size <= 0:
        return 0
    return (total - 1) // page_size


def paginate_service_report_rows(
    rows: Sequence[Any],
    page: int,
    page_size: int,
) -> ServiceReportPage:
    total = len(rows)
    max_page = max_service_report_page(total, page_size)
    safe_page = min(max(0, int(page or 0)), max_page)
    if page_size <= 0:
        return ServiceReportPage(tuple(), safe_page, max_page, total)
    start = safe_page * page_size
    end = start + page_size
    return ServiceReportPage(tuple(rows[start:end]), safe_page, max_page, total)


def format_report_quantity(value: float) -> str:
    numeric = float(value or 0)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.3f}".rstrip("0").rstrip(".")


def service_report_tree_values(
    row: ServiceReportRow,
    currency: Callable[[float], str],
) -> tuple[str, str, str, str]:
    return (
        row.name,
        format_report_quantity(row.count),
        currency(row.revenue),
        currency(row.avg),
    )


def product_report_tree_values(
    row: ProductReportRow,
    currency: Callable[[float], str],
) -> tuple[str, str, str]:
    return (
        row.name,
        format_report_quantity(row.count),
        currency(row.revenue),
    )
