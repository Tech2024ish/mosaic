import io
from datetime import date
from decimal import Decimal

import pytest

from app.domain.ingestion.csv_parser import CsvFormatError, parse_csv
from app.domain.ingestion.fingerprint import file_fingerprint, row_fingerprint
from app.domain.ingestion.sales import ALIASES, REQUIRED_COLUMNS, normalize_and_validate


def test_parser_streams_aliases_into_canonical_columns() -> None:
    rows = list(
        parse_csv(
            io.BytesIO(b"SKU,Date,Qty,Price,Warehouse\nP-1,2026-01-02,2,10.50,JHB\n"),
            REQUIRED_COLUMNS,
            ALIASES,
        )
    )
    assert rows[0].values == {
        "product_code": "P-1",
        "sale_date": "2026-01-02",
        "quantity": "2",
        "unit_price": "10.50",
        "warehouse_code": "JHB",
    }


def test_parser_rejects_missing_columns() -> None:
    with pytest.raises(CsvFormatError, match="Missing required columns"):
        list(parse_csv(io.BytesIO(b"sku,qty\nP-1,2\n"), REQUIRED_COLUMNS, ALIASES))


def test_validation_normalizes_decimal_and_rejects_bad_values() -> None:
    valid, issues = normalize_and_validate(
        type(
            "Row",
            (),
            {
                "row_number": 2,
                "values": {
                    "product_code": "P-1",
                    "sale_date": "2026-01-02",
                    "quantity": "2.50",
                    "unit_price": "10.00",
                    "warehouse_code": "JHB",
                },
            },
        )()
    )
    assert not issues
    assert valid is not None
    assert valid.sale_date == date(2026, 1, 2)
    assert valid.quantity == Decimal("2.50")
    invalid, issues = normalize_and_validate(
        type(
            "Row",
            (),
            {
                "row_number": 3,
                "values": {
                    "product_code": "P-1",
                    "sale_date": "bad",
                    "quantity": "-1",
                    "unit_price": "x",
                    "warehouse_code": "JHB",
                },
            },
        )()
    )
    assert invalid is None
    assert {issue.error_code for issue in issues} == {
        "invalid_date",
        "invalid_quantity",
        "invalid_price",
    }


def test_fingerprints_are_deterministic_and_tenant_scoped() -> None:
    rows = list(
        parse_csv(
            io.BytesIO(
                b"product_code,sale_date,quantity,unit_price,warehouse_code\nP-1,2026-01-02,2,10,JHB\n"
            ),
            REQUIRED_COLUMNS,
            ALIASES,
        )
    )
    sale, _ = normalize_and_validate(rows[0])
    assert sale is not None
    assert row_fingerprint(sale) == row_fingerprint(sale)
    assert file_fingerprint("abc", "sales_history", "org-a") != file_fingerprint(
        "abc", "sales_history", "org-b"
    )
