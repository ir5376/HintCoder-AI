from src.database import init_db, get_session
from src.models.problem import Problem

if __name__ == '__main__':
    db_url = 'sqlite:///test_dev.db'
    init_db(db_url)
    with get_session(db_url) as s:
        problems = s.query(Problem).order_by(Problem.id).limit(5).all()
        for p in problems:
            print(p.id, p.title)
