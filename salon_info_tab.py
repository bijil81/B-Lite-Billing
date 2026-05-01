def render_shop_info_tab(settings_frame):
    from salon_settings import get_settings

    cfg = get_settings()
    body = settings_frame._scroll("info")
    settings_frame._ents = {}
    for label, key, value in [
        ("Shop Name", "salon_name", cfg["salon_name"]),
        ("Address", "address", cfg["address"]),
        ("Phone Number", "phone", cfg.get("phone", "")),
        ("GST Number", "gst_no", cfg.get("gst_no", "")),
        ("Currency", "currency", cfg.get("currency", "\u20b9")),
    ]:
        settings_frame._lbl(body, label)
        settings_frame._ents[key] = settings_frame._ent(body, value)
    settings_frame._savebtn(body, "\U0001f4be  Save Shop Info", settings_frame._save_info)

