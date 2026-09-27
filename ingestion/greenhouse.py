import requests
import logging
from ingestion import ats

logger = logging.getLogger(__name__)

def fetch_greenhouse_raw(slug: str) -> bytes | None:
    try:    
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        response = ats.session.get(url, timeout=15)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch failed for {slug}: {e}")
        return None

def date_run(date: str) -> dict:
    return ats.run_extract("greenhouse", fetch_greenhouse_raw, date)
    
if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
    

    