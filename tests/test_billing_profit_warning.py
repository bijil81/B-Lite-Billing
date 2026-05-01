from src.blite_v6.billing.profit_warning import build_below_cost_warning_state


def test_below_cost_warning_triggers_without_discount():
    state = build_below_cost_warning_state(
        bill_items=[],
        item_name="Sunflower Oil 1L",
        sale_price=145,
        qty=1,
        cost_price=160,
        discount_enabled=False,
        discount_value=0,
    )

    assert state.should_warn is True
    assert "below cost" in state.message.lower()
    assert state.sale_total == 145.0
    assert state.cost_total == 160.0


def test_below_cost_warning_considers_current_bill_discount():
    state = build_below_cost_warning_state(
        bill_items=[
            {"mode": "products", "name": "Body Mist", "price": 499, "qty": 1},
            {"mode": "products", "name": "Banana", "price": 38, "qty": 1},
        ],
        item_name="Sugar 1kg",
        sale_price=48,
        qty=1,
        cost_price=46,
        discount_enabled=True,
        discount_value=100,
    )

    assert state.should_warn is True
    assert state.discount_amount == 100.0
    assert state.effective_unit_price < state.cost_unit_price


def test_below_cost_warning_stays_quiet_when_margin_remains():
    state = build_below_cost_warning_state(
        bill_items=[{"mode": "products", "name": "Rice", "price": 100, "qty": 1}],
        item_name="Rice Pack",
        sale_price=120,
        qty=1,
        cost_price=90,
        discount_enabled=True,
        discount_value=10,
    )

    assert state.should_warn is False
