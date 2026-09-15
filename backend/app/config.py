"""
Central place for all configuration / environment variables.

Why this file exists (interview point):
Keeping all env vars in one Settings object means the rest of the app
never calls os.environ.get() directly. That makes it obvious what the
service depends on, and makes it trivial to swap in a test config.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- GitHub ---
    github_token: str = ""          # Personal access token OR GitHub App installation token
    github_webhook_secret: str = "" # Used to verify that webhook calls really come from GitHub

    # --- LLM ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # cheap + fast, good enough for a portfolio project

    # --- Database ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "code_review_agent"

    # --- App ---
    app_env: str = "development"
    frontend_origin: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
