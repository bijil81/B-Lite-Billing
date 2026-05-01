from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import billing_logic


class DummyField:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class DummyVar(DummyField):
    pass


class DummyFrame:
    def __init__(self):
        self._current_invoice = "INV-TEST-001"
        self._saved_invoices = set()
        self._bill_completed = False
        self.bill_items = [
            {"mode": "services", "name": "Hair Cut", "price": 300.0, "qty": 1, "staff": "Asha"},
        ]
        self.name_ent = DummyField("Anu")
        self.phone_ent = DummyField("9999999999")
        self.bday_ent = DummyField("")
        self.payment_var = DummyVar("Cash")
        self.use_pts_var = DummyVar(True)
        self._applied_redeem_code = ""
        self.app = SimpleNamespace(current_user={"username": "owner1"}, on_bill_saved=lambda: None)


def _install_fake_modules(monkeypatch, auto_save, record_visit, redeem_points, apply_redeem):
    fake_billing = ModuleType("billing")
    fake_billing._auto_save_customer = auto_save
    fake_billing._billing_record_visit = record_visit
    fake_billing._billing_redeem_points = redeem_points
    monkeypatch.setitem(sys.modules, "billing", fake_billing)

    fake_redeem = ModuleType("redeem_codes")
    fake_redeem.apply_redeem_code = apply_redeem
    monkeypatch.setitem(sys.modules, "redeem_codes", fake_redeem)


def test_save_report_v5_skips_legacy_loyalty_hooks_when_v5_customers_enabled(tmp_path, monkeypatch):
    frame = DummyFrame()
    calls = {"auto": 0, "visit": 0, "redeem": 0, "finalize": 0}

    _install_fake_modules(
        monkeypatch,
        auto_save=lambda *_args, **_kwargs: calls.__setitem__("auto", calls["auto"] + 1),
        record_visit=lambda *_args, **_kwargs: calls.__setitem__("visit", calls["visit"] + 1),
        redeem_points=lambda *_args, **_kwargs: calls.__setitem__("redeem", calls["redeem"] + 1),
        apply_redeem=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(billing_logic, "F_REPORT", str(tmp_path / "sales.csv"))
    monkeypatch.setattr(
        billing_logic,
        "finalize_invoice_v5",
        lambda payload: calls.__setitem__("finalize", calls["finalize"] + 1) or {"ok": True, "invoice_no": payload["invoice_no"]},
    )
    monkeypatch.setattr(billing_logic, "use_v5_customers_db", lambda: True)

    billing_logic.save_report_v5(frame, final=300.0, disc=0.0, pts_disc=50.0)

    assert calls == {"auto": 1, "visit": 0, "redeem": 0, "finalize": 1}
    assert frame._current_invoice in frame._saved_invoices
    assert frame._bill_completed is True


def test_save_report_v5_preserves_legacy_customer_hooks_when_v5_customers_disabled(tmp_path, monkeypatch):
    frame = DummyFrame()
    calls = {"auto": 0, "visit": 0, "redeem": 0, "finalize": 0}

    _install_fake_modules(
        monkeypatch,
        auto_save=lambda *_args, **_kwargs: calls.__setitem__("auto", calls["auto"] + 1),
        record_visit=lambda *_args, **_kwargs: calls.__setitem__("visit", calls["visit"] + 1),
        redeem_points=lambda *_args, **_kwargs: calls.__setitem__("redeem", calls["redeem"] + 1),
        apply_redeem=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(billing_logic, "F_REPORT", str(tmp_path / "sales.csv"))
    monkeypatch.setattr(
        billing_logic,
        "finalize_invoice_v5",
        lambda payload: calls.__setitem__("finalize", calls["finalize"] + 1) or {"ok": True, "invoice_no": payload["invoice_no"]},
    )
    monkeypatch.setattr(billing_logic, "use_v5_customers_db", lambda: False)

    billing_logic.save_report_v5(frame, final=300.0, disc=0.0, pts_disc=50.0)

    assert calls == {"auto": 1, "visit": 1, "redeem": 1, "finalize": 1}
    assert frame._current_invoice in frame._saved_invoices
    assert frame._bill_completed is True


def test_save_report_v5_tolerates_csv_mirror_failure(tmp_path, monkeypatch):
    frame = DummyFrame()
    logs: list[str] = []

    _install_fake_modules(
        monkeypatch,
        auto_save=lambda *_args, **_kwargs: None,
        record_visit=lambda *_args, **_kwargs: None,
        redeem_points=lambda *_args, **_kwargs: None,
        apply_redeem=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(billing_logic, "F_REPORT", str(tmp_path / "sales.csv"))
    monkeypatch.setattr(billing_logic, "finalize_invoice_v5", lambda payload: {"ok": True, "invoice_no": payload["invoice_no"]})
    monkeypatch.setattr(billing_logic, "use_v5_customers_db", lambda: True)
    monkeypatch.setattr(billing_logic, "app_log", logs.append)

    def fail_open(*_args, **_kwargs):
        raise OSError("disk busy")

    monkeypatch.setattr("builtins.open", fail_open)

    billing_logic.save_report_v5(frame, final=300.0, disc=0.0, pts_disc=0.0)

    assert frame._current_invoice in frame._saved_invoices
    assert frame._bill_completed is True
    assert any("billing v5 csv mirror" in entry for entry in logs)
