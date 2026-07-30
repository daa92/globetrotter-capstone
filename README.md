# GT — GlobeTrotter

Discover, plan, and share trips across Cameroon. GT is a capstone project
(ICTU) being built in phases — from a monolith to a resilient, cloud-native,
multi-platform product — and doubling as a real commercial MVP.

**Current status: Phase 1 — Monolith.**

---

## Phase 1 scope

A single FastAPI service, JSON-file storage, JWT auth (access token +
httpOnly refresh cookie), optional TOTP-based MFA, and the core product
surface: destination search over a real Cameroon catalogue, content-based
recommendations, itinerary planning, a self-service user portal, a
user-submitted "advertise a place" flow with admin approval, and feedback
intake.

This is a **deliberately simple, single-process architecture.** It will hit
real limits as usage grows (see "Known Limitations" below) — that's expected
and by design; Phase 2 decomposes it into services, Phase 3 containerizes and
deploys it to the cloud, and Phase 4 adds resilience (caching, queues,
circuit breakers, tracing).

## Project structure

```
.
├── app/
│   ├── __init__.py          # FastAPI app factory (middleware + routers)
│   ├── main.py               # Entry point (uvicorn)
│   ├── config.py             # Environment-driven settings
│   ├── security.py           # Password hashing, JWT, MFA (TOTP)
│   ├── storage.py            # JSON-file persistence layer
│   ├── schemas.py            # Pydantic request/response models
│   ├── dependencies.py       # get_current_user / get_current_admin
│   └── routers/
│       ├── auth.py           # register, login, MFA, refresh, logout
│       ├── users.py          # profile portal (view/update/delete account)
│       ├── destinations.py   # search the Cameroon catalogue
│       ├── recommendations.py# content-based recommendation engine v1
│       ├── itineraries.py    # trip planning CRUD
│       ├── places.py         # user-submitted place "advertisements"
│       └── feedback.py       # feedback intake (feeds admin dashboard later)
├── data/
│   ├── destinations.json     # seed catalogue — real Cameroon places
│   ├── users.json            # runtime data, gitignored
│   ├── itineraries.json      # runtime data, gitignored
│   ├── places.json           # runtime data, gitignored
│   └── feedback.json         # runtime data, gitignored
├── tests/                    # pytest — unit/integration tests
├── testing/simulation/       # Locust load-test + chaos probe (dev-only, never shipped)
├── cli/                      # `gt` command-line client (separate installable package)
├── Dockerfile                # production image (lean, no dev/test deps)
├── Dockerfile.dev             # dev image (hot reload, includes dev deps)
├── docker-compose.yml
├── requirements.txt           # production dependencies
└── requirements-dev.txt       # + pytest, httpx, locust
```

