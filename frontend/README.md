# GT Frontend

React + Vite + Tailwind, talking to the FastAPI backend over REST.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_URL if the backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`.

## Where things go

```
frontend/
├── public/
│   ├── logo/                     ← your real logo (see public/logo/README.md)
│   │   ├── logo-icon.png             master 1024×1024 source
│   │   ├── logo-full.png             navbar/footer mark
│   │   ├── favicon.png               browser tab icon
│   │   └── og-image.png              social share preview
│   └── media/hero/                ← homepage hero image/video (see its README.md)
├── src/
│   ├── api/client.js               EVERY backend call goes through here — one
│   │                                place for credentials/headers/error shape
│   ├── context/
│   │   ├── AuthContext.jsx         session state (user, access token), wraps
│   │   │                            every auth API call
│   │   └── ThemeContext.jsx        dark/light mode, persisted to localStorage
│   ├── components/
│   │   ├── auth/                   GoogleSignInButton, MfaChallengeForm —
│   │   │                            shared by Login and (later) Register
│   │   └── layout/                 Navbar (auth-aware), Footer, Layout, Hero
│   ├── i18n/                       English + French strings
│   ├── assets/                     page-specific images/videos (imported, not
│   │                                referenced by URL — see below)
│   └── pages/                      one file per route — Login/Register/
│                                     PasswordReset are real; the rest are
│                                     still placeholders (see "Current status")
├── scripts/verify_auth_flow.mjs    contract check against the real backend,
│                                     no browser needed (see "Verifying the
│                                     connection" below)
├── package.json
├── vite.config.js
└── tailwind.config.js
```

### `public/` vs `src/assets/` — what's the difference?

- **`public/`** — files here are copied as-is and get a stable URL
  (`/logo/logo-full.svg`). Use this for anything referenced by a fixed
  path outside of React code: the favicon, the logo, `robots.txt`,
  social preview images.
- **`src/assets/`** — files here are `import`ed directly into components
  (e.g. `import hero1 from "../assets/images/hero/hero-1.jpg"`), so Vite
  can optimize/hash/bundle them. Use this for images and videos that are
  part of a specific page's design.

### What does NOT belong in this frontend at all

Destination photos (Limbe beach, Mount Cameroon, user-submitted place
photos, etc.) are **never** stored here — they come from the backend as
URLs (`image_url` field on every destination/place). The frontend just
renders whatever URL the API returns; don't add destination photos to this
repo.

## Stack

- **React Router** for navigation
- **react-i18next** for English/French
- **Tailwind** with `darkMode: "class"`, toggled via `ThemeContext`
- **Framer Motion** — installed, not yet used; reserved for the animation
  pass once the visual design is locked in
- **Leaflet + react-leaflet** — installed, not yet used; will power the
  Cameroon destinations map

## Current status

**Backend and frontend are genuinely connected**, page by page, each
verified two ways: a real headless-DOM test that actually renders the
React components and clicks through them (`npm run test:auth-forms`,
`npm run test:explore`) against the real backend, plus manual dev-server
checks.

- **Auth**: register (email or phone), inline verification, login, MFA
  challenge, Google Sign-In, password reset, logout, silent session
  restore on page load.
- **Explore**: live search + autocomplete against the curated catalogue,
  a multi-criteria filter panel (tags, budget — defaults to unlimited,
  not capped — and a "near me" distance filter), **live nearby-place
  search** via OpenStreetMap (restaurants, airports, hotels, fast food,
  fuel stations, and 12 more categories — fetched from the backend so the
  list never drifts out of sync), a **place detail modal** (click any
  card: full description + photo — Wikipedia-backed for live places,
  curated content for the seed catalogue), and **pagination** once
  results exceed 10.
- **Recommendations / Itineraries**: connected, live.
- **Profile portal**: view/edit preferences + profile picture, delete
  account, an earnings dashboard, and a full notification center.
- **Page transitions and card animations** throughout, via framer-motion.

## Testing — two real, running-code test suites

Unlike `scripts/verify_*.mjs` (which only ever call `fetch()` directly),
these actually render the React components in jsdom and interact with
them like a user would — this is what caught a real bug (every form's
`<label>` was never associated with its `<input>`) that a pure-fetch
simulation couldn't have found.

```bash
uvicorn app.main:app --port 8000 &   # backend must be running
cd frontend
npm run test:auth-forms               # register + login, filled and submitted for real
npm run test:explore                  # catalogue load, pagination, place detail modal, live POI categories
```

## Known, tracked (not fixed this pass)

- `npm audit` flags `react-router-dom` (moderate, open-redirect related)
  and `esbuild`'s dev server (moderate, dev-only — doesn't affect the
  built app). Both need a breaking major-version bump to fully resolve;
  deliberately not force-upgraded mid-feature-work.
- Production bundle is ~960KB — Leaflet + Recharts + framer-motion in one
  chunk. Worth code-splitting by route via `React.lazy()` later.

## Verifying the connection

Two things you can run yourself:

```bash
# 1. Contract check — replicates exactly what the React code does
#    (same endpoints, same payload shapes, same cookie handling) against
#    a real running backend, without needing a browser:
uvicorn app.main:app --port 8000 &     # from the project root, in another terminal
cd frontend && node scripts/verify_auth_flow.mjs
node scripts/verify_app_flow.mjs        # destinations, recommendations, itineraries, earnings, notifications

# 2. The real thing — run both dev servers and click through it yourself:
uvicorn app.main:app --port 8000 &     # project root
npm run dev                             # frontend/
# open http://localhost:5173/register
```

Re-run these any time you change `src/api/client.js` or a component that
calls it — they'll catch a payload/endpoint mismatch immediately instead
of you finding out in the browser's network tab.

## Architecture: how auth state actually works

- **Access token**: held only in React state (`AuthContext`), never in
  `localStorage`/`sessionStorage`. It's short-lived (15 min) by design.
- **Refresh token**: an httpOnly cookie the browser manages automatically
  — JavaScript can't read it (that's the point), and every `fetch` call
  in `src/api/client.js` sets `credentials: "include"` so it's sent/received
  correctly across the frontend's origin (`localhost:5173`) and the
  backend's (`localhost:8000`). CORS is configured on the backend to
  allow exactly this (see `app/config.py`'s `CORS_ORIGINS` — verified live
  with a real preflight request, not assumed).
- **On page load**: `AuthProvider` silently calls `POST /auth/refresh`.
  If the httpOnly cookie is still valid, this transparently logs the user
  back in without them re-entering credentials — same behavior as staying
  logged into any website. If not, they're just logged out, no error shown.

## Environment variables

```bash
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=              # same value as the backend's GOOGLE_CLIENT_ID
```

`VITE_GOOGLE_CLIENT_ID` is a public identifier, not a secret — safe to
expose to the browser. Leaving it blank hides the Google Sign-In button
entirely (`GoogleSignInButton.jsx` renders nothing) rather than showing a
button guaranteed to fail.

