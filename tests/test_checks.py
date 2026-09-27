import pytest
from ingestion import checks

def test_all_present():
    expected = {"a", "b"}
    counts = {"a": 1, "b": 1}
    checks.evaluate_files(expected, counts, "2026-09-22")

def test_nothing_landed():
    expected = {"a", "b"}
    counts = {}
    with pytest.raises(ValueError):
        checks.evaluate_files(expected, counts, "2026-09-22")

def test_most_missing():
    expected = {"a", "b", "c"}
    counts = {"a": 1}
    with pytest.raises(ValueError):
        checks.evaluate_files(expected, counts, "2026-09-22")

def test_missing_but_extract_said_it_failed():
    # b's fetch failed, so no file for b is expected: a warning, not a failure.
    expected = {"a", "b", "c"}
    counts = {"a": 1, "c": 1}
    checks.evaluate_files(expected, counts, "2026-09-22", known_failed={"b"})

def test_missing_although_extract_said_it_succeeded():
    # Nothing failed to fetch, yet b landed no file: always a bug, whatever the count.
    expected = {"a", "b", "c"}
    counts = {"a": 1, "c": 1}
    with pytest.raises(ValueError, match="reported success"):
        checks.evaluate_files(expected, counts, "2026-09-22", known_failed=set())

def test_one_missing_of_three_without_extract_summary():
    # The old, uninformed path: one of three missing only warns.
    expected = {"a", "b", "c"}
    counts = {"a": 1, "c": 1}
    checks.evaluate_files(expected, counts, "2026-09-22")

def test_empty_staging():
    with pytest.raises(ValueError):
        checks.evaluate_staging(0, 0, 5, "2026-09-22")

def test_mismatch():
    with pytest.raises(ValueError):
        checks.evaluate_staging(4051, 15, 5, "2026-09-22")
    
def test_healthy_staging():
    checks.evaluate_staging(4051, 15, 15, "2026-09-22")

def test_evaluate_final_duplicate_keys():
    with pytest.raises(ValueError):
        checks.evaluate_final(1600, 1556, 0, "2026-09-23") 

def test_evaluate_final_ids_never_merged():
    with pytest.raises(ValueError):
        checks.evaluate_final(1556, 1556, 12, "2026-09-23")

def test_evaluate_final_healthy():
    checks.evaluate_final(1556, 1556, 0, "2026-09-23")

def test_c1_boundary():
    expected = {"a", "b", "c", "d"}
    counts = {"a": 1, "b": 1}
    checks.evaluate_files(expected, counts, "2026-09-23")