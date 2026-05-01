from __future__ import annotations

from src.blite_v6.settings.gst_master import (
    build_gst_master_payload,
    gst_category_rate_rows,
    gst_master_saved_message,
    normalize_gst_category_rate_map,
)
from src.blite_v6.billing.gst_category_rules import resolve_category_gst_rate


def test_gst_master_normalization_keeps_defaults_and_overrides():
    result = normalize_gst_category_rate_map(
        {"Grocery": "12", "Fruits": "0"},
        fallback={"Body Care": 18, "Grocery": 5},
    )

    assert result["Body Care"] == 18.0
    assert result["Grocery"] == 12.0
    assert result["Fruits"] == 0.0


def test_gst_master_payload_saves_clean_category_map():
    cfg = {"gst_category_rate_map": {"Old": 7}}

    result = build_gst_master_payload(
        cfg,
        gst_category_rate_map={"Grocery": 5, "Body Care": "18"},
    )

    assert result["gst_category_rate_map"]["Old"] == 7.0
    assert result["gst_category_rate_map"]["Grocery"] == 5.0
    assert result["gst_category_rate_map"]["Body Care"] == 18.0
    assert cfg == {"gst_category_rate_map": {"Old": 7}}


def test_gst_master_rows_and_saved_message_are_human_friendly():
    rows = gst_category_rate_rows({"gst_category_rate_map": {"Grocery": 5, "Fruits": 0}})
    msg = gst_master_saved_message({"gst_category_rate_map": {"Grocery": 5, "Fruits": 0}})

    assert ("Fruits", 0.0) in rows
    assert ("Grocery", 5.0) in rows
    assert "GST master saved!" in msg
    assert "Categories:" in msg


def test_category_override_wins_over_default_master():
    assert resolve_category_gst_rate(
        "Grocery",
        category_rate_map={"Grocery": 18},
    ) == 18.0
