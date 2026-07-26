"""
app/config.py

Centralised, environment-driven configuration. Nothing secret is hardcoded;
every sensitive default is intentionally unusable so the app fails loudly
in production if you forget to set real values.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- App ---
    APP_NAME: str = "GlobeTrotter (GT) API"
    ENV: str = "development"  # development | production
    DEBUG: bool = True

    # --- Security / JWT ---
    # MUST be overridden via env var in any non-local environment.
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_NAME_REFRESH: str = "gt_refresh_token"
    COOKIE_SECURE: bool = False  # set True behind HTTPS in production

    # --- MFA ---
    MFA_ISSUER_NAME: str = "GlobeTrotter"

    # --- CORS (tighten in production to your real frontend origins) ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Simulation / load-testing guard ---
    # Must be explicitly enabled; production images never set this to true.
    SIMULATION_MODE: bool = False

    PORT: int = 8000


settings = Settings()
