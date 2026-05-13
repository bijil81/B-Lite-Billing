"""Compatibility adapter for gradual offers/redeem codes migration to v5 services."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.offers_service import OffersService
from db import db_transaction

_offers_service = OffersService()

def use_v5_offers_db() -> bool:
    return bool(get_settings().get("use_v5_offers_db", False))

def get_offers_legacy_map_v5() -> list:
    """Returns offers in legacy format: list of dicts"""
    return _offers_service.get_all()

def save_offers_legacy_map_v5(data: list) -> None:
    """Receives legacy format list and saves via OffersService transaction."""
    with db_transaction():
        # save_all handles soft delete now
        _offers_service.save_all(data)

def hard_delete_offer_v5(name: str) -> None:
    with db_transaction():
        _offers_service.hard_delete_offer(name)
