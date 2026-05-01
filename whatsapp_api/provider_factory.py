"""Factory for optional WhatsApp API providers."""

from __future__ import annotations

from .base_provider import BaseWhatsAppProvider
from .gupshup_provider import GupshupProvider
from .meta_provider import MetaProvider
from .twilio_provider import TwilioProvider


PROVIDER_MAP = {
    "meta": MetaProvider,
    "gupshup": GupshupProvider,
    "twilio": TwilioProvider,
}


def create_provider(provider_name: str, settings: dict | None = None) -> BaseWhatsAppProvider:
    provider_cls = PROVIDER_MAP.get((provider_name or "meta").strip().lower(), MetaProvider)
    return provider_cls(settings=settings or {})
