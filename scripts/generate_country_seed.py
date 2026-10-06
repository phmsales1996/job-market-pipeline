"""Generate the dbt seed dbt/seeds/country_codes.csv from the data itself.

Collects every distinct country value the sources actually send (names like 'United States',
'USA', 'Norway'; codes like 'US'), matches each against the ISO 3166 list, and writes one row
per observed value: country_raw -> country_code (ISO alpha-2).

The ISO list (datasets/country-codes, public domain) gives several names per country - the
everyday name, the UN short name, the official name - plus the alpha-2 and alpha-3 codes, so most
spellings match automatically. Values that still don't match go in ALIASES below: those are the
only judgement calls, and they are reviewed here, in one place. Anything unmatched is printed and
left out of the seed, so the staging models' "raw present, mapped missing" tests flag it.

    python scripts/generate_country_seed.py            # writes the seed, prints unmatched values
"""

import csv
import io
import pathlib
import sys
import urllib.request

from google.cloud import bigquery

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ingestion.ats import dataset  # noqa: E402

ISO_URL = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
SEED_PATH = pathlib.Path(__file__).parent.parent / "dbt" / "seeds" / "country_codes.csv"

# Every column that holds a country value, per raw table.
COUNTRY_COLUMNS = [
    ("lever_postings", "country"),
    ("ashby_postings", "country"),
    ("recruitee_postings", "country_code"),
    ("teamtailor_postings", "country"),
    ("workable_postings", "country"),
    ("workable_postings", "country_code"),
]

# Observed spellings the ISO names don't cover. Keys are compared case-insensitively.
ALIASES = {
    "brasil": "BR",
    "svalbard and jan mayen":"SJ",
    "uk": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "south korea": "KR",
    "korea": "KR",
    "russia": "RU",
    "turkey": "TR",
    "czech republic": "CZ",
    "vietnam": "VN",
    "taiwan": "TW",
    "hong kong": "HK",
    "macau": "MO",
    "iran": "IR",
    "syria": "SY",
    "laos": "LA",
    "moldova": "MD",
    "bolivia": "BO",
    "venezuela": "VE",
    "tanzania": "TZ",
    "ivory coast": "CI",
    "cote d'ivoire": "CI",
    "côte d'ivoire": "CI",
    "the netherlands": "NL",
    "holland": "NL",
    "kosovo": "XK",   # not in ISO 3166-1; XK is the widely used user-assigned code
    "xk": "XK",
    "united states": "US",
    "u.s.": "US",
    "u.s.a": "US",
    "united kingdom": "GB",
    "méxico": "MX",
    "turkiye": "TR",
    "hong kong sar": "HK",
    "hong kong sar, china": "HK",
    "people's republic of china": "CN",
    "reunion": "RE",
    "france, metropolitan": "FR",
    "bolivia, plurinational state of": "BO",
    "congo, the democratic republic of the": "CD",
    "tanzania, united republic of": "TZ",
    "venezuela, bolivarian republic of": "VE",
}

# Values that are not a country - regions and "remote" labels. They go INTO the seed with an
# empty code: the seed knows them and deliberately maps them to no country. That keeps the
# "value the seed has never seen" test meaningful (it would otherwise flag these forever).
NOT_A_COUNTRY = {
    "anywhere", "europe", "europa", "european union", "latam", "latin america",
    "north america", "eu, latam, canada", "remote", "remote - emea", "remote - global",
    "remote - south america",
}


def observed_values() -> set[str]:
    client = bigquery.Client()
    selects = " UNION DISTINCT ".join(
        f"SELECT TRIM({col}) AS v FROM `{dataset}.{table}` WHERE {col} IS NOT NULL"
        for table, col in COUNTRY_COLUMNS
    )
    return {row.v for row in client.query(selects).result() if row.v}


def iso_lookup() -> dict[str, str]:
    """lower-cased name or code -> alpha-2, from every name column of the ISO list."""
    text = urllib.request.urlopen(ISO_URL, timeout=30).read().decode("utf-8")
    lookup: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(text)):
        code = row["ISO3166-1-Alpha-2"]
        if not code:
            continue
        for column in ("ISO3166-1-Alpha-2", "ISO3166-1-Alpha-3", "CLDR display name",
                       "UNTERM English Short", "official_name_en"):
            value = (row.get(column) or "").strip()
            if value:
                lookup.setdefault(value.lower(), code)
    return lookup


def main() -> None:
    lookup = iso_lookup()
    lookup.update({k.lower(): v for k, v in ALIASES.items()})
    rows, unmatched = [], []
    for value in sorted(observed_values()):
        code = lookup.get(value.lower())
        if code:
            rows.append((value, code))
        elif value.lower() in NOT_A_COUNTRY:
            rows.append((value, ""))       # known, and deliberately no country
        else:
            unmatched.append(value)
    with SEED_PATH.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["country_raw", "country_code"])
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {SEED_PATH}")
    print(f"unmatched ({len(unmatched)}): {unmatched}")


if __name__ == "__main__":
    main()
