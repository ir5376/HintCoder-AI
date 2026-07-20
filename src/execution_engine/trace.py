from __future__ import annotations

import contextlib
import io
import sys
import time
import traceback
from dataclasses import dataclass, field
from types import FrameType
from typing import Any


@dataclass(frozen=True)
class TraceStep:
    line_no: int
    event: str
    function_name: str
    locals_snapshot: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionTrace:
    language: str
    status: str
    steps: list[TraceStep]
    stdout: str
    stderr: str
    duration_ms: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "status": self.status,
            "steps": [step.__dict__ for step in self.steps],
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class PythonExecutionTracer:
    def __init__(self, *, max_steps: int = 200) -> None:
        self.max_steps = max_steps

    def run(self, code: str, *, stdin: str = "") -> ExecutionTrace:
        steps: list[TraceStep] = []
        stdout = io.StringIO()
        stderr = io.StringIO()
        start = time.perf_counter()
        status = "completed"
        error = None
        globals_scope = {"__name__": "__main__"}

        def tracer(frame: FrameType, event: str, arg: Any):
            if event == "line" and len(steps) >= self.max_steps:
                raise RuntimeError(f"Execution trace stopped after {self.max_steps} steps.")
            if event == "line":
                steps.append(
                    TraceStep(
                        line_no=frame.f_lineno,
                        event=event,
                        function_name=frame.f_code.co_name,
                        locals_snapshot=self._safe_locals(frame.f_locals),
                    )
                )
            return tracer

        old_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin)
        sys.settrace(tracer)
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(code, "<nextep-python-trace>", "exec"), globals_scope)
        except Exception:
            status = "error"
            error = traceback.format_exc(limit=5)
        finally:
            sys.settrace(None)
            sys.stdin = old_stdin

        duration_ms = int((time.perf_counter() - start) * 1000)
        return ExecutionTrace(
            language="Python",
            status=status,
            steps=steps,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
            duration_ms=duration_ms,
            error=error,
        )

    def _safe_locals(self, local_values: dict[str, Any]) -> dict[str, str]:
        safe = {}
        for key, value in local_values.items():
            if key.startswith("__"):
                continue
            try:
                text = repr(value)
            except Exception:
                text = "<unrepresentable>"
            safe[key] = text[:120]
        return safe
