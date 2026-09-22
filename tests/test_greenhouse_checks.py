import pytest
from ingestion import greenhouse_checks

def test_all_present():
    expected = {"a", "b"}
    counts = {"a": 1, "b": 1}
    greenhouse_checks.evaluate_files(expected, counts, "2026-09-22")

def test_nothing_landed():
    expected = {"a", "b"}
    counts = {}
    with pytest.raises(ValueError):
        greenhouse_checks.evaluate_files(expected, counts, "2026-09-22")

def test_most_missing():
    expected = {"a", "b", "c"}
    counts = {"a": 1}
    with pytest.raises(ValueError):
        greenhouse_checks.evaluate_files(expected, counts, "2026-09-22")