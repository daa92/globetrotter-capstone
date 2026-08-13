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

    # --- Database (Phase 2: TiDB, MySQL-compatible) ---
    # Production (Render): a TiDB connection string, e.g.
    #   mysql+pymysql://user:password@host:4000/globetrotter
    # If unset, falls back to a local SQLite file — keeps local dev/tests
    # zero-config. See app/db.py.
    DATABASE_URL: str = ""

    # --- Admin bootstrap ---
    # One-time-use secret used to promote an existing account to admin via
    # POST /auth/admin/bootstrap. Empty by default so the endpoint is a
    # hard 404-equivalent (403) until explicitly configured. Set this as an
    # env var on Render, call the endpoint once, then unset/rotate it.
    ADMIN_BOOTSTRAP_SECRET: str = ""

    # --- Brevo (transactional email) ---
    # If BREVO_API_KEY is unset, outbox.send() falls back to logging to
    # data/outbox.json instead of a real API call — keeps local dev/tests
    # working with zero external calls or secrets.
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = ""
    BREVO_SENDER_NAME: str = "GlobeTrotter"
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

    # --- Password recovery ---
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 30

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

    # --- Google Sign-In ---
    # Only the Client ID is needed — we verify the ID token Google's button
    # hands the frontend directly (signature check against Google's public
    # keys), which never requires the Client Secret. Leaving this empty
    # disables the /auth/google endpoint with a clear error rather than
    # crashing.
    GOOGLE_CLIENT_ID: str = ""

    # --- Free map/geo stack (Cameroon-scoped) ---
    # Nominatim and Overpass need no API key at all, but Nominatim's usage
    # policy caps requests at 1/second and expects a real identifying
    # User-Agent — set GEO_USER_AGENT to something with a real contact
    # before deploying. OpenRouteService needs a free API key (2,000
    # requests/day free tier) — sign up at openrouteservice.org.
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    OVERPASS_BASE_URL: str = "https://overpass-api.de/api/interpreter"
    OPENROUTESERVICE_BASE_URL: str = "https://api.openrouteservice.org"
    OPENROUTESERVICE_API_KEY: str = ""
    GEO_USER_AGENT: str = "GT-GlobeTrotter/0.1 (contact: set-a-real-contact-email@example.com)"
    # Nominatim viewbox format: left,top,right,bottom (min_lon,max_lat,max_lon,min_lat)
    CAMEROON_VIEWBOX: str = "8.3,13.1,16.2,1.6"
    # How long a cached geo result is considered fresh before we hit the
    # live API again — keeps us well under every service's rate limits
    # while still updating "frequently enough" for a Cameroon-scoped app.
    GEO_CACHE_TTL_HOURS: int = 168  # 7 days

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
