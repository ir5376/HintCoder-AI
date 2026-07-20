import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    gemini_model: str


def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL", "sqlite:///hintcode.db")
    gemini_model = os.environ.get("GEMINI_MODEL", "")
    return Settings(database_url=database_url, gemini_model=gemini_model)
