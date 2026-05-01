"""Legacy offers and redeem codes -> v5 migration."""

from __future__ import annotations

from offers import get_offers
from redeem_codes import get_codes
from repositories.offers_repo import OffersRepository


def migrate_offers(dry_run: bool = True) -> dict:
    repo = OffersRepository()
    offers = get_offers()
    codes = get_codes()
    offer_names = []
    code_names = []
    for offer in offers:
        offer_names.append(offer.get("name", ""))
        if not dry_run:
            repo.upsert_offer({
                "legacy_name": offer.get("name", ""),
                "offer_type": offer.get("type", "percentage"),
                "value": offer.get("value", 0.0),
                "service_name": offer.get("service_name", ""),
                "coupon_code": offer.get("coupon_code", ""),
                "min_bill": offer.get("min_bill", 0.0),
                "valid_from": offer.get("valid_from", ""),
                "valid_to": offer.get("valid_to", ""),
                "active": offer.get("active", True),
                "notes": offer.get("notes", ""),
            })
    for code, info in codes.items():
        code_names.append(code)
        if not dry_run:
            repo.upsert_redeem_code({
                "code": code,
                "customer_phone": info.get("phone", ""),
                "customer_name": info.get("name", ""),
                "discount_type": info.get("discount_type", "flat"),
                "discount_value": info.get("value", 0.0),
                "min_bill": info.get("min_bill", 0.0),
                "active": not bool(info.get("expired", False)),
                "used": bool(info.get("used", False)),
                "used_invoice": info.get("used_invoice", ""),
                "valid_until": info.get("expiry", info.get("valid_until", "")),
            })
    return {
        "offer_count": len(offer_names),
        "code_count": len(code_names),
        "offers": offer_names,
        "codes": code_names,
        "dry_run": dry_run,
    }
