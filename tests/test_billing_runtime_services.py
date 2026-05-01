from __future__ import annotations

from src.blite_v6.billing import runtime_services


def test_auto_save_customer_normalizes_and_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime_services, "billing_save_customer", lambda *args: calls.append(args))

    runtime_services.auto_save_customer(" 9999999999 ", " Anu ", " 2000-01-01 ")

    assert calls == [("9999999999", "Anu", "2000-01-01")]


def test_auto_save_customer_skips_guest_or_blank_identity(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime_services, "billing_save_customer", lambda *args: calls.append(args))

    runtime_services.auto_save_customer("", "Anu")
    runtime_services.auto_save_customer("9999999999", "Guest")

    assert calls == []


def test_load_services_products_delegates_to_snapshot(monkeypatch):
    monkeypatch.setattr(
        runtime_services,
        "get_billing_services_products_snapshot",
        lambda: ({"Hair": {"Cut": 100}}, {"Retail": {"Serum": 200}}),
    )

    assert runtime_services.load_services_products() == (
        {"Hair": {"Cut": 100}},
        {"Retail": {"Serum": 200}},
    )
