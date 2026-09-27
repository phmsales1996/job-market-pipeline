import pytest
from ingestion import ats

def test_all_companies_succeeded():
    summary = ats.summarise_extract("greenhouse", "2026-09-26", 3, [])
    assert summary["companies"] == 3
    assert summary["succeeded"] == 3
    assert summary["failed"] == 0

def test_some_failed():
    summary = ats.summarise_extract("greenhouse", "2026-09-26", 3, ["beta"])
    assert summary["companies"] == 3
    assert summary["succeeded"] == 2
    assert summary["failed"] == 1
    assert "beta" in summary["failed_slugs"]

def test_all_failed():
    with pytest.raises(ValueError):
        ats.summarise_extract("greenhouse", "2026-09-26", 3, ["alpha", "beta", "gamma"])