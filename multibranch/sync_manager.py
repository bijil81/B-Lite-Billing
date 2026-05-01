"""High-level coordinator for optional multi-branch sync."""

from __future__ import annotations

from .api_client import MultiBranchApiClient


class MultiBranchSyncManager:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.client = MultiBranchApiClient(
            server_url=self.config.get("server_url", ""),
            api_key=self.config.get("api_key", ""),
        )

    def test_connection(self) -> tuple[bool, str]:
        return self.client.test_connection()
