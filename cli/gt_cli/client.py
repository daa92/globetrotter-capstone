"""
gt_cli/client.py

A thin wrapper around `requests` that:
  - talks to whatever GT_API_URL / config api_url points at
  - attaches `Authorization: Bearer <access_token>` automatically
  - loads/saves the refresh-token cookie jar between CLI invocations
  - transparently refreshes an expired access token before a call fails,
    the same way a web frontend would do silently in the background
  - turns HTTP error responses into a single, consistent GTApiError so
    main.py doesn't need to know about requests/HTTP details
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from gt_cli import config


class GTApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


class GTClient:
    def __init__(self):
        self.cfg = config.load_config()
        self.base_url = self.cfg["api_url"].rstrip("/")
        self.session = requests.Session()
        self.session.cookies = config.get_cookie_jar()

    # -- internal helpers ----------------------------------------------

    def _save_cookies(self) -> None:
        config.save_cookie_jar(self.session.cookies)

    def _auth_headers(self) -> dict:
        token = self.cfg.get("access_token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _token_expired(self) -> bool:
        expires_at = self.cfg.get("access_token_expires_at")
        if not expires_at:
            return True
        # refresh a little early (30s buffer) rather than cutting it exactly at expiry
        return datetime.now(timezone.utc) >= datetime.fromisoformat(expires_at) - timedelta(seconds=30)

    def _store_access_token(self, access_token: str, expires_in_minutes: int, username: Optional[str] = None) -> None:
        self.cfg["access_token"] = access_token
        self.cfg["access_token_expires_at"] = (
            datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        ).isoformat()
        if username:
            self.cfg["username"] = username
        config.save_config(self.cfg)

    def _refresh_access_token(self) -> bool:
        """Returns True if refresh succeeded, False if the refresh cookie is
        missing/expired (caller should tell the user to log in again)."""
        resp = self.session.post(f"{self.base_url}/auth/refresh")
        self._save_cookies()
        if resp.status_code != 200:
            return False
        body = resp.json()
        self._store_access_token(body["access_token"], body["expires_in_minutes"])
        return True

    def _request(self, method: str, path: str, auth: bool = False, **kwargs) -> Any:
        if auth and self._token_expired():
            self._refresh_access_token()  # best-effort; if it fails, the real call below will 401 and we surface that

        headers = kwargs.pop("headers", {})
        if auth:
            headers.update(self._auth_headers())

        resp = self.session.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        self._save_cookies()

        # One retry after a transparent refresh if we got a 401 on what we
        # thought was a valid token (e.g. server restarted, clock drift).
        if auth and resp.status_code == 401 and self._refresh_access_token():
            headers.update(self._auth_headers())
            resp = self.session.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
            self._save_cookies()

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise GTApiError(resp.status_code, str(detail))

        return resp.json() if resp.content else None

    # -- public API -------------------------------------------------------

    def register(self, username: str, email: str, password: str, preferences: list[str], referral_code: Optional[str] = None) -> dict:
        payload = {"username": username, "email": email, "password": password, "preferences": preferences}
        if referral_code:
            payload["referral_code"] = referral_code
        return self._request("POST", "/auth/register", json=payload)

    def register_phone(self, username: str, phone: str, password: str, preferences: list[str], referral_code: Optional[str] = None) -> dict:
        payload = {"username": username, "phone": phone, "password": password, "preferences": preferences}
        if referral_code:
            payload["referral_code"] = referral_code
        return self._request("POST", "/auth/register/phone", json=payload)

    def request_password_reset(self, username: str) -> dict:
        return self._request("POST", "/auth/password-reset/request", json={"username": username})

    def confirm_password_reset(self, token: str, new_password: str) -> dict:
        return self._request("POST", "/auth/password-reset/confirm", json={"token": token, "new_password": new_password})

    def verify(self, token: str) -> dict:
        return self._request("POST", "/auth/verify", json={"token": token})

    def login(self, username: str, password: str, mfa_code: Optional[str] = None) -> dict:
        payload = {"username": username, "password": password}
        if mfa_code:
            payload["mfa_code"] = mfa_code
        result = self._request("POST", "/auth/login", json=payload)
        if result.get("mfa_required"):
            return result  # caller (main.py) prompts for the code and calls again
        self._store_access_token(result["access_token"], result["expires_in_minutes"], username=username)
        return result

    def logout(self) -> None:
        try:
            self._request("POST", "/auth/logout")
        finally:
            config.clear_session()

    def whoami(self) -> dict:
        return self._request("GET", "/users/me", auth=True)

    def mfa_setup(self) -> dict:
        return self._request("POST", "/auth/mfa/setup", auth=True)

    def mfa_confirm(self, code: str) -> dict:
        return self._request("POST", "/auth/mfa/confirm", auth=True, json={"code": code})

    def search_destinations(self, q=None, tag=None, region=None, max_cost=None) -> list[dict]:
        params = {k: v for k, v in {"q": q, "tag": tag, "region": region, "max_cost": max_cost}.items() if v is not None}
        return self._request("GET", "/destinations", params=params)

    def recommendations(self, limit: int = 10) -> list[dict]:
        return self._request("GET", "/recommendations", auth=True, params={"limit": limit})

    def create_itinerary(self, title: str, destinations: list[str], start_date: str, end_date: str) -> dict:
        return self._request(
            "POST", "/itineraries", auth=True,
            json={"title": title, "destinations": destinations, "start_date": start_date, "end_date": end_date},
        )

    def list_itineraries(self) -> list[dict]:
        return self._request("GET", "/itineraries", auth=True)

    def delete_itinerary(self, itinerary_id: str) -> None:
        self._request("DELETE", f"/itineraries/{itinerary_id}", auth=True)

    def submit_place(self, **fields) -> dict:
        return self._request("POST", "/places", auth=True, json=fields)

    def my_places(self) -> list[dict]:
        return self._request("GET", "/places/mine", auth=True)

    def submit_feedback(self, category: str, message: str, rating: Optional[int] = None) -> dict:
        return self._request("POST", "/feedback", auth=True, json={"category": category, "message": message, "rating": rating})

    def heartbeat(self, elapsed_seconds: int) -> dict:
        return self._request("POST", "/users/me/activity/heartbeat", auth=True, json={"elapsed_seconds": elapsed_seconds})

    def earnings(self) -> dict:
        return self._request("GET", "/users/me/earnings", auth=True)

    def request_payout(self) -> dict:
        return self._request("POST", "/users/me/payouts/request", auth=True)

    def list_notifications(self, unread_only: bool = False) -> list[dict]:
        return self._request("GET", "/notifications", auth=True, params={"unread_only": unread_only})

    def unread_notification_count(self) -> int:
        return self._request("GET", "/notifications/unread-count", auth=True)["unread_count"]

    def mark_notifications_read(self, ids: Optional[list[str]] = None, all_: bool = False) -> dict:
        return self._request("POST", "/notifications/mark-read", auth=True, json={"ids": ids, "all": all_})

    def delete_notification(self, notification_id: str) -> None:
        self._request("DELETE", f"/notifications/{notification_id}", auth=True)

    def delete_notifications(self, ids: Optional[list[str]] = None, all_: bool = False) -> dict:
        return self._request("POST", "/notifications/delete", auth=True, json={"ids": ids, "all": all_})
