from ingestion import loader

def test_slug_from_path_takes_the_third_piece():
    assert loader.slug_from_path('lever/ingest_date=2026-10-06/acme/063512.json') == 'acme'
