from src.blite_v6.billing.sale_margin_warning import build_sale_margin_warning_state


def test_sale_margin_warning_triggers_on_discounted_bill_total():
    state = build_sale_margin_warning_state(
        bill_items=[
            {
                "mode": "products",
                "name": "Sunflower Oil 1L",
                "price": 145.0,
                "qty": 1,
                "cost_price": 120.0,
            }
        ],
        gross_before_discount=145.0,
        discount_total=100.0,
    )

    assert state.should_warn is True
    assert "below cost" in state.message.lower()
    assert state.effective_bill_total == 45.0


def test_sale_margin_warning_stays_quiet_when_margin_remains():
    state = build_sale_margin_warning_state(
        bill_items=[
            {
                "mode": "products",
                "name": "Sunflower Oil 1L",
                "price": 160.0,
                "qty": 1,
                "cost_price": 120.0,
            }
        ],
        gross_before_discount=160.0,
        discount_total=20.0,
    )

    assert state.should_warn is False
