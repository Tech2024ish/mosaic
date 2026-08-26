import hashlib

from app.domain.ingestion.contracts import NormalizedSale


def row_fingerprint(sale: NormalizedSale) -> str:
    payload = "|".join(
        [
            sale.product_code,
            sale.sale_date.isoformat(),
            format(sale.quantity, "f"),
            format(sale.unit_price, "f"),
            sale.warehouse_code,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def file_fingerprint(content_sha256: str, dataset_type: str, organization_id: str) -> str:
    return hashlib.sha256(f"{organization_id}|{dataset_type}|{content_sha256}".encode()).hexdigest()
