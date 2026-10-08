"""Generate the dbt seed dbt/seeds/country_codes.csv from the data itself.

Collects every distinct country value the sources actually send (names like 'United States',
'USA', 'Norway'; codes like 'US'), matches each against the ISO 3166 list, and writes one row
per observed value: country_raw -> country_code (ISO alpha-2).

The ISO list (datasets/country-codes, public domain) gives several names per country - the
everyday name, the UN short name, the official name - plus the alpha-2 and alpha-3 codes, so most
spellings match automatically. Values that still don't match go in ALIASES below: those are the
only judgement calls, and they are reviewed here, in one place. Anything unmatched is printed and
left out of the seed, so the staging models' "raw present, mapped missing" tests flag it.

    python scripts/generate_country_seed.py            # writes both seeds, prints unmatched values

It also writes dbt/seeds/countries.csv: one row per ISO country (code, name, the UN region and
sub-region, and our business region), the source of the country dimension.
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
COUNTRIES_PATH = pathlib.Path(__file__).parent.parent / "dbt" / "seeds" / "countries.csv"

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
    "remote - south america", "us | eu",
}


# The business region of each UN sub-region. The UN groupings come with the ISO list and are
# kept as they are (region, sub_region); this is our own reading on top of them, in one place.
# Judgement calls: Western Asia (the Middle East) is the "ME" of EMEA; Mexico follows the UN
# into Latin America, although some companies count it in North America.
BUSINESS_REGIONS = {
    "Northern America": "NAMER",
    "Latin America and the Caribbean": "LATAM",
    "Northern Europe": "EMEA", "Western Europe": "EMEA", "Southern Europe": "EMEA",
    "Eastern Europe": "EMEA", "Northern Africa": "EMEA", "Sub-Saharan Africa": "EMEA",
    "Western Asia": "EMEA",
    "Eastern Asia": "APAC", "South-eastern Asia": "APAC", "Southern Asia": "APAC",
    "Central Asia": "APAC", "Australia and New Zealand": "APAC", "Melanesia": "APAC",
    "Micronesia": "APAC", "Polynesia": "APAC",
}

# The ISO list's everyday name is an abbreviation for these two; a dashboard wants the name.
NAME_OVERRIDES = {"US": "United States", "GB": "United Kingdom"}

# Countries the UN columns leave empty in this list, placed by hand: (region, sub_region).
REGION_OVERRIDES = {"TW": ("Asia", "Eastern Asia")}

# Codes the sources use that are not in the ISO list: code -> (name, region, sub_region).
# 'XK' is the widely used, user-assigned code for Kosovo (see ALIASES).
EXTRA_COUNTRIES = {"XK": ("Kosovo", "Europe", "Southern Europe")}


def observed_values() -> set[str]:
    client = bigquery.Client()
    selects = " UNION DISTINCT ".join(
        f"SELECT TRIM({col}) AS v FROM `{dataset}.{table}` WHERE {col} IS NOT NULL"
        for table, col in COUNTRY_COLUMNS
    )
    return {row.v for row in client.query(selects).result() if row.v}


def iso_rows() -> list[dict[str, str]]:
    """The ISO list, one dict per country that has an alpha-2 code. Downloaded once per run."""
    text = urllib.request.urlopen(ISO_URL, timeout=30).read().decode("utf-8")
    return [row for row in csv.DictReader(io.StringIO(text)) if row["ISO3166-1-Alpha-2"]]


def country_rows(iso: list[dict[str, str]]) -> list[tuple[str, str, str, str, str]]:
    """One row per country for the countries seed: code, name, region, sub_region, business_region.

    A different question from country_codes.csv: that one maps every SPELLING a source sends to
    a code (many rows per country); this one describes each COUNTRY once, for the dimension.
    """
    rows = []
    for row in iso:
        code = row["ISO3166-1-Alpha-2"]
        name = NAME_OVERRIDES.get(code) or row["CLDR display name"].strip()
        region, sub_region = REGION_OVERRIDES.get(
            code, (row["Region Name"].strip(), row["Sub-region Name"].strip()))
        rows.append((code, name, region, sub_region, BUSINESS_REGIONS.get(sub_region, "")))
    for code, (name, region, sub_region) in EXTRA_COUNTRIES.items():
        rows.append((code, name, region, sub_region, BUSINESS_REGIONS.get(sub_region, "")))
    return sorted(rows)


def iso_lookup(iso: list[dict[str, str]]) -> dict[str, str]:
    """lower-cased name or code -> alpha-2, from every name column of the ISO list."""
    lookup: dict[str, str] = {}
    for row in iso:
        code = row["ISO3166-1-Alpha-2"]
        for column in ("ISO3166-1-Alpha-2", "ISO3166-1-Alpha-3", "CLDR display name",
                       "UNTERM English Short", "official_name_en"):
            value = (row.get(column) or "").strip()
            if value:
                lookup.setdefault(value.lower(), code)
    return lookup


def main() -> None:
    iso = iso_rows()
    lookup = iso_lookup(iso)
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

    countries = country_rows(iso)
    with COUNTRIES_PATH.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["country_code", "country_name", "region", "sub_region", "business_region"])
        writer.writerows(countries)
    no_region = [code for code, _, _, _, business in countries if not business]
    print(f"wrote {len(countries)} rows to {COUNTRIES_PATH}")
    print(f"no business region ({len(no_region)}): {no_region}")


if __name__ == "__main__":
    main()
