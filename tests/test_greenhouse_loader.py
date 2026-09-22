from ingestion import greenhouse_loader

def test_empty_list_returns_none():
    assert greenhouse_loader.first_field([], "name") is None

def test_returns_first_items_value():
    test = [{"name": "Alice"}, {"name": "Beth"}]
    assert greenhouse_loader.first_field(test, "name") == "Alice"