from __future__ import annotations

import pytest

from redeem_codes import validate_code
from services_v5.billing_service import BillingService
from src.blite_v6.billing.report_persistence import build_invoice_payload
from validators.billing_validator import validate_invoice_payload
from validators.customer_validator import validate_customer_payload


class DummyField:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class DummyFrame:
    _current_invoice = "INV-QA-001"
    _applied_redeem_code = "PHONE10"

    def __init__(self):
        self.phone_ent = DummyField("9999999999")
        self.name_ent = DummyField("Anu")
        self.payment_var = DummyField("Cash")
        self.app = type("App", (), {"current_user": {"username": "owner"}})()
        self.bill_items = [{"mode": "services", "name": "Hair Cut", "price": 100.0, "qty": 1}]


def test_redeem_phone_bound_code_requires_matching_billing_phone(monkeypatch):
    monkeypatch.setattr(
        "redeem_codes.get_codes",
        lambda: {
            "PHONE10": {
                "discount_type": "flat",
                "value": 10,
                "phone": "9999999999",
                "expiry": "2099-12-31",
                "used": False,
            }
        },
    )

    assert validate_code("PHONE10", customer_phone="")[0] is False
    assert validate_code("PHONE10", customer_phone="8888888888")[0] is False
    assert validate_code("PHONE10", customer_phone="9999999999")[0] is True


def test_invoice_payload_carries_redeem_discount_separately():
    payload = build_invoice_payload(
        DummyFrame(),
        final=80.0,
        disc=5.0,
        pts_disc=0.0,
        offer_disc=0.0,
        redeem_disc=15.0,
        mem_disc=0.0,
        now=lambda: "2026-04-29",
    )

    assert payload["discount_total"] == 20.0
    assert payload["redeem_discount"] == 15.0


def test_billing_service_records_redeem_discount_not_total_discount():
    calls = []

    class FakeConn:
        def execute(self, sql, params=()):
            calls.append((sql, params))

    BillingService()._record_redeem_usage(
        FakeConn(),
        {
            "redeem_code": "PHONE10",
            "invoice_no": "INV-QA-001",
            "discount_total": 100.0,
            "redeem_discount": 15.0,
            "customer_phone": "9999999999",
        },
    )

    assert calls[1][1] == ("PHONE10", "INV-QA-001", 15.0, "9999999999")


def test_customer_validator_enforces_10_digit_phone():
    with pytest.raises(ValueError, match="10-digit"):
        validate_customer_payload({"phone": "12345", "name": "Bad"})
    assert validate_customer_payload({"phone": "9999999999", "name": "Good"})["phone"] == "9999999999"


def test_invoice_validator_enforces_accounting_invariants():
    base = {
        "invoice_no": "INV-QA-001",
        "invoice_date": "2026-04-29",
        "gross_total": 100.0,
        "discount_total": 10.0,
        "tax_total": 0.0,
        "net_total": 90.0,
        "items": [{"qty": 1, "unit_price": 100.0, "line_total": 100.0}],
        "payments": [{"payment_method": "Cash", "amount": 90.0}],
    }

    assert validate_invoice_payload(base)["net_total"] == 90.0
    broken = dict(base)
    broken["payments"] = [{"payment_method": "Cash", "amount": 80.0}]
    with pytest.raises(ValueError, match="payment total"):
        validate_invoice_payload(broken)
