from src.blite_v6.text_normalization import smart_title_name


def test_smart_title_name_capitalizes_display_names_without_corrupting_units():
    assert smart_title_name("  body   care ") == "Body Care"
    assert smart_title_name("body lotion 200ml pcs") == "Body Lotion 200ml pcs"
    assert smart_title_name("aloe vera wax 1kg pcs") == "Aloe Vera Wax 1kg pcs"
    assert smart_title_name("HSN service / GST item") == "HSN Service / GST Item"
    assert smart_title_name("") == ""
