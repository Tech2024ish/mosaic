import csv
import io
from collections.abc import Iterator
from typing import BinaryIO

from app.domain.ingestion.contracts import ParsedRow


class CsvFormatError(ValueError):
    def __init__(self, message: str, code: str = "invalid_csv") -> None:
        super().__init__(message)
        self.code = code


def parse_csv(
    stream: BinaryIO, required_columns: set[str], aliases: dict[str, str]
) -> Iterator[ParsedRow]:
    """Stream CSV rows without reading the complete upload into memory."""
    text_stream = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    try:
        reader = csv.DictReader(text_stream)
        if not reader.fieldnames:
            raise CsvFormatError("CSV must contain a header row", "missing_header")
        canonical_headers = {
            aliases.get(header.strip().lower(), header.strip().lower())
            for header in reader.fieldnames
        }
        missing = required_columns - canonical_headers
        if missing:
            raise CsvFormatError(
                f"Missing required columns: {', '.join(sorted(missing))}", "missing_columns"
            )
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                yield ParsedRow(row_number, {"__row_error": "malformed_row"})
                continue
            values = {
                aliases.get(str(key).strip().lower(), str(key).strip().lower()): (
                    value or ""
                ).strip()
                for key, value in row.items()
            }
            yield ParsedRow(row_number, values)
    except UnicodeDecodeError as exc:
        raise CsvFormatError("CSV must be valid UTF-8", "invalid_encoding") from exc
    except csv.Error as exc:
        raise CsvFormatError("CSV structure is malformed", "malformed_csv") from exc
    finally:
        text_stream.detach()
