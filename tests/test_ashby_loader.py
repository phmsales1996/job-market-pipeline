from ingestion import ashby_loader

SALARY = {"compensationType": "Salary", "interval": "1 YEAR", "currencyCode": "USD",
          "minValue": 180000, "maxValue": 290000}
EQUITY = {"compensationType": "EquityPercentage", "interval": "NONE", "currencyCode": None,
          "minValue": 0.1, "maxValue": 0.5}

def test_transform_rename():
    job = {"id": "abc", "title": "Engineer", "jobUrl": "https://x", "location": "Remote",
           "department": "Engineering", "team": "Platform", "employmentType": "FullTime",
           "workplaceType": "Remote", "descriptionPlain": "body", "isListed": True,
           "publishedAt": "2026-09-01T10:00:00.000+00:00",
           "address": {"postalAddress": {"addressCountry": "USA"}},
           "compensation": {"compensationTierSummary": "$180K – $290K",
                            "summaryComponents": [SALARY]}}
    row = ashby_loader.transform(job)
    assert row["title"] == "Engineer"
    assert row["url"] == "https://x"
    assert row["department"] == "Engineering"
    assert row["team"] == "Platform"
    assert row["employment_type"] == "FullTime"
    assert row["country"] == "USA"
    assert row["content"] == "body"
    assert row["is_listed"] is True
    assert row["salary_min"] == 180000
    assert row["salary_interval"] == "1 YEAR"
    assert row["compensation_summary"] == "$180K – $290K"
    assert row["published_at"] == "2026-09-01T10:00:00.000+00:00"

def test_transform_sparse():
    # A posting with nothing but an id must not crash: every (… or {}) guard is exercised.
    row = ashby_loader.transform({"id": "abc"})
    assert row["country"] is None
    assert row["salary_min"] is None
    assert row["compensation_summary"] is None

def test_transform_nulls():
    # Present-but-null is not the same as missing: .get(k, {}) would crash here, (… or {}) does not.
    row = ashby_loader.transform({"id": "abc", "address": None, "compensation": None})
    assert row["country"] is None
    assert row["salary_min"] is None

def test_salary_component_one():
    assert ashby_loader.salary_component({"compensation": {"summaryComponents": [SALARY]}}) == SALARY

def test_salary_component_ignores_equity():
    # Equity comes first on purpose: a [0] shortcut would store 0.1 as a salary.
    job = {"compensation": {"summaryComponents": [EQUITY, SALARY]}}
    assert ashby_loader.salary_component(job) == SALARY

def test_salary_component_ambiguous():
    # Two Salary entries: we cannot know which one is meant, so none is taken.
    job = {"compensation": {"summaryComponents": [SALARY, dict(SALARY, minValue=1)]}}
    assert ashby_loader.salary_component(job) == {}

def test_parse_rows_wrapped():
    # Ashby wraps postings under "jobs"; a board with no open roles is a normal night.
    assert [r["id"] for r in ashby_loader.parse_rows(b'{"jobs": [{"id": "a"}, {"id": "b"}]}')] == ["a", "b"]
    assert ashby_loader.parse_rows(b'{"jobs": []}') == []
