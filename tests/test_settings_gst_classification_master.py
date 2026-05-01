from src.blite_v6.settings.gst_classification_master import (
    build_gst_classification_payload,
    gst_classification_saved_message,
    normalize_gst_classification_rules,
    resolve_gst_classification_rate,
)


def test_classification_rules_normalize_and_keep_user_overrides():
    rules = normalize_gst_classification_rules(
        [
            {"field": "Name", "mode": "contains", "pattern": "Sunflower", "rate": "5"},
            {"field": "HSN/SAC", "mode": "exact", "pattern": "1507", "rate": 12},
        ]
    )

    assert rules[0]["field"] == "name"
    assert rules[0]["mode"] == "contains"
    assert rules[0]["pattern"] == "Sunflower"
    assert rules[0]["rate"] == 5.0
    assert rules[1]["field"] == "hsn_sac"
    assert rules[1]["mode"] == "exact"


def test_classification_payload_merges_rules_without_mutating_source():
    cfg = {"gst_classification_rules": [{"field": "name", "mode": "contains", "pattern": "oil", "rate": 5}]}
    result = build_gst_classification_payload(
        cfg,
        gst_classification_rules=[
            {"field": "category", "mode": "exact", "pattern": "Hair Care", "rate": 18}
        ],
    )

    assert result["gst_classification_rules"][0]["field"] == "category"
    assert cfg["gst_classification_rules"][0]["field"] == "name"


def test_classification_resolver_prefers_exact_rules_over_contains():
    rate = resolve_gst_classification_rate(
        {"name": "Sunflower Oil 1L", "hsn_sac": "1507"},
        rules=[
            {"field": "name", "mode": "contains", "pattern": "Oil", "rate": 12},
            {"field": "hsn_sac", "mode": "exact", "pattern": "1507", "rate": 5},
        ],
    )

    assert rate == 5.0


def test_classification_saved_message_reads_human_friendly():
    msg = gst_classification_saved_message(
        {
            "gst_classification_rules": [
                {"field": "name", "mode": "contains", "pattern": "Oil", "rate": 12}
            ]
        }
    )

    assert "GST classification saved!" in msg
    assert "Rules: 1" in msg
