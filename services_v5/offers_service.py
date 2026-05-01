"""Workflow layer for offers and coupons."""

from __future__ import annotations

from repositories.offers_repo import OffersRepository


class OffersService:
    def __init__(self, repo: OffersRepository | None = None):
        self.repo = repo or OffersRepository()

    def get_all(self) -> list[dict]:
        return [self._to_legacy_offer(row) for row in self.repo.list_offers()]

    def get_active(self, today_iso: str) -> list[dict]:
        result = []
        for offer in self.get_all():
            if not bool(offer.get("active", True)):
                continue
            start = offer.get("valid_from", "2000-01-01")
            end = offer.get("valid_to", "2099-12-31")
            if start <= today_iso <= end:
                result.append(offer)
        return result

    def find_coupon(self, code: str, today_iso: str) -> dict | None:
        target = str(code or "").strip().upper()
        if not target:
            return None
        for offer in self.get_active(today_iso):
            if str(offer.get("coupon_code", "")).strip().upper() == target:
                return offer
        return None

    def save_offer(self, payload: dict) -> None:
        self.repo.upsert_offer(
            {
                "legacy_name": payload.get("name", ""),
                "offer_type": payload.get("type", "percentage"),
                "value": payload.get("value", 0.0),
                "service_name": payload.get("service_name", ""),
                "coupon_code": payload.get("coupon_code", ""),
                "min_bill": payload.get("min_bill", 0.0),
                "valid_from": payload.get("valid_from", ""),
                "valid_to": payload.get("valid_to", ""),
                "active": payload.get("active", True),
                "notes": payload.get("description", ""),
            }
        )

    def save_all(self, offers: list[dict]) -> None:
        existing_names = {row.get("legacy_name", "") for row in self.repo.list_offers()}
        incoming_names = {
            str(offer.get("name", "")).strip()
            for offer in offers
            if str(offer.get("name", "")).strip()
        }
        for offer in offers:
            self.save_offer(offer)
        for stale_name in existing_names - incoming_names:
            if stale_name:
                self.repo.delete_offer(stale_name)

    def delete_offer(self, name: str) -> None:
        self.repo.delete_offer(name)

    @staticmethod
    def _to_legacy_offer(row: dict) -> dict:
        return {
            "name": row.get("legacy_name", ""),
            "type": row.get("offer_type", "percentage"),
            "value": float(row.get("value", 0.0) or 0.0),
            "service_name": row.get("service_name", ""),
            "coupon_code": row.get("coupon_code", ""),
            "min_bill": float(row.get("min_bill", 0.0) or 0.0),
            "valid_from": row.get("valid_from", ""),
            "valid_to": row.get("valid_to", ""),
            "description": row.get("notes", ""),
            "active": bool(row.get("active", 1)),
            "created": row.get("created_at", ""),
        }
