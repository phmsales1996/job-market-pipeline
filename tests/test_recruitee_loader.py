from ingestion import recruitee_loader

def test_choose_language_prefers_english():
    assert recruitee_loader.choose_language({"it": {}, "en": {}}) == "en"

def test_choose_language_portuguese_second():
    assert recruitee_loader.choose_language({"pt": {}, "de": {}}) == "pt"

def test_choose_language_fallback_is_stable():
    # No preferred language: the first code alphabetically, whatever order the JSON had.
    assert recruitee_loader.choose_language({"tr": {}, "de": {}}) == "de"

def test_choose_language_none():
    assert recruitee_loader.choose_language({}) is None
    assert recruitee_loader.choose_language(None) is None

def test_transform_reads_the_chosen_translation():
    # Top-level and translation disagree on purpose: the row must come from translations.en.
    job = {"id": 1, "title": "Top level", "careers_url": "https://x", "country_code": "US",
           "remote": True, "hybrid": False, "on_site": False,
           "employment_type_code": "freelance", "published_at": "2026-09-25 10:47:06 UTC",
           "salary": {"min": 50000, "max": 60000, "currency": "EUR", "period": "year"},
           "translations": {"it": {"title": "Italiano"},
                            "en": {"title": "English", "description": "<p>d</p>",
                                   "requirements": "<p>r</p>", "highlight": "h"}}}
    row = recruitee_loader.transform(job)
    assert row["title"] == "English"
    assert row["language"] == "en"
    assert row["content"] == "<p>d</p>"
    assert row["requirements"] == "<p>r</p>"
    assert row["highlight"] == "h"
    assert row["url"] == "https://x"
    assert row["employment_type"] == "freelance"
    assert row["salary_period"] == "year"
    assert row["hybrid"] is False

def test_transform_without_translations_uses_top_level():
    row = recruitee_loader.transform({"id": 1, "title": "Only version", "description": "d"})
    assert row["language"] is None
    assert row["title"] == "Only version"
    assert row["content"] == "d"

def test_transform_sparse_and_nulls():
    # Only an id, and a present-but-null salary: nothing may crash.
    row = recruitee_loader.transform({"id": 1, "salary": None, "translations": None})
    assert row["salary_min"] is None
    assert row["title"] is None

def test_parse_rows_wrapped():
    assert [r["id"] for r in recruitee_loader.parse_rows(b'{"offers": [{"id": 1}, {"id": 2}]}')] == [1, 2]
    assert recruitee_loader.parse_rows(b'{"offers": []}') == []
