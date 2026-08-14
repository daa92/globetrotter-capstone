# TiDB migration — how to apply

This swaps the JSON-file storage for TiDB (MySQL-compatible), keeping
every router/business-logic file untouched — only `app/storage.py` and
its plumbing changed.

## 1. Files to copy in (overwrite existing / add new)

| File in this zip | Goes to | Status |
|---|---|---|
| `app/config.py` | `app/config.py` | edited (added `DATABASE_URL`) |
| `app/db.py` | `app/db.py` | **new** — engine + generic `store` table |
| `app/storage.py` | `app/storage.py` | **rewritten** — same public API, now DB-backed |
| `app/__init__.py` | `app/__init__.py` | edited (calls `init_db()` on startup) |
| `app/schemas.py` | `app/schemas.py` | unchanged from earlier zip (included for completeness) |
| `app/routers/auth.py` | `app/routers/auth.py` | edited (fixed a token-format regression from the Brevo change — see note below) |
| `app/notifications/outbox.py` | `app/notifications/outbox.py` | unchanged from earlier zip |
| `requirements.txt` | `requirements.txt` | edited (added `sqlalchemy`, `pymysql`, `certifi`) |
| `.gitignore` | `.gitignore` | edited (removed `data/*.json` entries, ignores `*.db`) |
| `scripts/migrate_json_to_tidb.py` | `scripts/migrate_json_to_tidb.py` | **new** — one-time data migration |
| `tests/conftest.py` | `tests/conftest.py` | **rewritten** — tests now use an isolated SQLite DB instead of temp JSON files |
| `frontend/src/api/client.js` | same | unchanged from earlier zip |
| `frontend/src/pages/AdminDashboard.jsx` | same | unchanged from earlier zip |
| `frontend/src/pages/Verify.jsx` | same | unchanged from earlier zip |
| `frontend/src/components/layout/AnimatedRoutes.jsx` | same | unchanged from earlier zip |

**Side-fix included**: running the actual pytest suite against this
caught a real regression from the Brevo step (verification email format
broke a test helper that parses tokens) — fixed in this `auth.py`. All
87 tests pass with these files.

**SSL note**: `db.py`'s TLS args were adjusted to match your exact
`pymysql` version (1.2.0) and TiDB Cloud's own recommended connection
format — flat `ssl_ca` / `ssl_verify_cert` / `ssl_verify_identity` params
using `certifi`'s CA bundle (portable across hosts, unlike a fixed OS
path like `/etc/ssl/certs/ca-certificates.crt`).

## 2. Files/folders to DELETE locally

Dead code (confirmed nothing imports them) or made obsolete by the DB
migration:

```
rm -rf data/
rm app/models.py
rm app/auth.py
rm app/itineraries.py
rm app/destinations.py
rm app/recommendations.py
```

(Those last four are top-level files directly in `app/`, **not** the
ones in `app/routers/` — don't touch `app/routers/auth.py` etc.)

## 3. Your DATABASE_URL

Built from your TiDB Cloud connection panel:

```
mysql+pymysql://Ee79kA9198FPMyo.root:j63u5W0SlzylE27P@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/globetrotter
```

**Rotate this password after testing.** Go to TiDB Cloud → your cluster
→ Connect → "Reset Password", generate a new one, and update it
everywhere you've used the old one (just Render, in this case), since
this value passed through this chat.

## 4. Migrate your existing data (mainly your destinations catalog)

Locally, before deleting `data/` (do this from your own machine, not
Render — Render's shell doesn't have your local `data/` folder):

```bash
export DATABASE_URL="mysql+pymysql://Ee79kA9198FPMyo.root:j63u5W0SlzylE27P@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/globetrotter"
pip install -r requirements.txt
python -m scripts.migrate_json_to_tidb
```

This reads whatever's in your local `data/*.json` and loads it into
TiDB. I tested this script's logic end-to-end (against SQLite, same code
path) — it correctly migrated a 20-destination catalog from your repo.
Only `destinations.json` is likely to exist in your local clone; anything
else (users, itineraries) that only ever lived on Render's ephemeral
disk is gone regardless — expected, not something this script can fix.

If you skip this step, your `/destinations` endpoint will just return an
empty list until you run it (or manually re-add destinations).

## 5. Commit and push

```bash
git checkout ICTU20241556
git add -A
git commit -m "Migrate storage from JSON files to TiDB; remove dead legacy modules"
git push origin ICTU20241556
```

## 6. Set DATABASE_URL on Render

Render → your service → Environment → add `DATABASE_URL` with the same
value from step 3. Save (triggers redeploy).

On startup, the app automatically creates the `store` table if it
doesn't already exist (`init_db()` runs in the FastAPI lifespan) — no
manual schema step needed on Render's side.

## 7. Verify after deploy

- Check Render's **Events/Logs** tab for the new deploy — if `init_db()`
  or the DB connection fails, you'll see it there immediately (likely as
  an `OperationalError` or SSL-related error on startup).
- Hit `GET https://<your-backend>/destinations` — should return your
  migrated catalog if you ran step 4.
- Register a fresh test account, then trigger a Render restart/redeploy
  and confirm the account still exists afterward — that's the actual
  point of this whole migration.

---

Everything from the previous zip (admin dashboard, Brevo verification)
still applies on top of this — this zip is additive, not a replacement,
except where the table above says "edited"/"rewritten".
