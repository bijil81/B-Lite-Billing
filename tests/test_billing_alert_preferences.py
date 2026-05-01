from src.blite_v6.settings.billing_alert_preferences import (
    ALERT_PREF_KEY,
    is_below_cost_alert_enabled,
)


def test_below_cost_alert_enabled_defaults_true():
    assert is_below_cost_alert_enabled({}) is True


def test_below_cost_alert_enabled_reads_saved_flag():
    assert is_below_cost_alert_enabled({ALERT_PREF_KEY: False}) is False
    assert is_below_cost_alert_enabled({ALERT_PREF_KEY: True}) is True