## REST API (Phase 1)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create an account (unverified — deleted after 30 min if not verified) |
| POST | `/auth/register/phone` | No | Register with phone + pseudo + password instead of email |
| POST | `/auth/verify` | No | Verify a new account with the token/code sent at registration (email or SMS) |
| POST | `/auth/login` | No | Login (requires a verified account); returns tokens, or an MFA challenge if enabled |
| POST | `/auth/google` | No | Sign in/register via Google ID token (see "Google Sign-In" below) |
| POST | `/auth/password-reset/request` | No | Request a reset code (sent via SMS or email, whichever the account has) |
| POST | `/auth/password-reset/confirm` | No | Confirm with the code + a new password |
| POST | `/auth/mfa/setup` | Yes | Generate a TOTP secret + QR provisioning URI |
| POST | `/auth/mfa/confirm` | Yes | Confirm a TOTP code, enabling MFA |
| POST | `/auth/mfa/disable` | Yes | Disable MFA |
| POST | `/auth/refresh` | Cookie | Exchange refresh cookie for a new access token |
| POST | `/auth/logout` | Cookie | Clear the refresh cookie |
| GET | `/users/me` | Yes | View your profile |
| PATCH | `/users/me` | Yes | Update email / preferences / profile picture |
| DELETE | `/users/me` | Yes | Delete your account |
| GET | `/destinations` | No | Search (`q`, `tag`, `region`, `max_cost`) |
| GET | `/destinations/{id}` | No | Get one destination |
| GET | `/recommendations` | Yes | Personalised recommendations |
| POST | `/itineraries` | Yes | Create an itinerary |
| GET | `/itineraries` | Yes | List your itineraries |
| DELETE | `/itineraries/{id}` | Yes | Delete your itinerary |
| POST | `/places` | Yes | Submit/advertise a new place (pending review) |
| GET | `/places/mine` | Yes | List your submissions |
| GET | `/places/pending` | Admin | List pending submissions |
| POST | `/places/{id}/approve` | Admin | Approve + publish a submission |
| POST | `/places/{id}/reject` | Admin | Reject a submission |
| POST | `/feedback` | Yes | Submit feedback |
| GET | `/feedback` | Admin | List all feedback |
| POST | `/users/me/activity/heartbeat` | Yes | Report active usage time (drives daily earnings) |
| GET | `/users/me/earnings` | Yes | Full earnings breakdown: usage days, referrals, feedback, totals in USD/FCFA, payout eligibility |
| POST | `/users/me/payouts/request` | Yes | Request a payout (requires $30+ balance, 5+ referrals, 5+ good feedback) |
| GET | `/admin/payouts` | Admin | List payout requests (`?status_filter=pending\|approved\|rejected\|all`) |
| POST | `/admin/payouts/{id}/approve` | Admin | Approve a payout request |
| POST | `/admin/payouts/{id}/reject` | Admin | Reject a payout request |
| GET | `/notifications` | Yes | List your notifications (`?unread_only=true`) |
| GET | `/notifications/unread-count` | Yes | Just the unread count, for a bell badge |
| POST | `/notifications/mark-read` | Yes | `{"ids": [...]}` or `{"all": true}` |
| DELETE | `/notifications/{id}` | Yes | Delete a single notification |
| POST | `/notifications/delete` | Yes | Bulk delete: `{"ids": [...]}` or `{"all": true}` |
| POST | `/admin/notifications/send` | Admin | Push a notification to specific users or `broadcast: true` for everyone; `also_email: true` to also email |
| GET | `/health` | No | Liveness probe |

Interactive docs (auto-generated): `http://localhost:8000/docs`

Protected routes expect `Authorization: Bearer <access_token>`.

## Running locally

```bash
# 1. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # includes prod deps + pytest/locust

# 2. Configure environment
cp .env.example .env
# edit .env — at minimum set a real SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Run
uvicorn app.main:app --reload --port 8000
```

## Running with Docker

```bash
docker compose up --build
```

The `data/` directory is mounted so JSON files persist between runs. This
uses `Dockerfile.dev` (hot reload). The production `Dockerfile` is smaller
and excludes tests/simulation tooling entirely — build it directly for
anything resembling a deploy:

```bash
docker build -t gt-api .
docker run -p 8000:8000 --env-file .env gt-api
```

## Testing

```bash
pytest -v
```

## Manual testing

There are two ways to poke at the API by hand: the auto-generated Swagger UI
(fastest, no setup), or `curl` (useful for scripting, or for testing cookie
behavior which Swagger UI hides from you).

### Option A — Swagger UI (recommended for quick manual checks)

With the server running (`uvicorn app.main:app --reload`), open:

```
http://localhost:8000/docs
```

Every endpoint is listed, with example request bodies and a "Try it out"
button. For protected routes:
1. Call `POST /auth/register`, then `POST /auth/login` via "Try it out".
2. Copy the `access_token` from the response.
3. Click the green **Authorize** button at the top of the page, paste the
   token (just the token, Swagger adds the `Bearer` prefix), and confirm.
4. Every protected route ("Try it out") now sends that token automatically.

An alternative, still no-install option: `http://localhost:8000/redoc` gives
you a read-only, nicely laid-out version of the same spec (no "Try it out"
buttons — good for just browsing the contract).

### Option B — curl, full walkthrough

This mirrors exactly what the automated tests check, but lets you see the
raw JSON and the refresh cookie yourself.

