"""Workflow layer for v5 users/auth data."""

from __future__ import annotations

from repositories.users_repo import UsersRepository


class AuthService:
    def __init__(self, repo: UsersRepository | None = None):
        self.repo = repo or UsersRepository()

    def list_users(self) -> list[dict]:
        return self.repo.list_all()

    def get_user(self, username: str) -> dict | None:
        return self.repo.get_by_username(username)

    def save_user(self, payload: dict) -> None:
        self.repo.upsert(payload)
