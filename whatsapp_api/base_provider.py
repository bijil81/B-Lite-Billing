"""Base contracts for optional WhatsApp API providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderResult:
    ok: bool
    message: str


class BaseWhatsAppProvider:
    provider_name = "base"

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {}

    def validate(self) -> ProviderResult:
        return ProviderResult(False, f"{self.provider_name} validation is not implemented yet.")

    def test_send(self, to_number: str, message: str) -> ProviderResult:
        return ProviderResult(False, f"{self.provider_name} test send is not implemented yet.")
