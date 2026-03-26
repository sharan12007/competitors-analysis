"""
config.py - Single source of truth for all environment variables.
Every other module imports `settings` from here. Never read os.environ directly elsewhere.
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    TAVILY_API_KEY: str
    FIRECRAWL_API_KEY: str
    GITHUB_TOKEN: str

    EXA_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    BROWSER_HEADLESS: bool = False
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    BROWSER_TIMEOUT_SEC: int = 90
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    model_config = {
        "env_file": os.path.join(os.path.dirname(__file__), "..", ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
