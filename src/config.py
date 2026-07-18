import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str


def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL", "sqlite:///hintcode.db")
    return Settings(database_url=database_url)
