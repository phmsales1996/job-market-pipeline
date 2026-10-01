import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from ingestion import loader

logger = logging.getLogger(__name__)

# Teamtailor's own tags (tt:locations, tt:department, ...) live in this XML namespace. The
# parser stores them under the full URI, so "tt:city" finds nothing: it has to be f"{NS}city".
NS = "{https://teamtailor.com/locations}"
# Without this, serialising an item back to text renames the prefix to "ns0:" - not what was sent.
ET.register_namespace("tt", "https://teamtailor.com/locations")

# Product preference: a Brazilian location if the posting lists one. Both spellings occur.
BRAZIL = {"Brazil", "Brasil"}

def text(element: ET.Element | None, path: str) -> str | None:
    """findtext, but an empty tag (<tt:department/>) becomes None, not "" - otherwise fill rates
    count an empty string as filled. A missing element (no location at all) is None too."""
    if element is None:
        return None
    return element.findtext(path) or None

def choose_location(locations: list[ET.Element]) -> ET.Element | None:
    """The one location to store: a Brazilian one if there is any, else the first, else None."""
    if not locations:
        return None
    for location in locations:
        if location.findtext(f"{NS}country") in BRAZIL:
            return location
    return locations[0]

def rfc822_to_iso(value: str | None) -> str | None:
    """'Wed, 30 Sep 2026 09:36:12 +0200' -> '2026-09-30T09:36:12+02:00'. BigQuery cannot read
    RFC-822; None stays None so one undated posting cannot take the load down."""
    if not value:
        return None
    return parsedate_to_datetime(value).isoformat()

def transform(item: ET.Element) -> dict:
    location = choose_location(item.findall(f"{NS}locations/{NS}location"))
    transformed_job = {}
    transformed_job["id"] = item.findtext("guid")
    transformed_job["title"] = text(item, "title")
    transformed_job["url"] = text(item, "link")
    transformed_job["location"] = text(location, f"{NS}name")
    transformed_job["city"] = text(location, f"{NS}city")
    transformed_job["country"] = text(location, f"{NS}country")
    transformed_job["remote_status"] = text(item, "remoteStatus")
    transformed_job["department"] = text(item, f"{NS}department")
    transformed_job["role"] = text(item, f"{NS}role")
    transformed_job["content"] = text(item, "description")
    transformed_job["published_at"] = rfc822_to_iso(text(item, "pubDate"))
    transformed_job["raw"] = ET.tostring(item, encoding="unicode")

    return transformed_job

def parse_rows(content: bytes) -> list[dict]:
    """Teamtailor: an RSS feed, one <item> per posting under <channel>."""
    root = ET.fromstring(content)
    return [transform(item) for item in root.findall("channel/item")]

def date_run(date: str) -> dict:
    return loader.run_load("teamtailor", parse_rows, date)


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
