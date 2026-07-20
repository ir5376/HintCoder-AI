from __future__ import annotations

from src.content_modules.coding import CodingModule
from src.content_modules.information_processing_engineer import InformationProcessingEngineerModule
from src.learning_engine.content import ContentModule


class ContentModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, ContentModule] = {}
        self.register(CodingModule())
        self.register(InformationProcessingEngineerModule())

    def register(self, module: ContentModule) -> None:
        self._modules[module.module_id] = module

    def get(self, module_id: str) -> ContentModule:
        return self._modules[module_id]

    def list_modules(self) -> list[dict[str, str]]:
        return [
            {"module_id": module.module_id, "display_name": module.display_name}
            for module in self._modules.values()
        ]
