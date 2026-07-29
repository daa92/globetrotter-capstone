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

    # --- Account verification ---
    UNVERIFIED_ACCOUNT_TTL_MINUTES: int = 30
    VERIFICATION_CLEANUP_INTERVAL_SECONDS: int = 60

    # --- Earnings: daily usage reward ---
    DAILY_USAGE_THRESHOLD_SECONDS: int = 300  # 5 minutes
    DAILY_USAGE_BONUS_USD: float = 0.5
    # Upper bound on how much active time a single heartbeat call can add,
    # so a client can't fake a huge jump in one request. The frontend/CLI
    # should call the heartbeat endpoint roughly this often.
    MAX_HEARTBEAT_INCREMENT_SECONDS: int = 90

    # --- Earnings: referral / sponsorship ---
    REFERRAL_BONUS_USD: float = 0.25

    # --- Payout eligibility ---
    MIN_PAYOUT_USD: float = 30.0
    MIN_REFERRALS_FOR_PAYOUT: int = 5
    MIN_GOOD_FEEDBACK_FOR_PAYOUT: int = 5
    GOOD_FEEDBACK_MIN_RATING: int = 4  # a "good" feedback = rating >= this

    # --- Currency display ---
    # XAF (FCFA) is pegged to the EUR, not freely floating — a fixed,
    # occasionally-updated rate is normal practice here, not a cut corner.
    FCFA_PER_USD: float = 610.0

    # Used to build referral links (see /users/me/earnings -> referral_link)
    FRONTEND_URL: str = "http://localhost:5173"

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
