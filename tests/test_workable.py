import json
from ingestion import workable, workable_loader

JOB = {"shortcode": "AAA", "title": "Engineer", "url": "https://apply.workable.com/j/AAA",
       "city": "Torrington", "state": "Connecticut", "country": "United States",
       "locations": [{"countryCode": "US"}], "telecommuting": False, "department": None,
       "employment_type": "Full-time", "education": "", "experience": "Director",
       "industry": "Manufacturing", "function": "", "published_on": "2026-09-01"}
DETAIL = {"shortcode": "AAA", "description": "<p>d</p>", "requirements": "<p>r</p>",
          "benefits": "<p>b</p>", "workplace": "hybrid", "language": "en",
          "salary_from": 200000, "salary_to": 250000, "salary_currency_iso_code": "USD",
          "salary_frequency": "year"}

# --- which jobs get a detail request (the incremental extract)

def test_shortcodes_to_detail_skips_known():
    jobs = [{"shortcode": "A"}, {"shortcode": "B"}, {"shortcode": "C"}]
    assert workable.shortcodes_to_detail(jobs, known={"B"}, budget=10) == ["A", "C"]

def test_shortcodes_to_detail_respects_budget():
    jobs = [{"shortcode": "A"}, {"shortcode": "B"}, {"shortcode": "C"}]
    assert workable.shortcodes_to_detail(jobs, known=set(), budget=2) == ["A", "B"]

def test_shortcodes_to_detail_exhausted_budget():
    # A spent (or overspent) budget means no detail requests at all - never a negative slice.
    jobs = [{"shortcode": "A"}, {"shortcode": "B"}]
    assert workable.shortcodes_to_detail(jobs, known=set(), budget=0) == []
    assert workable.shortcodes_to_detail(jobs, known=set(), budget=-1) == []

# --- the loader

def test_transform_with_detail():
    row = workable_loader.transform([JOB], DETAIL)
    assert row["id"] == "AAA"
    assert row["region"] == "Connecticut"
    assert row["country_code"] == "US"
    assert row["experience"] == "Director"
    assert row["has_detail"] is True
    assert row["content"] == "<p>d</p>"
    assert row["salary_min"] == 200000
    assert row["salary_frequency"] == "year"
    assert json.loads(row["raw_detail"]) == DETAIL

def test_transform_without_detail_marks_it():
    # No detail this run: detail columns NULL *and* has_detail False, so the MERGE keeps the
    # existing values. If has_detail were True here, last week's description would be blanked.
    row = workable_loader.transform([JOB], None)
    assert row["has_detail"] is False
    assert row["content"] is None and row["raw_detail"] is None
    assert row["title"] == "Engineer"          # list columns still filled

def test_transform_empty_strings_become_null():
    row = workable_loader.transform([JOB], None)
    assert row["education"] is None and row["job_function"] is None

def test_transform_sparse():
    row = workable_loader.transform([{"shortcode": "AAA"}], None)
    assert row["country_code"] is None and row["published_on"] is None

def test_parse_rows_matches_details_to_jobs():
    envelope = {"account": {"name": "Acme", "jobs": [JOB, dict(JOB, shortcode="BBB")]},
                "details": {"BBB": dict(DETAIL, shortcode="BBB")}}
    rows = workable_loader.parse_rows(json.dumps(envelope).encode())
    assert [(r["id"], r["has_detail"]) for r in rows] == [("AAA", False), ("BBB", True)]

def test_parse_rows_empty_board():
    assert workable_loader.parse_rows(b'{"account": {"jobs": []}, "details": {}}') == []

def test_shortcodes_to_detail_counts_a_repeated_job_once():
    # The list repeats a job once per location: one detail request per job, not per entry.
    jobs = [{"shortcode": "A"}, {"shortcode": "A"}, {"shortcode": "B"}]
    assert workable.shortcodes_to_detail(jobs, known=set(), budget=10) == ["A", "B"]

def test_parse_rows_one_row_per_job_keeping_all_entries():
    upland = dict(JOB, city="Upland")
    victorville = dict(JOB, city="Victorville")
    envelope = {"account": {"jobs": [upland, victorville]}, "details": {}}
    rows = workable_loader.parse_rows(json.dumps(envelope).encode())
    assert len(rows) == 1
    assert rows[0]["city"] == "Upland"                                  # first entry, stable
    assert [e["city"] for e in json.loads(rows[0]["raw"])] == ["Upland", "Victorville"]

class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
    def json(self): return self._body
    def raise_for_status(self):
        if self.status_code >= 400:
            raise workable.requests.exceptions.HTTPError(str(self.status_code))

def test_rate_limit_stops_detail_requests_but_not_the_run(monkeypatch):
    # A 429 on a detail must not freeze the run (it once slept 23h on Retry-After) nor lose
    # the board: details stop for the rest of the run, the list still lands.
    calls = []
    def fake_get(url, timeout):
        calls.append(url)
        if "/widget/" in url:
            return FakeResponse(200, {"jobs": [{"shortcode": "A"}, {"shortcode": "B"}, {"shortcode": "C"}]})
        return FakeResponse(429, headers={"retry-after": "84473"})
    monkeypatch.setattr(workable.session, "get", fake_get)
    fetch = workable.make_fetch(known=set(), max_details=10)
    body = json.loads(fetch("acme"))
    assert body["details"] == {} and len(body["account"]["jobs"]) == 3
    assert fetch.budget["rate_limited"] is True and fetch.budget["left"] == 0
    assert len(calls) == 2                       # one list + ONE detail, then it stopped
    fetch("other")                               # next board: list only, no detail requests
    assert len(calls) == 3
