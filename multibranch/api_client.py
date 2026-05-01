"""API client placeholder for customer-owned multi-branch servers."""

from __future__ import annotations


class MultiBranchApiClient:
    def __init__(self, server_url: str = "", api_key: str = ""):
        self.server_url = (server_url or "").strip()
        self.api_key = (api_key or "").strip()

    def test_connection(self) -> tuple[bool, str]:
        if not self.server_url:
            return False, "Server URL is required."
        if not self.api_key:
            return False, "API key is required."
        return True, "Configuration ready. Server validation pending."
