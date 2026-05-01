from src.blite_v6.billing.sale_margin_alerts import build_sale_margin_alert_text
from src.blite_v6.billing.sale_margin_warning import SaleMarginWarningState


def test_sale_margin_alert_text_summarizes_offenders():
    state = SaleMarginWarningState(
        should_warn=True,
        offending_items=(
            {"name": "Sunflower Oil 1L", "sale": 42.86, "cost": 120.00},
            {"name": "Sugar 1kg", "sale": 38.00, "cost": 46.00},
            {"name": "Banana", "sale": 10.00, "cost": 12.00},
        ),
    )

    text = build_sale_margin_alert_text(state)

    assert text.startswith("Below cost")
    assert "Sunflower Oil 1L" in text
    assert "Sugar 1kg" in text
    assert "+ 1 more item(s)" in text


def test_sale_margin_alert_text_stays_empty_when_no_warning():
    state = SaleMarginWarningState(should_warn=False)

    assert build_sale_margin_alert_text(state) == ""
