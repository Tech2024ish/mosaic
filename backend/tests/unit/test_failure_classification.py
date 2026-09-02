from app.domain.ingestion.failure import FailureCategory, classify_failure


def test_failure_categories_are_safe_and_operational() -> None:
    assert classify_failure(OSError("storage unavailable")) == FailureCategory.STORAGE_ERROR
    assert (
        classify_failure(ValueError("unexpected processing input"))
        == FailureCategory.PROCESSING_ERROR
    )
