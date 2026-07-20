from __future__ import annotations

from src.learning_engine.domain import ProviderAdapter, ProviderMetadata
from src.provider_adapters.static_coding import (
    BaekjoonProvider,
    CustomProvider,
    LeetCodeProvider,
    ProgrammersProvider,
    StaticCodingProviderAdapter,
)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderAdapter] = {}
        self.register(LeetCodeProvider())
        self.register(ProgrammersProvider())
        self.register(BaekjoonProvider())
        self.register(StaticCodingProviderAdapter("codeforces", "Codeforces", icon="CF"))
        self.register(StaticCodingProviderAdapter("atcoder", "AtCoder", icon="AC"))
        self.register(CustomProvider())

    def register(self, provider: ProviderAdapter) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> ProviderAdapter:
        return self._providers[provider_id]

    def list_providers(self) -> list[ProviderMetadata]:
        return [provider.metadata() for provider in self._providers.values()]

    def list_importable_providers(self) -> list[ProviderAdapter]:
        return [provider for provider in self._providers.values() if provider.supports_url or provider.supports_search]
