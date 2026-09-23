import pytest
from ingestion.dates import require_date

def test_accepts_valid_date():
    assert require_date("2026-09-23") == ("2026-09-23")

def test_rejects_none():
    with pytest.raises(ValueError):
        require_date(None)

def test_rejects_bad_format():
    with pytest.raises(ValueError):
        require_date("23/09/2026")