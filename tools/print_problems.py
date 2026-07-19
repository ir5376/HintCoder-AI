import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import get_session
from src.models.problem import Problem
import json

DB_URL = 'sqlite:///hintcode.db'

with get_session(DB_URL) as s:
    problems = s.query(Problem).order_by(Problem.id).all()
    out = []
    for p in problems:
        out.append({
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'category': p.category,
            'difficulty': p.difficulty,
            'problem_type': p.problem_type,
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))
