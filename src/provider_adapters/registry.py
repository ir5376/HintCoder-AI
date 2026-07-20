from __future__ import annotations

from src.provider_adapters.base import ProviderAdapter
from src.provider_adapters.external import ExternalProviderAdapter


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderAdapter] = {}
        self.register(ExternalProviderAdapter())

    def register(self, provider: ProviderAdapter) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> ProviderAdapter:
        return self._providers[provider_id]

    def list_providers(self) -> list[dict]:
        return [provider.metadata() for provider in self._providers.values()]
