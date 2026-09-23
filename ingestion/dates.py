import datetime

def require_date(date) -> str:
    """Return the date unchanged, or raise if it isn't a YYYY-MM-DD string.

    Pipeline entry points take the run's date from outside (Airflow's ds, or the
    command line), so a missing or malformed value must fail here rather than
    silently becoming part of a GCS path.
    """
    if not isinstance(date, str) or not date:
        raise ValueError(f"date is required as a YYYY-MM-DD string, got: {date!r}")
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
         raise ValueError(f"date must be YYYY-MM-DD, got: {date!r}") from None
    return date