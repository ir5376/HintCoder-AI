from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_STARTER_TEMPLATES = {
    "Python": "def solution():\n    pass\n",
    "Java": "class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}\n",
    "C++": "#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n",
    "JavaScript": "function solution() {\n    // Write your solution here\n}\n",
    "C": "#include <stdio.h>\n\nint main(void) {\n    // Write your solution here\n    return 0;\n}\n",
}


ACE_LANGUAGE_MAP = {
    "Python": "python",
    "Java": "java",
    "C++": "c_cpp",
    "JavaScript": "javascript",
    "C": "c_cpp",
}


@dataclass(frozen=True)
class StarterTemplateRegistry:
    templates: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_STARTER_TEMPLATES))

    def supported_languages(self) -> list[str]:
        return list(self.templates.keys())

    def get_template(self, language: str | None, fallback: str = "") -> str:
        if language and language in self.templates:
            return self.templates[language]
        return fallback or self.templates["Python"]

    def get_ace_language(self, language: str | None) -> str:
        return ACE_LANGUAGE_MAP.get(language or "Python", "python")
