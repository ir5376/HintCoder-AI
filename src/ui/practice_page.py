from __future__ import annotations

from src.content_modules.registry import ContentModuleRegistry
from src.learning_engine.engine import LearningEngine
from src.services.hint_service import HintService
from src.services.problem_service import ProblemService
from src.ui.module_practice_page import render_module_practice
from src.ui.problem_detail_page import render_problem_detail


def render_practice_page(
    *,
    problem_service: ProblemService,
    registry: ContentModuleRegistry,
    learning_engine: LearningEngine,
    hint_service: HintService,
    selected_module_id: str,
    app_mode: str,
    preferred_language: str | None = None,
    external_title: str | None = None,
    external_url: str | None = None,
) -> None:
    if selected_module_id != "coding":
        render_module_practice(
            registry=registry,
            learning_engine=learning_engine,
            hint_service=hint_service,
            selected_module_id=selected_module_id,
            app_mode=app_mode,
        )
        return

    render_problem_detail(
        problem_service,
        hint_service=hint_service,
        app_mode=app_mode,
        preferred_language=preferred_language,
        external_title=external_title,
        external_url=external_url,
    )
