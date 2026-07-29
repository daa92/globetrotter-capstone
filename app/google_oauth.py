"""
app/google_oauth.py

Verifies the ID token Google's "Sign In With Google" button hands the
frontend. This is a pure signature/audience/expiry check against Google's
published public keys — it never needs the Client Secret, only the
Client ID (as the expected "audience").

Isolated in its own module for one reason: a real call here reaches
Google's live certificate endpoint over the network, which a test suite
should never depend on. Every test in tests/test_google_auth.py monkeypatches
`verify_google_id_token` at its import site in app/routers/auth.py instead
of hitting Google for real.
"""
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings

_google_request = google_requests.Request()


def verify_google_id_token(token: str) -> dict:
    """Returns the decoded payload (sub, email, email_verified, name,
    picture, ...) on success. Raises ValueError if the token is invalid,
    expired, or issued for a different Client ID."""
    return google_id_token.verify_oauth2_token(token, _google_request, settings.GOOGLE_CLIENT_ID)
