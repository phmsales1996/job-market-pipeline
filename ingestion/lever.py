import requests
import logging
from ingestion import ats

logger = logging.getLogger(__name__)

def fetch_lever_raw(slug: str) -> bytes | None:
    try:    
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        response = ats.session.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch failed for {slug}: {e}")
        return None

def date_run(date: str) -> dict:
    return ats.run_extract("lever", fetch_lever_raw, date)
    
if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
    

    