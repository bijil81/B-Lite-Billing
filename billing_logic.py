"""Focused V5 billing persistence helpers extracted from billing.py."""
from __future__ import annotations

import os
from datetime import datetime

from src.blite_v6.billing.report_persistence import (
    SaveReportDependencies,
    mirror_invoice_to_csv,
    save_report_v5_core,
)


def now_str() -> str:
    try:
        from utils import now_str as _now_str
        return _now_str()
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def app_log(message: str) -> None:
    try:
        from utils import app_log as _app_log
        _app_log(message)
    except Exception:
        print(message)


try:
    from utils import F_REPORT as F_REPORT
except Exception:
    F_REPORT = os.path.join(os.getcwd(), "sales.csv")


def finalize_invoice_v5(payload: dict) -> dict:
    from adapters.billing_adapter import finalize_invoice_v5 as _finalize_invoice_v5
    return _finalize_invoice_v5(payload)


def use_v5_customers_db() -> bool:
    from adapters.customer_adapter import use_v5_customers_db as _use_v5_customers_db
    return _use_v5_customers_db()


def _mirror_invoice_to_csv(
    invoice_no: str,
    customer_name: str,
    customer_phone: str,
    payment_method: str,
    final: float,
    total_discount: float,
    items_str: str,
) -> None:
    mirror_invoice_to_csv(
        report_path=F_REPORT,
        invoice_no=invoice_no,
        customer_name=customer_name,
        customer_phone=customer_phone,
        payment_method=payment_method,
        final=final,
        total_discount=total_discount,
        items_str=items_str,
        now=now_str,
        app_log=app_log,
    )


def save_report_v5(
    frame,
    final: float,
    disc: float,
    pts_disc: float,
    offer_disc: float = 0.0,
    redeem_disc: float = 0.0,
    mem_disc: float = 0.0,
):
    from billing import _auto_save_customer, _billing_record_visit, _billing_redeem_points
    from redeem_codes import apply_redeem_code

    deps = SaveReportDependencies(
        finalize_invoice=finalize_invoice_v5,
        use_v5_customers_db=use_v5_customers_db,
        auto_save_customer=_auto_save_customer,
        record_visit=_billing_record_visit,
        redeem_points=_billing_redeem_points,
        apply_redeem_code=apply_redeem_code,
        auto_sync=_auto_sync,
        log_event=_log_event,
        now=now_str,
        app_log=app_log,
    )
    save_report_v5_core(
        frame,
        final=final,
        disc=disc,
        pts_disc=pts_disc,
        offer_disc=offer_disc,
        redeem_disc=redeem_disc,
        mem_disc=mem_disc,
        report_path=F_REPORT,
        deps=deps,
    )


def _auto_sync() -> None:
    try:
        from cloud_sync import auto_sync
        auto_sync()
    except Exception:
        pass


def _log_event(*args, **kwargs) -> None:
    try:
        from activity_log import log_event
        log_event(*args, **kwargs)
    except Exception:
        pass
