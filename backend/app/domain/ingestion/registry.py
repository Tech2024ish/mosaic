from collections.abc import Callable, Iterator

from app.domain.ingestion.contracts import ParsedRow
from app.domain.ingestion.csv_parser import parse_csv
from app.domain.ingestion.sales import ALIASES, REQUIRED_COLUMNS

Parser = Callable[..., Iterator[ParsedRow]]


def get_dataset_parser(dataset_type: str) -> tuple[Parser, set[str], dict[str, str]]:
    if dataset_type == "sales_history":
        return parse_csv, REQUIRED_COLUMNS, ALIASES
    raise ValueError(f"Unsupported dataset type: {dataset_type}")
