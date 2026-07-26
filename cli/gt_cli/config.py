"""
gt_cli/config.py

Where the CLI keeps its local state between invocations. Every `gt`
command is a fresh process, so unlike a browser (which just holds the
refresh cookie in memory), we have to persist it to disk ourselves.

Everything lives under ~/.gt/:
    ~/.gt/config.json   -> api_url, username, access_token, access_token_expires_at
    ~/.gt/cookies.txt    -> the httpOnly refresh-token cookie, in Netscape/LWP
                            cookiejar format, so `requests` can load/save it
                            natively via http.cookiejar.LWPCookieJar

Both files are created with 0600 permissions (owner read/write only) since
they hold live credentials — the same reason a browser marks that cookie
httpOnly, we make sure only you can read it off disk.
"""
import http.cookiejar
import json
import os
import stat
from pathlib import Path
from typing import Optional

GT_DIR = Path(os.environ.get("GT_CONFIG_DIR", Path.home() / ".gt"))
CONFIG_FILE = GT_DIR / "config.json"
COOKIE_FILE = GT_DIR / "cookies.txt"

DEFAULT_API_URL = os.environ.get("GT_API_URL", "http://localhost:8000")


def _ensure_dir() -> None:
    GT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(GT_DIR, stat.S_IRWXU)  # 0700 — owner only
    except OSError:
        pass  # best-effort; some filesystems (e.g. some CI runners) disallow this


def _secure_file(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600 — owner read/write only
    except OSError:
        pass


def load_config() -> dict:
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return {"api_url": DEFAULT_API_URL}
    with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("api_url", DEFAULT_API_URL)
    return data


def save_config(data: dict) -> None:
    _ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    _secure_file(CONFIG_FILE)


def clear_session() -> None:
    """Used by `gt auth logout` — wipes local tokens without touching api_url."""
    config = load_config()
    for key in ("username", "access_token", "access_token_expires_at"):
        config.pop(key, None)
    save_config(config)
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()


def get_cookie_jar() -> http.cookiejar.LWPCookieJar:
    _ensure_dir()
    jar = http.cookiejar.LWPCookieJar(str(COOKIE_FILE))
    if COOKIE_FILE.exists():
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except (OSError, http.cookiejar.LoadError):
            pass  # corrupt/empty cookie file — proceed with an empty jar
    return jar


def save_cookie_jar(jar: http.cookiejar.LWPCookieJar) -> None:
    jar.save(ignore_discard=True, ignore_expires=True)
    _secure_file(COOKIE_FILE)


def get_access_token() -> Optional[str]:
    return load_config().get("access_token")
