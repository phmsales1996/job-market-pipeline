import requests
import logging
from ingestion import ats

logger = logging.getLogger(__name__)
PER_PAGE = 10000

def fetch_teamtailor_raw(slug: str) -> bytes | None:
    try:    
        url = f"https://{slug}.teamtailor.com/jobs.rss?per_page={PER_PAGE}"
        response = ats.session.get(url, timeout=10)
        response.raise_for_status()
        counting = response.content.count(b"<item>")
        if counting == PER_PAGE:
            logger.error(f"Returned exactly the number of jobs as Per Page:{PER_PAGE}, for company {slug}. Probably a new limit on per_page; the board would be truncated.")
            return None
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch failed for {slug}: {e}")
        return None

def date_run(date: str) -> dict:
    return ats.run_extract("teamtailor", fetch_teamtailor_raw, date, file_format="xml")
    
if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
    

    