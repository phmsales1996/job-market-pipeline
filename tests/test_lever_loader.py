from ingestion import lever_loader

def test_epoch_ms_to_iso_value():
    assert lever_loader.epoch_ms_to_iso(1600000000000) == '2020-09-13T12:26:40+00:00'

def test_epoch_ms_to_iso_none():
    assert lever_loader.epoch_ms_to_iso(None) is None

def test_epoch_ms_to_iso_zero():
    # 0 is falsy but is a real timestamp: this fails if the guard becomes `if not ms`.
    assert lever_loader.epoch_ms_to_iso(0) == '1970-01-01T00:00:00+00:00'

def test_transform_rename():
    job = {"id": "abc", "text": "Engineer", "hostedUrl": "https://x",
           "description": "<p>body</p>", "createdAt": 1600000000000}
    row = lever_loader.transform(job)
    assert row["title"] == "Engineer"
    assert row["url"] == "https://x"
    assert row["content"] == "<p>body</p>"
    assert row["published_at"] == '2020-09-13T12:26:40+00:00'

def test_transform_sparse():
    # A posting with nothing but an id must not crash: every guard in transform is here.
    job = {"id": "abc"}
    row = lever_loader.transform(job)
    assert row["location"] is None
    assert row["department"] is None
    assert row["salary_min"] is None
    assert row["published_at"] is None

def test_parse_rows_bare_array():
    # Lever's payload is a bare array; this fails if anyone reaches for data["jobs"].
    content = b'[{"id": "a"}, {"id": "b"}]'
    rows = lever_loader.parse_rows(content)
    assert len(rows) == 2
    assert [row["id"] for row in rows] == ["a", "b"]
