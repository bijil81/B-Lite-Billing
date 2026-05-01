"""Legacy users -> v5_app_users migration."""

from __future__ import annotations

from auth import get_users
from repositories.users_repo import UsersRepository


def migrate_users(dry_run: bool = True) -> dict:
    users = get_users()
    repo = UsersRepository()
    migrated = []
    for username, user in users.items():
        row = {
            "username": username,
            "password_hash": user.get("password", ""),
            "role": user.get("role", "staff"),
            "display_name": user.get("name", username),
            "active": user.get("active", True),
        }
        if not dry_run:
            repo.upsert(row)
        migrated.append(username)
    return {
        "source_count": len(users),
        "migrated": migrated,
        "dry_run": dry_run,
    }