```bash
# 1. Register — creates an UNVERIFIED account and "sends" a verification
#    email (in dev, this just gets logged to data/outbox.json — see
#    "Account verification" below). Unverified accounts are deleted after
#    30 minutes.
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"jane_doe","email":"jane@example.com","password":"TripLover1","preferences":["beach","culture"]}'

# 2. Grab the verification token from the outbox and verify
TOKEN_LINE=$(python3 -c "
import json
outbox = json.load(open('data/outbox.json'))
msg = [m for m in outbox if m['to']=='jane@example.com'][-1]
print(msg['body'].split('token: ')[1].split(chr(10))[0])
")
curl -s -X POST http://localhost:8000/auth/verify -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN_LINE\"}"

# 3. NOW login works — save cookies to a jar so we can test /auth/refresh afterwards
LOGIN_RESP=$(curl -s -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"jane_doe","password":"TripLover1"}')
echo "$LOGIN_RESP"
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 4. Call a protected route with the access token
curl -s http://localhost:8000/users/me -H "Authorization: Bearer $TOKEN"

# 5. Search destinations (public, no token needed)
curl -s "http://localhost:8000/destinations?tag=beach"

# 6. Get personalised recommendations
curl -s http://localhost:8000/recommendations -H "Authorization: Bearer $TOKEN"

# 7. Create an itinerary
curl -s -X POST http://localhost:8000/itineraries -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Coastal weekend","destinations":["limbe-botanic-beach"],"start_date":"2026-09-01","end_date":"2026-09-03"}'

# 8. Submit a place ("advertise" it) — lands as status=pending
curl -s -X POST http://localhost:8000/places -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Falls","region":"West","tags":["waterfall","nature"],"description":"A beautiful hidden waterfall near a small village, great for a day trip.","image_url":"https://example.com/falls.jpg","latitude":5.5,"longitude":10.5,"avg_cost_fcfa":2000}'

# 9. Submit feedback
curl -s -X POST http://localhost:8000/feedback -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"suggestion","message":"Would love a filter by season.","rating":5}'

# 10. Refresh the access token using the httpOnly cookie saved in step 3
curl -s -b cookies.txt -X POST http://localhost:8000/auth/refresh

# 11. Logout — clears the refresh cookie server-side
curl -s -b cookies.txt -X POST http://localhost:8000/auth/logout
```

`-c cookies.txt` tells curl to *save* cookies from the response; `-b cookies.txt`
tells it to *send* them on the next request — that's how step 10 gets the
refresh cookie that step 3 received, exactly like a browser would.

### Account verification (dev/local)

There's no real email/SMS provider wired in yet (that needs paid/free-tier
credentials from a real provider — deliberately not hardcoded into this
repo). In dev, "sending" a verification message just appends it to
`data/outbox.json`, which is exactly what the script above reads from —
open that file yourself after registering to see it, or use the snippet
above to extract the token programmatically.

**Unverified accounts are deleted automatically 30 minutes after
registration** — this runs as a background task inside the API process
(see `app/cleanup.py`), checked every 60 seconds. To see it happen faster
than waiting 30 minutes, either lower `UNVERIFIED_ACCOUNT_TTL_MINUTES` in
`.env` temporarily, or call the purge function directly in a Python shell:

```bash
python3 -c "from app.cleanup import purge_unverified_users; print(purge_unverified_users())"
```

### Testing MFA manually

MFA needs a real TOTP code, which needs the same secret your authenticator
app would use. `pyotp` (already in `requirements-dev.txt`) can generate one
from the terminal instead of scanning a QR code:

```bash
# after logging in and getting $TOKEN as above:

# 1. Start MFA setup — returns a secret + provisioning URI
SETUP_RESP=$(curl -s -X POST http://localhost:8000/auth/mfa/setup -H "Authorization: Bearer $TOKEN")
echo "$SETUP_RESP"
SECRET=$(echo "$SETUP_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['secret'])")

# 2. Generate the current 6-digit code for that secret (what a phone app would show)
CODE=$(python3 -c "import pyotp; print(pyotp.TOTP('$SECRET').now())")

# 3. Confirm it — MFA is now enabled on the account
curl -s -X POST http://localhost:8000/auth/mfa/confirm -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d "{\"code\":\"$CODE\"}"

# 4. Logging in now returns a challenge instead of tokens, until you add mfa_code
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"username":"jane_doe","password":"TripLover1"}'
# => {"mfa_required":true,"username":"jane_doe"}

# 5. Login again, this time including a fresh code
FRESH_CODE=$(python3 -c "import pyotp; print(pyotp.TOTP('$SECRET').now())")
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d "{\"username\":\"jane_doe\",\"password\":\"TripLover1\",\"mfa_code\":\"$FRESH_CODE\"}"
```

If you want to actually scan a QR code with a real phone authenticator app
instead, paste the `provisioning_uri` from step 1 into any free QR generator
website, or generate one locally: `pip install qrcode` then
`python3 -c "import qrcode; qrcode.make('PASTE_URI_HERE').save('mfa.png')"`
and open `mfa.png`.

