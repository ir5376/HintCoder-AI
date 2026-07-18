import os
import tempfile

from src.database import init_db, get_engine, get_session
from src.models.problem import Problem


def test_database_initializes_and_seeds():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        database_url = f"sqlite:///{db_path}"

        init_db(database_url)

        engine = get_engine(database_url)
        with get_session(database_url) as session:
            count = session.query(Problem).count()

        assert count == 10
        assert os.path.exists(db_path)
