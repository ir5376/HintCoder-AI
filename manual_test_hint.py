from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _load_hint_service_class():
    service_path = ROOT_DIR / "src" / "services" / "hint_service.py"
    source = service_path.read_text(encoding="utf-8")

    if "<<<<<<<" in source and "=======" in source and ">>>>>>>" in source:
        head_branch = source.split("<<<<<<< HEAD", 1)[1].split("=======", 1)[0]
        branch_text = head_branch
    else:
        branch_text = source

    match = re.search(r"class HintService:\n(?P<body>.*)", branch_text, re.S)
    if not match:
        raise RuntimeError("Could not locate HintService class in src/services/hint_service.py")

    namespace: dict[str, object] = {"__builtins__": __builtins__}
    exec("class HintService:\n" + match.group("body"), namespace)
    return namespace["HintService"]


HintService = _load_hint_service_class()
service = HintService()

problem = {
    "title": "Two Sum",
    "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to the target.",
    "source_platform": "LeetCode",
    "source_url": "https://leetcode.com/problems/two-sum/",
    "external_problem_id": "1",
    "difficulty": "Easy",
    "programming_language": "Python",
}

student_code = """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
"""

hint = service.get_hint(problem, student_code, hint_level=1)

print("Generated hint:")
print(hint)
print("Provider info: current HintService API does not expose whether OpenAI or fallback was used.")

if os.getenv("OPENAI_API_KEY"):
    print("OpenAI key is configured in the environment.")
else:
    print("OpenAI key is not configured in the environment.")