### Testing admin-only routes manually

There's no signup flow for admins yet in Phase 1 (intentional — admin
promotion will go through a proper process later). For now, to test
`GET /places/pending`, `POST /places/{id}/approve`, or `GET /feedback`
locally: stop the server, open `data/users.json`, find your test user, and
change `"is_admin": false` to `"is_admin": true`, then restart the server.
Never do this in a deployed/shared environment — it's a local-only shortcut.

## CLI client

A full command-line client (`gt`) lives in `cli/` — register, login, search
destinations, get recommendations, plan itineraries, advertise places, and
submit feedback, all from the terminal. See [`cli/README.md`](cli/README.md)
for install and usage. Quick start:

```bash
cd cli && pip install -e . && gt --help
```

## Robustness / load simulation

See [`testing/simulation/README.md`](testing/simulation/README.md). Short version:

```bash
# Load test (many concurrent simulated users)
locust -f testing/simulation/locustfile.py --host http://localhost:8000

# Malformed/adversarial input probe
python testing/simulation/chaos_probe.py --host http://localhost:8000
```

Neither tool is imported by app code or included in the production Docker
image — verified via `.dockerignore` and the separate `Dockerfile`.

## Phone registration & password recovery

`POST /auth/register/phone` is the phone + pseudo + password alternative
to email registration — same unverified-account rules apply (30-minute
cleanup, same `/auth/verify` endpoint, since verification is
channel-agnostic and just matches a token regardless of how it was sent).
The only difference is the verification code arrives via SMS (logged to
`data/outbox.json` in dev, same as email — see "Account verification"
above) instead of email.

Password recovery (`/auth/password-reset/request` + `/auth/password-reset/confirm`)
works for **any** account type — email, phone, or Google:
- **Request** takes just a `username` and always returns the same generic
  response whether or not that username exists, so this endpoint can't be
  used to enumerate real accounts. If the account exists, a code is sent
  to whatever it has on file (SMS for phone accounts, email otherwise).
- **Confirm** takes the code + a new password, validates it hasn't expired
  (`PASSWORD_RESET_TOKEN_TTL_MINUTES`, default 30), and updates the
  password. A "your password was changed" notification fires afterward
  (category `security`) so a legitimate user notices if this wasn't them.
- **A Google-only account** (no local password set) can go through this
  same flow to set a local password for the first time — a useful side
  effect of reusing one mechanism rather than building a separate one.

## Google Sign-In

`POST /auth/google` accepts `{"id_token": "..."}` — the credential Google's
"Sign In With Google" button hands your frontend after the user clicks and
agrees. No redirect, no server-side code exchange, and **no Client Secret
needed** — verification is just a signature/audience check against
Google's public keys (see `app/google_oauth.py`).

Setup:
1. Create a free Google Cloud project and OAuth Client ID (Web application
   type, no billing account needed) — full walkthrough available on
   request, or see [Google's guide](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid).
2. Set `GOOGLE_CLIENT_ID` in `.env`. Leaving it blank makes the endpoint
   return a clear `501` rather than trying and failing.
3. On the frontend, render Google's Sign-In button (loads `accounts.google.com`'s
   script), which calls back with the credential — POST that straight to
   `/auth/google`.

