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
| POST | `/auth/register` | No | Create an account |
| POST | `/auth/login` | No | Login; returns tokens, or an MFA challenge if enabled |
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
# 1. Register
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"jane_doe","email":"jane@example.com","password":"TripLover1","preferences":["beach","culture"]}'

# 2. Login — save cookies to a jar so we can test /auth/refresh afterwards
LOGIN_RESP=$(curl -s -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"jane_doe","password":"TripLover1"}')
echo "$LOGIN_RESP"
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 3. Call a protected route with the access token
curl -s http://localhost:8000/users/me -H "Authorization: Bearer $TOKEN"

# 4. Search destinations (public, no token needed)
curl -s "http://localhost:8000/destinations?tag=beach"

# 5. Get personalised recommendations
curl -s http://localhost:8000/recommendations -H "Authorization: Bearer $TOKEN"

# 6. Create an itinerary
curl -s -X POST http://localhost:8000/itineraries -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Coastal weekend","destinations":["limbe-botanic-beach"],"start_date":"2026-09-01","end_date":"2026-09-03"}'

# 7. Submit a place ("advertise" it) — lands as status=pending
curl -s -X POST http://localhost:8000/places -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Falls","region":"West","tags":["waterfall","nature"],"description":"A beautiful hidden waterfall near a small village, great for a day trip.","image_url":"https://example.com/falls.jpg","latitude":5.5,"longitude":10.5,"avg_cost_fcfa":2000}'

# 8. Submit feedback
curl -s -X POST http://localhost:8000/feedback -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"suggestion","message":"Would love a filter by season.","rating":5}'

# 9. Refresh the access token using the httpOnly cookie saved in step 2
curl -s -b cookies.txt -X POST http://localhost:8000/auth/refresh

# 10. Logout — clears the refresh cookie server-side
curl -s -b cookies.txt -X POST http://localhost:8000/auth/logout
```

`-c cookies.txt` tells curl to *save* cookies from the response; `-b cookies.txt`
tells it to *send* them on the next request — that's how step 9 gets the
refresh cookie that step 2 received, exactly like a browser would.

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

## Roadmap

- **Phase 2 — Microservices**: split into User / Itinerary / Recommendation services behind an API Gateway, plus new Chat and Admin/Analytics services.
- **Phase 3 — Cloud deployment**: containerized, load-balanced, autoscaled.
- **Phase 4 — Resilience**: Redis caching, RabbitMQ queues, circuit breakers, health checks, OpenTelemetry/Jaeger tracing — the backbone of the admin observability dashboard.
- **Phase 5 — Multi-platform + polish**: Flutter mobile app, glassmorphism design pass, dark/light + EN/FR, collaborative-filtering recommendations v2.
