from __future__ import annotations

from src.learning_engine.content import LearningContent


INFORMATION_PROCESSING_ENGINEER_CONTENT = [
    {
        "id": "ipe-001",
        "title": "Database Normalization",
        "content": "Which normal form removes partial dependency from a relation?",
        "difficulty": "Easy",
        "topic": "Database",
        "question_type": "multiple_choice",
        "choices": ["1NF", "2NF", "3NF", "BCNF"],
        "answer": "2NF",
        "metadata": {"concept": "normalization"},
    },
    {
        "id": "ipe-002",
        "title": "Transaction ACID",
        "content": "Which ACID property guarantees that committed data survives system failure?",
        "difficulty": "Easy",
        "topic": "Database",
        "question_type": "multiple_choice",
        "choices": ["Atomicity", "Consistency", "Isolation", "Durability"],
        "answer": "Durability",
        "metadata": {"concept": "acid"},
    },
    {
        "id": "ipe-003",
        "title": "OSI Layer",
        "content": "TCP mainly operates at which OSI layer?",
        "difficulty": "Easy",
        "topic": "Network",
        "question_type": "multiple_choice",
        "choices": ["Data Link", "Network", "Transport", "Application"],
        "answer": "Transport",
        "metadata": {"concept": "osi"},
    },
    {
        "id": "ipe-004",
        "title": "IP Addressing",
        "content": "What is the purpose of subnetting?",
        "difficulty": "Medium",
        "topic": "Network",
        "question_type": "short_answer",
        "choices": None,
        "answer": "To divide a network into smaller logical networks.",
        "metadata": {"concept": "subnetting"},
    },
    {
        "id": "ipe-005",
        "title": "Software Development Model",
        "content": "Which model repeats planning, risk analysis, engineering, and evaluation?",
        "difficulty": "Medium",
        "topic": "Software Engineering",
        "question_type": "multiple_choice",
        "choices": ["Waterfall", "Spiral", "V-Model", "Prototype"],
        "answer": "Spiral",
        "metadata": {"concept": "process_model"},
    },
    {
        "id": "ipe-006",
        "title": "UML Diagram",
        "content": "Which UML diagram is best for showing object interactions over time?",
        "difficulty": "Easy",
        "topic": "Software Engineering",
        "question_type": "multiple_choice",
        "choices": ["Class Diagram", "Use Case Diagram", "Sequence Diagram", "Deployment Diagram"],
        "answer": "Sequence Diagram",
        "metadata": {"concept": "uml"},
    },
    {
        "id": "ipe-007",
        "title": "Security Attack",
        "content": "An attacker secretly relays communication between two parties. What is this attack called?",
        "difficulty": "Medium",
        "topic": "Security",
        "question_type": "multiple_choice",
        "choices": ["SQL Injection", "Man-in-the-Middle", "Phishing", "DDoS"],
        "answer": "Man-in-the-Middle",
        "metadata": {"concept": "mitm"},
    },
    {
        "id": "ipe-008",
        "title": "Encryption",
        "content": "Name one key difference between symmetric and asymmetric encryption.",
        "difficulty": "Medium",
        "topic": "Security",
        "question_type": "short_answer",
        "choices": None,
        "answer": "Symmetric encryption uses one shared key; asymmetric encryption uses a public/private key pair.",
        "metadata": {"concept": "encryption"},
    },
    {
        "id": "ipe-009",
        "title": "Operating System Scheduling",
        "content": "Which scheduling algorithm always runs the process with the shortest estimated processing time first?",
        "difficulty": "Medium",
        "topic": "Operating Systems",
        "question_type": "multiple_choice",
        "choices": ["FCFS", "SJF", "Round Robin", "Priority Aging"],
        "answer": "SJF",
        "metadata": {"concept": "scheduling"},
    },
    {
        "id": "ipe-010",
        "title": "Deadlock Conditions",
        "content": "List two necessary conditions for deadlock.",
        "difficulty": "Hard",
        "topic": "Operating Systems",
        "question_type": "short_answer",
        "choices": None,
        "answer": "Mutual exclusion, hold and wait, no preemption, or circular wait.",
        "metadata": {"concept": "deadlock"},
    },
    {
        "id": "ipe-011",
        "title": "Data Structure",
        "content": "Which data structure follows FIFO order?",
        "difficulty": "Easy",
        "topic": "Data Structures",
        "question_type": "multiple_choice",
        "choices": ["Stack", "Queue", "Tree", "Graph"],
        "answer": "Queue",
        "metadata": {"concept": "queue"},
    },
    {
        "id": "ipe-012",
        "title": "Big-O",
        "content": "Binary search on a sorted array has which time complexity?",
        "difficulty": "Easy",
        "topic": "Algorithms",
        "question_type": "multiple_choice",
        "choices": ["O(1)", "O(log n)", "O(n)", "O(n log n)"],
        "answer": "O(log n)",
        "metadata": {"concept": "complexity"},
    },
]


class InformationProcessingEngineerModule:
    module_id = "information_processing_engineer"
    display_name = "Information Processing Engineer"

    def list_content(self) -> list[LearningContent]:
        return [self.to_learning_content(item) for item in INFORMATION_PROCESSING_ENGINEER_CONTENT]

    def get_content(self, content_id: str) -> LearningContent | None:
        for content in self.list_content():
            if content.id == content_id:
                return content
        return None

    def to_learning_content(self, item: dict, *, language: str | None = None) -> LearningContent:
        return LearningContent(
            id=item["id"],
            title=item["title"],
            content=item["content"],
            difficulty=item["difficulty"],
            topic=item["topic"],
            source="Nextep Demo",
            content_type="multiple_choice" if item["question_type"] == "multiple_choice" else "short_answer",
            question_type=item["question_type"],
            choices=item.get("choices"),
            answer=item["answer"],
            metadata={"module": self.module_id, **item.get("metadata", {})},
            coding_template=None,
            language=None,
        )
