from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    values: dict[str, str]


@dataclass(frozen=True)
class NormalizedSale:
    row_number: int
    product_code: str
    sale_date: date
    quantity: Decimal
    unit_price: Decimal
    warehouse_code: str


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int
    error_code: str
    message: str
    field_name: str | None = None
    raw_value: str | None = None
