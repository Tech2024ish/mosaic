from datetime import date
from decimal import Decimal, InvalidOperation

from app.domain.ingestion.contracts import ParsedRow, ValidationIssue


def _value(row: ParsedRow, field: str, issues: list[ValidationIssue]) -> str:
    value = row.values.get(field, "").strip()
    if not value:
        issues.append(
            ValidationIssue(row.row_number, "required_value", f"{field} is required", field)
        )
    return value


def _boolean(value: str, row: ParsedRow, field: str, issues: list[ValidationIssue]) -> bool:
    if not value:
        return True
    if value.lower() in {"true", "1", "yes", "y"}:
        return True
    if value.lower() in {"false", "0", "no", "n"}:
        return False
    issues.append(
        ValidationIssue(
            row.row_number, "invalid_boolean", f"{field} must be true or false", field, value
        )
    )
    return True


def normalize_master_row(
    row: ParsedRow, dataset_type: str
) -> tuple[dict[str, object] | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if row.values.get("__row_error"):
        return None, [
            ValidationIssue(
                row.row_number, "malformed_row", "Row contains more fields than its header"
            )
        ]
    if dataset_type == "products":
        code = _value(row, "product_code", issues).upper()
        name = _value(row, "product_name", issues)
        return (
            (
                {
                    "product_code": code,
                    "name": name,
                    "description": row.values.get("description") or None,
                    "category": row.values.get("category") or None,
                    "unit_of_measure": row.values.get("unit_of_measure") or None,
                    "is_active": _boolean(
                        row.values.get("is_active", ""), row, "is_active", issues
                    ),
                    "row_number": row.row_number,
                },
                issues,
            )
            if not issues
            else (None, issues)
        )
    if dataset_type == "warehouses":
        code = _value(row, "warehouse_code", issues).upper()
        name = _value(row, "warehouse_name", issues)
        return (
            (
                {
                    "warehouse_code": code,
                    "name": name,
                    "location": row.values.get("location") or None,
                    "is_active": _boolean(
                        row.values.get("is_active", ""), row, "is_active", issues
                    ),
                    "row_number": row.row_number,
                },
                issues,
            )
            if not issues
            else (None, issues)
        )
    if dataset_type == "suppliers":
        code = _value(row, "supplier_code", issues).upper()
        name = _value(row, "supplier_name", issues)
        email = row.values.get("contact_email") or None
        if email and ("@" not in email or " " in email):
            issues.append(
                ValidationIssue(
                    row.row_number,
                    "invalid_email",
                    "contact_email must be a valid email",
                    "contact_email",
                    email,
                )
            )
        return (
            (
                {
                    "supplier_code": code,
                    "name": name,
                    "contact_name": row.values.get("contact_name") or None,
                    "contact_email": email,
                    "contact_phone": row.values.get("contact_phone") or None,
                    "is_active": _boolean(
                        row.values.get("is_active", ""), row, "is_active", issues
                    ),
                    "row_number": row.row_number,
                },
                issues,
            )
            if not issues
            else (None, issues)
        )
    if dataset_type == "inventory_snapshots":
        snapshot_date = _value(row, "snapshot_date", issues)
        product_code = _value(row, "product_code", issues).upper()
        warehouse_code = _value(row, "warehouse_code", issues).upper()
        quantity_value = _value(row, "quantity_on_hand", issues)
        cost_value = row.values.get("unit_cost", "")
        try:
            parsed_date = date.fromisoformat(snapshot_date)
        except ValueError:
            issues.append(
                ValidationIssue(
                    row.row_number,
                    "invalid_date",
                    "snapshot_date must be YYYY-MM-DD",
                    "snapshot_date",
                    snapshot_date,
                )
            )
            parsed_date = None
        try:
            quantity = Decimal(quantity_value)
            if quantity < 0:
                raise InvalidOperation
        except InvalidOperation:
            issues.append(
                ValidationIssue(
                    row.row_number,
                    "invalid_quantity",
                    "quantity_on_hand must be zero or greater",
                    "quantity_on_hand",
                    quantity_value,
                )
            )
            quantity = None
        try:
            cost = Decimal(cost_value) if cost_value else None
            if cost is not None and cost < 0:
                raise InvalidOperation
        except InvalidOperation:
            issues.append(
                ValidationIssue(
                    row.row_number,
                    "invalid_cost",
                    "unit_cost must be zero or greater",
                    "unit_cost",
                    cost_value,
                )
            )
            cost = None
        if issues or parsed_date is None or quantity is None:
            return None, issues
        return {
            "snapshot_date": parsed_date,
            "product_code": product_code,
            "warehouse_code": warehouse_code,
            "quantity_on_hand": quantity,
            "unit_cost": cost,
            "row_number": row.row_number,
        }, []
    raise ValueError(f"Unsupported master dataset: {dataset_type}")
