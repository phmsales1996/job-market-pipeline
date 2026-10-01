import xml.etree.ElementTree as ET
from ingestion import teamtailor_loader as tt

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:tt="https://teamtailor.com/locations">
  <channel>
    <title>Acme</title>
    <item>
      <title>Engineer</title>
      <description>&lt;p&gt;body&lt;/p&gt;</description>
      <pubDate>Wed, 30 Sep 2026 09:36:12 +0200</pubDate>
      <link>https://acme.example/jobs/1</link>
      <remoteStatus>hybrid</remoteStatus>
      <guid>abc-123</guid>
      <tt:locations>
        <tt:location><tt:name>Oslo HQ</tt:name><tt:city>Oslo</tt:city><tt:country>Norway</tt:country></tt:location>
        <tt:location><tt:name>SP</tt:name><tt:city>Sao Paulo</tt:city><tt:country>Brazil</tt:country></tt:location>
      </tt:locations>
      <tt:department>Engineering</tt:department>
      <tt:role/>
    </item>
    <item><guid>def-456</guid></item>
  </channel>
</rss>"""

def location(country):
    return ET.fromstring(f'<tt:location xmlns:tt="https://teamtailor.com/locations">'
                         f'<tt:country>{country}</tt:country></tt:location>')

def test_parse_rows_finds_items_under_channel():
    # Items live under <channel>: a findall("item") from the root would find none, silently.
    rows = tt.parse_rows(FEED)
    assert [r["id"] for r in rows] == ["abc-123", "def-456"]

def test_parse_rows_empty_feed():
    assert tt.parse_rows(b"<rss><channel><title>Acme</title></channel></rss>") == []

def test_transform_full_item():
    row = tt.parse_rows(FEED)[0]
    assert row["title"] == "Engineer"
    assert row["url"] == "https://acme.example/jobs/1"
    assert row["remote_status"] == "hybrid"
    assert row["department"] == "Engineering"        # a tt: tag: fails if the namespace is dropped
    assert row["content"] == "<p>body</p>"           # XML escaping undone once, HTML left as HTML
    assert row["published_at"] == "2026-09-30T09:36:12+02:00"

def test_transform_location_fields_come_from_the_chosen_location():
    # Brazil is second on purpose: name, city and country must all come from it, not mixed.
    row = tt.parse_rows(FEED)[0]
    assert (row["location"], row["city"], row["country"]) == ("SP", "Sao Paulo", "Brazil")

def test_transform_empty_tag_is_none():
    # <tt:role/> must be NULL, not "", or the fill-rate check counts it as filled.
    assert tt.parse_rows(FEED)[0]["role"] is None

def test_transform_sparse_item():
    row = tt.parse_rows(FEED)[1]
    assert row["title"] is None
    assert row["location"] is None and row["city"] is None
    assert row["published_at"] is None

def test_raw_keeps_the_tt_prefix():
    # Without register_namespace the serialiser writes ns0: - no longer what the source sent.
    raw = tt.parse_rows(FEED)[0]["raw"]
    assert "<tt:city>Oslo</tt:city>" in raw
    assert "ns0" not in raw

def test_choose_location_prefers_brazil_either_spelling():
    assert tt.choose_location([location("Norway"), location("Brasil")]).findtext(f"{tt.NS}country") == "Brasil"

def test_choose_location_falls_back_to_first():
    assert tt.choose_location([location("Norway"), location("Sweden")]).findtext(f"{tt.NS}country") == "Norway"

def test_choose_location_none():
    assert tt.choose_location([]) is None

def test_rfc822_to_iso():
    assert tt.rfc822_to_iso("Wed, 30 Sep 2026 09:36:12 +0200") == "2026-09-30T09:36:12+02:00"
    assert tt.rfc822_to_iso(None) is None
    assert tt.rfc822_to_iso("") is None
