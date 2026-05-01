from __future__ import annotations

import csv
from types import SimpleNamespace

from src.blite_v6.billing.report_persistence import (
    SaveLegacyReportDependencies,
    format_items_for_legacy_csv,
    save_report_legacy_core,
)


class DummyField:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class DummyFrame:
    def __init__(self):
        self._current_invoice = "INV-LEGACY-001"
        self._saved_invoices = set()
        self.bill_items = [
            {"mode": "services", "name": "Hair Cut", "price": 300.0, "qty": 1},
            {"mode": "products", "name": "Serum", "price": 200.0, "qty": 2},
        ]
        self.name_ent = DummyField("Anu")
        self.phone_ent = DummyField("9999999999")
        self.bday_ent = DummyField("2000-01-01")
        self.payment_var = DummyField("UPI")
        self.use_pts_var = DummyField(True)
        self._applied_redeem_code = "R10"
        self.app = SimpleNamespace(current_user={"username": "owner1"})


def _deps(calls: list[str]) -> SaveLegacyReportDependencies:
    return SaveLegacyReportDependencies(
        deduct_inventory_for_sale=lambda _items: calls.append("inventory"),
        auto_save_customer=lambda *_args: calls.append("auto_customer"),
        record_visit=lambda *_args: calls.append("visit"),
        redeem_points=lambda *_args: calls.append("points"),
        apply_redeem_code=lambda *_args, **_kwargs: calls.append("redeem_code"),
        auto_sync=lambda: calls.append("sync"),
        on_bill_saved=lambda: calls.append("app_saved"),
        now=lambda: "2026-04-28 10:00:00",
    )


def test_save_report_legacy_core_writes_report_and_runs_side_effects(tmp_path):
    frame = DummyFrame()
    calls: list[str] = []
    report_path = tmp_path / "sales.csv"

    save_report_legacy_core(
        frame,
        final=650.0,
        disc=10.0,
        pts_disc=20.0,
        offer_disc=30.0,
        redeem_disc=40.0,
        mem_disc=50.0,
        report_path=str(report_path),
        deps=_deps(calls),
    )

    assert frame._saved_invoices == {"INV-LEGACY-001"}
    assert calls == ["inventory", "auto_customer", "visit", "points", "redeem_code", "sync", "app_saved"]
    rows = list(csv.reader(report_path.open(newline="", encoding="utf-8")))
    assert rows[0] == ["Date", "Invoice", "Name", "Phone", "Payment", "Total", "Discount", "Items", "Created By"]
    assert rows[1] == [
        "2026-04-28 10:00:00",
        "INV-LEGACY-001",
        "Anu",
        "9999999999",
        "UPI",
        "650.0",
        "150.0",
        "services~Hair Cut~300.0~1|products~Serum~200.0~2",
        "owner1",
    ]


def test_format_items_for_legacy_csv_keeps_product_report_metadata_when_available():
    items = [
        {"mode": "products", "name": "Banana Loose", "price": 38.0, "qty": 1.5, "unit_type": "kg", "gst_rate": 0, "cost_price": 28, "category": "Fruits"},
        {"mode": "products", "name": "Oil 1L", "price": 160.0, "qty": 1, "unit_type": "pcs", "gst_rate": 5, "cost_price": 120, "category": "Grocery"},
    ]

    assert format_items_for_legacy_csv(items) == (
        "products~Banana Loose~38.0~1.5~kg~0~28~Fruits|"
        "products~Oil 1L~160.0~1~pcs~5~120~Grocery"
    )


def test_save_report_legacy_core_passes_customer_phone_to_redeem_apply(tmp_path):
    frame = DummyFrame()
    redeem_calls: list[tuple] = []
    deps = SaveLegacyReportDependencies(
        deduct_inventory_for_sale=lambda _items: None,
        auto_save_customer=lambda *_args: None,
        record_visit=lambda *_args: None,
        redeem_points=lambda *_args: None,
        apply_redeem_code=lambda *args, **kwargs: redeem_calls.append((args, kwargs)),
        auto_sync=lambda: None,
        on_bill_saved=lambda: None,
        now=lambda: "2026-04-28 10:00:00",
    )

    save_report_legacy_core(
        frame,
        final=650.0,
        disc=0.0,
        pts_disc=0.0,
        report_path=str(tmp_path / "sales.csv"),
        deps=deps,
    )

    assert redeem_calls == [(("R10", "INV-LEGACY-001"), {"customer_phone": "9999999999"})]


def test_save_report_legacy_core_duplicate_guard_skips_everything(tmp_path):
    frame = DummyFrame()
    frame._saved_invoices.add(frame._current_invoice)
    calls: list[str] = []
    report_path = tmp_path / "sales.csv"

    save_report_legacy_core(
        frame,
        final=650.0,
        disc=0.0,
        pts_disc=0.0,
        report_path=str(report_path),
        deps=_deps(calls),
    )

    assert calls == []
    assert not report_path.exists()


def test_save_report_legacy_core_tolerates_optional_side_effect_failures(tmp_path):
    frame = DummyFrame()
    calls: list[str] = []
    deps = SaveLegacyReportDependencies(
        deduct_inventory_for_sale=lambda _items: (_ for _ in ()).throw(RuntimeError("inventory busy")),
        auto_save_customer=lambda *_args: calls.append("auto_customer"),
        record_visit=lambda *_args: calls.append("visit"),
        redeem_points=lambda *_args: calls.append("points"),
        apply_redeem_code=lambda *_args: (_ for _ in ()).throw(RuntimeError("redeem busy")),
        auto_sync=lambda: (_ for _ in ()).throw(RuntimeError("offline")),
        on_bill_saved=lambda: (_ for _ in ()).throw(RuntimeError("callback busy")),
        now=lambda: "2026-04-28 10:00:00",
    )

    save_report_legacy_core(
        frame,
        final=650.0,
        disc=0.0,
        pts_disc=20.0,
        report_path=str(tmp_path / "sales.csv"),
        deps=deps,
    )

    assert calls == ["auto_customer", "visit", "points"]
    assert frame._saved_invoices == {"INV-LEGACY-001"}