Behavior:
- **New Google sign-in, no matching account** → creates one, auto-verified
  (Google already confirmed the email, so the 30-minute verification
  window doesn't apply), with a username derived from the email's local
  part (a numeric suffix is appended on collision, e.g. `alice` → `alice1`).
- **Google sign-in matching an existing account's email** → logs into that
  same account and links it (no duplicate accounts by email).
- **That account has MFA enabled** → same challenge/response pattern as
  password login: first call returns `{"mfa_required": true}`, retry with
  `mfa_code` included.
- **A Google-only account (no local password set) tries `/auth/login`
  with a password** → rejected with the same generic "invalid username or
  password" as any other wrong attempt — never reveals that the account
  exists or how it was created.
- A network failure reaching Google (rare, but real) returns `503`, kept
  distinct from a genuinely invalid/expired token (`401`) — verified this
  by actually triggering the real verification path against Google's live
  endpoint and confirming the error type.

## Notifications

The in-app notification center (`app/routers/notifications.py`) is deliberately
separate from `app/notifications/outbox.py` (the raw email/SMS channel) —
a single event often writes to both: an in-app notification the user sees
immediately, and optionally an email if they have one and it's warranted.

- **Automatic notifications** already fire from: a referral getting credited,
  a payout being approved/rejected, and a place submission being approved/
  rejected. Wiring a new event in is one call to
  `create_notification(username, title, message, category)`.
- **Ownership is enforced server-side, not trusted from the client.** Bulk
  mark-read/delete accept a list of IDs, but the route always intersects
  that list with the caller's *own* notification IDs first — passing
  someone else's ID just gets silently ignored rather than acted on. This
  is tested directly (`test_cannot_delete_or_read_someone_elses_notification`).
- **Admin broadcast** (`broadcast: true`) sends to literally every user —
  there's no pagination/throttling yet, fine at Phase 1 scale, worth
  revisiting once the user base is large enough for that to matter.

## Earnings / referrals / payouts

Implements: $0.50/day for 5+ minutes of active use, $0.25 per verified
referral, and a payout system with a $30 minimum requiring 5 referrals +
5 feedback submissions rated 4-5 stars.

- **Activity tracking**: the frontend/CLI should call
  `POST /users/me/activity/heartbeat` roughly every 60–90 seconds while
  the user is actively using the app, with `elapsed_seconds` since the
  last call. A single call can't add more than
  `MAX_HEARTBEAT_INCREMENT_SECONDS` (90s default) — this stops a client
  from just claiming a huge jump in one request.
- **Referral crediting happens at verification, not registration** — an
  unverified referral would just get deleted by the 30-minute cleanup job
  anyway, so this doubles as the anti-fake-signup gate for the referral
  bonus.
- **Nothing is stored as a running balance.** Every number in
  `GET /users/me/earnings` is computed fresh from the underlying activity/
  referral/feedback/payout records every time. Given Phase 1's JSON
  storage has no transactions, a stored balance could drift from the
  records it's supposed to represent; computing on read avoids that whole
  class of bug.
- **FCFA conversion** uses a fixed rate (`FCFA_PER_USD` in `.env`, default
  610) rather than a live exchange-rate API — XAF is pegged to the EUR,
  not freely floating, so this is normal practice, not a shortcut.
- **No real payment processor is wired in.** `POST /users/me/payouts/request`
  creates a request an admin approves/rejects via
  `POST /admin/payouts/{id}/approve` — actually moving money to a user
  (Mobile Money, bank transfer, etc.) is a manual step for now, since
  integrating a real payment processor needs a paid account you'll need
  to set up yourself when you're ready to launch.

## Security notes (Phase 1)

- Passwords hashed with bcrypt (via passlib), never stored or returned in plaintext.
- Access tokens are short-lived JWTs (15 min default) sent via `Authorization` header.
- Refresh tokens are longer-lived JWTs stored in an **httpOnly, `SameSite=Lax` cookie** — never exposed to JS.
- MFA via TOTP (Google Authenticator / Authy compatible), optional per-user.
- Coordinates on user-submitted places are bounds-checked to roughly Cameroon's borders.
- `SECRET_KEY` has a deliberately unusable default; the app should be considered insecure until it's overridden.

## Known limitations (Phase 1, by design)

This is the point of Phase 1 — experience these first-hand:
- JSON-file storage has no real concurrency control beyond a coarse in-process lock; it will not survive multiple server processes/replicas.
- No database, no indexing, no transactions.
- Single process — one bug can take down the whole API.
- No caching, no message queue, no circuit breakers (arriving in Phase 4).
- No real email/SMS provider — verification and (future) password-reset messages are logged to `data/outbox.json` instead of actually sent. Swapping in a real provider (see `app/notifications/outbox.py`) is a small, isolated change whenever you're ready to pay for one (or use a free tier like Mailtrap/SendGrid for email, or a free-tier SMS API).

## Roadmap

- **Phase 2 — Microservices**: split into User / Itinerary / Recommendation services behind an API Gateway, plus new Chat and Admin/Analytics services.
- **Phase 3 — Cloud deployment**: containerized, load-balanced, autoscaled.
- **Phase 4 — Resilience**: Redis caching, RabbitMQ queues, circuit breakers, health checks, OpenTelemetry/Jaeger tracing — the backbone of the admin observability dashboard.
- **Phase 5 — Multi-platform + polish**: Flutter mobile app, glassmorphism design pass, dark/light + EN/FR, collaborative-filtering recommendations v2.
