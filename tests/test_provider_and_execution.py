import os
import tempfile

from src.database import get_session, init_db
from src.execution_engine.trace import PythonExecutionTracer
from src.models.learning import ProviderProblem, ProviderSubmission
from src.provider_adapters.external import ExternalProviderAdapter
from src.services.provider_service import ProviderService


def test_external_provider_imports_problem_as_learning_content():
    adapter = ExternalProviderAdapter()

    imported = adapter.import_problem(
        {
            "problem_title": "Two Sum",
            "problem_url": "https://example.com/two-sum",
            "language": "python3",
        }
    )

    assert imported.provider == "external"
    assert imported.content.content_type == "coding"
    assert imported.content.language == "Python"
    assert imported.content.coding_template.startswith("def solution")


def test_external_provider_maps_supported_languages():
    adapter = ExternalProviderAdapter()

    assert adapter.map_language("cpp") == "C++"
    assert adapter.map_language("js") == "JavaScript"
    assert adapter.map_language("unknown") == "Python"


def test_python_execution_tracer_records_steps_and_stdout():
    trace = PythonExecutionTracer(max_steps=20).run("x = 1\nx += 2\nprint(x)")

    assert trace.status == "completed"
    assert trace.stdout.strip() == "3"
    assert len(trace.steps) >= 2
    assert trace.to_dict()["steps"][0]["line_no"] >= 1


def test_provider_service_persists_import_and_synced_submission_with_trace():
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = f"sqlite:///{os.path.join(temp_dir, 'test.db')}"
        init_db(database_url)

        with get_session(database_url) as session:
            service = ProviderService(session)
            imported = service.import_problem(
                "external",
                {
                    "problem_title": "Trace Demo",
                    "problem_url": "https://example.com/trace-demo",
                    "language": "Python",
                    "provider_problem_id": "trace-demo",
                },
            )
            synced = service.sync_submission(
                "external",
                {
                    "provider_problem_id": "trace-demo",
                    "content_id": imported["content"]["id"],
                    "status": "accepted",
                    "language": "Python",
                    "code": "answer = 40 + 2\nprint(answer)",
                },
            )
            provider_problem_count = session.query(ProviderProblem).count()
            provider_submission = session.query(ProviderSubmission).one()

        assert provider_problem_count == 1
        assert synced["status"] == "accepted"
        assert synced["trace"]["stdout"].strip() == "42"
        assert provider_submission.trace_json != "{}"
