from datetime import date
from decimal import Decimal, InvalidOperation

from app.domain.ingestion.contracts import NormalizedSale, ParsedRow, ValidationIssue

REQUIRED_COLUMNS = {"product_code", "sale_date", "quantity", "unit_price", "warehouse_code"}
ALIASES = {
    "product_code": "product_code",
    "product id": "product_code",
    "product_id": "product_code",
    "sku": "product_code",
    "sale_date": "sale_date",
    "date": "sale_date",
    "quantity": "quantity",
    "qty": "quantity",
    "unit_price": "unit_price",
    "unit price": "unit_price",
    "price": "unit_price",
    "warehouse_code": "warehouse_code",
    "warehouse": "warehouse_code",
    "warehouse id": "warehouse_code",
}


def normalize_and_validate(row: ParsedRow) -> tuple[NormalizedSale | None, list[ValidationIssue]]:
    if row.values.get("__row_error"):
        return None, [
            ValidationIssue(
                row.row_number, "malformed_row", "Row contains more fields than its header"
            )
        ]
    issues: list[ValidationIssue] = []

    def required(field: str) -> str:
        value = row.values.get(field, "")
        if not value:
            issues.append(
                ValidationIssue(row.row_number, "required_value", f"{field} is required", field)
            )
        return value

    product_code = required("product_code")
    warehouse_code = required("warehouse_code")
    date_value = required("sale_date")
    quantity_value = required("quantity")
    price_value = required("unit_price")
    if issues:
        return None, issues

    try:
        sale_date = date.fromisoformat(date_value)
    except ValueError:
        issues.append(
            ValidationIssue(
                row.row_number,
                "invalid_date",
                "sale_date must be YYYY-MM-DD",
                "sale_date",
                date_value,
            )
        )
        sale_date = None
    try:
        quantity = Decimal(quantity_value)
        if quantity <= 0:
            raise InvalidOperation
    except InvalidOperation:
        issues.append(
            ValidationIssue(
                row.row_number,
                "invalid_quantity",
                "quantity must be greater than zero",
                "quantity",
                quantity_value,
            )
        )
        quantity = None
    try:
        unit_price = Decimal(price_value)
        if unit_price < 0:
            raise InvalidOperation
    except InvalidOperation:
        issues.append(
            ValidationIssue(
                row.row_number,
                "invalid_price",
                "unit_price must be zero or greater",
                "unit_price",
                price_value,
            )
        )
        unit_price = None
    if issues or sale_date is None or quantity is None or unit_price is None:
        return None, issues
    return NormalizedSale(
        row.row_number, product_code, sale_date, quantity, unit_price, warehouse_code
    ), []
