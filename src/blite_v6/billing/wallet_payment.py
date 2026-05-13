from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class WalletPreview:
    available: float
    used: float
    balance_after: float
    payable: float
    label: str


def safe_amount(value: Any) -> float:
    try:
        return max(0.0, float(value or 0.0))
    except Exception:
        return 0.0


def wallet_available_from_membership(membership: Mapping[str, Any] | None) -> float:
    if not membership:
        return 0.0
    status = str(membership.get("status", "")).strip().lower()
    if status not in {"active", "1", "true", "yes"}:
        return 0.0
    return safe_amount(membership.get("wallet_balance", 0.0))


def build_wallet_preview(
    *,
    enabled: bool,
    available: float,
    payable_before_wallet: float,
    requested_amount: Any = None,
) -> WalletPreview:
    available = safe_amount(available)
    payable_before_wallet = safe_amount(payable_before_wallet)
    if enabled:
        requested = safe_amount(requested_amount)
        spend_limit = requested if requested > 0 else available
        used = round(min(available, payable_before_wallet, spend_limit), 2)
    else:
        used = 0.0
    payable = round(max(0.0, payable_before_wallet - used), 2)
    balance_after = round(max(0.0, available - used), 2)

    if available <= 0:
        label = ""
    elif used > 0:
        label = f"Wallet Applied: Rs{used:.0f} | Bal Rs{balance_after:.0f}"
    else:
        label = f"Wallet Avl: Rs{available:.0f}"

    return WalletPreview(
        available=available,
        used=used,
        balance_after=balance_after,
        payable=payable,
        label=label,
    )


def build_payment_split(*, payment_method: str, payable_after_wallet: float, wallet_used: float) -> list[dict[str, Any]]:
    payments: list[dict[str, Any]] = []
    wallet_used = round(safe_amount(wallet_used), 2)
    payable_after_wallet = round(safe_amount(payable_after_wallet), 2)
    if wallet_used > 0:
        payments.append(
            {
                "payment_method": "Wallet",
                "amount": wallet_used,
                "reference_no": "",
            }
        )
    if payable_after_wallet > 0:
        payments.append(
            {
                "payment_method": payment_method or "Cash",
                "amount": payable_after_wallet,
                "reference_no": "",
            }
        )
    if not payments:
        payments.append({"payment_method": payment_method or "Cash", "amount": 0.0, "reference_no": ""})
    return payments
