from src.content_modules.coding import CodingModule
from src.content_modules.information_processing_engineer import InformationProcessingEngineerModule
from src.content_modules.registry import ContentModuleRegistry
from src.learning_engine.content import LearningContent
from src.learning_engine.templates import StarterTemplateRegistry


def test_learning_content_interface_accepts_future_module_fields():
    content = LearningContent(
        id="custom-001",
        title="Sample",
        content="Answer briefly.",
        difficulty="Easy",
        topic="General",
        source="custom",
        content_type="short_answer",
        question_type="short_answer",
        answer="Sample answer",
        metadata={"module": "custom_content"},
    )

    assert content.id == "custom-001"
    assert content.title == "Sample"
    assert content.metadata["module"] == "custom_content"


def test_coding_module_converts_problem_to_learning_content_with_language_template():
    problem = {
        "id": 1,
        "title": "Two Sum",
        "difficulty": "Easy",
        "category": "Arrays",
        "source_reference": "https://example.com/two-sum",
        "problem_type": "Function Implementation",
        "description": "Return indices.",
        "starter_code": "def two_sum(nums, target):\n    pass",
    }

    content = CodingModule().to_learning_content(problem, language="JavaScript")

    assert content.title == "Two Sum"
    assert content.topic == "Arrays"
    assert content.language == "JavaScript"
    assert content.metadata["module"] == "coding"
    assert "function solution" in content.starter_template


def test_starter_template_registry_supports_required_languages():
    registry = StarterTemplateRegistry()

    assert registry.supported_languages() == ["Python", "Java", "C++", "JavaScript", "C"]
    assert "int main" in registry.get_template("C")
    assert registry.get_ace_language("JavaScript") == "javascript"


def test_content_module_registry_lists_coding_module():
    modules = ContentModuleRegistry().list_modules()

    assert {"module_id": "coding", "display_name": "Coding"} in modules
    assert {"module_id": "information_processing_engineer", "display_name": "Information Processing Engineer"} in modules


def test_information_processing_engineer_module_has_demo_questions():
    module = InformationProcessingEngineerModule()
    content = module.list_content()

    assert len(content) == 12
    assert {item.content_type for item in content} == {"multiple_choice", "short_answer"}
    assert content[0].id.startswith("ipe-")
    assert content[0].answer
