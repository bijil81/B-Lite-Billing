"""Compatibility adapter for gradual auth/users migration to v5 services."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.auth_service import AuthService
from db import db_transaction

_auth_service = AuthService()

def use_v5_users_db() -> bool:
    return bool(get_settings().get("use_v5_users_db", False))

def get_users_legacy_map_v5() -> dict:
    """Returns users in legacy format: {username: {password, role, name, active}}"""
    users = _auth_service.list_users()
    result = {}
    for u in users:
        uname = u.get("username", "")
        if not uname: continue
        result[uname] = {
            "password": u.get("password_hash", ""),
            "role": u.get("role", "staff"),
            "name": u.get("display_name", ""),
            "active": bool(u.get("active", True))
        }
    return result

def save_users_legacy_map_v5(data: dict) -> None:
    """Receives legacy format and saves via AuthService transaction."""
    with db_transaction():
        # Using a transaction context for safety
        incoming_keys = set()
        for uname, udata in data.items():
            if not uname: continue
            incoming_keys.add(uname)
            _auth_service.save_user({
                "username": uname,
                "password_hash": udata.get("password", ""),
                "role": udata.get("role", "staff"),
                "display_name": udata.get("name", ""),
                "active": udata.get("active", True),
            })
        
        # Soft delete missing users
        for existing in _auth_service.list_users():
            uname = existing.get("username", "")
            if uname and uname not in incoming_keys:
                _auth_service.save_user({
                    "username": uname,
                    "password_hash": existing.get("password_hash", ""),
                    "role": existing.get("role", "staff"),
                    "display_name": existing.get("display_name", ""),
                    "active": False,
                })

def delete_user_v5(username: str) -> None:
    """Hard-delete a user row for the User Management Delete action."""
    _auth_service.delete_user(username)
