import sys
from pathlib import Path

# Ensure repository root is on sys.path so we can import `src`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import get_engine, init_db
from src.models.base import Base

DB_URL = 'sqlite:///hintcode.db'

if __name__ == '__main__':
    engine = get_engine(DB_URL)
    print('Dropping existing tables...')
    Base.metadata.drop_all(engine)
    print('Recreating tables and seeding...')
    init_db(DB_URL)
    engine.dispose()
    print('Reseed complete')
