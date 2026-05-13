"""Compatibility adapter for gradual memberships migration to v5 services."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.membership_service import MembershipService
from db import db_transaction

_membership_service = MembershipService()

def use_v5_memberships_db() -> bool:
    return bool(get_settings().get("use_v5_memberships_db", False))

def get_memberships_legacy_map_v5() -> dict:
    """Returns memberships in legacy format: dict of {phone: membership_dict}"""
    return _membership_service.get_all()

def save_memberships_legacy_map_v5(data: dict) -> None:
    """Receives legacy format dict and saves via MembershipService transaction."""
    with db_transaction():
        # save_all handles soft delete now via the repo updates we made
        _membership_service.save_all(data)
