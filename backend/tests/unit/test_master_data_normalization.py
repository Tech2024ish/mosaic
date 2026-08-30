from app.domain.ingestion.contracts import ParsedRow
from app.domain.master_data.normalization import normalize_master_row


def test_product_row_is_normalized() -> None:
    normalized, errors = normalize_master_row(
        ParsedRow(2, {"product_code": " p-1 ", "product_name": " Widget ", "is_active": "no"}),
        "products",
    )
    assert errors == []
    assert normalized is not None
    assert normalized["product_code"] == "P-1"
    assert normalized["name"] == "Widget"
    assert normalized["is_active"] is False


def test_inventory_row_rejects_invalid_values() -> None:
    normalized, errors = normalize_master_row(
        ParsedRow(
            4,
            {
                "snapshot_date": "not-a-date",
                "product_code": "P-1",
                "warehouse_code": "W-1",
                "quantity_on_hand": "-2",
                "unit_cost": "bad",
            },
        ),
        "inventory_snapshots",
    )
    assert normalized is None
    assert {issue.error_code for issue in errors} == {
        "invalid_date",
        "invalid_quantity",
        "invalid_cost",
    }


def test_required_master_columns_are_reported() -> None:
    normalized, errors = normalize_master_row(
        ParsedRow(5, {"product_code": "", "product_name": ""}), "products"
    )
    assert normalized is None
    assert [issue.error_code for issue in errors] == ["required_value", "required_value"]
