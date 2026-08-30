from collections.abc import Callable, Iterator

from app.domain.ingestion.contracts import ParsedRow
from app.domain.ingestion.csv_parser import parse_csv
from app.domain.ingestion.sales import ALIASES, REQUIRED_COLUMNS

Parser = Callable[..., Iterator[ParsedRow]]


def get_dataset_parser(dataset_type: str) -> tuple[Parser, set[str], dict[str, str]]:
    if dataset_type == "sales_history":
        return parse_csv, REQUIRED_COLUMNS, ALIASES
    formats = {
        "products": (
            {"product_code", "product_name"},
            {
                "product code": "product_code",
                "sku": "product_code",
                "product_name": "product_name",
                "product name": "product_name",
            },
        ),
        "warehouses": (
            {"warehouse_code", "warehouse_name"},
            {
                "warehouse": "warehouse_code",
                "warehouse code": "warehouse_code",
                "warehouse_name": "warehouse_name",
                "warehouse name": "warehouse_name",
            },
        ),
        "suppliers": (
            {"supplier_code", "supplier_name"},
            {
                "supplier": "supplier_code",
                "supplier code": "supplier_code",
                "supplier_name": "supplier_name",
                "supplier name": "supplier_name",
            },
        ),
        "inventory_snapshots": (
            {"snapshot_date", "product_code", "warehouse_code", "quantity_on_hand"},
            {
                "date": "snapshot_date",
                "product": "product_code",
                "sku": "product_code",
                "warehouse": "warehouse_code",
                "quantity": "quantity_on_hand",
                "qty": "quantity_on_hand",
            },
        ),
    }
    if dataset_type in formats:
        required, aliases = formats[dataset_type]
        return parse_csv, required, aliases
    raise ValueError(f"Unsupported dataset type: {dataset_type}")
