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
│   ├── logo/                  ← YOUR LOGO GOES HERE (see public/logo/README.md)
│   │   ├── logo-full.svg          full wordmark, used in navbar + footer
│   │   ├── logo-full-dark.svg     (add this) dark-mode variant
│   │   ├── favicon.svg            icon-only mark, browser tab
│   │   ├── favicon.png            (add this) 512×512 PNG fallback
│   │   └── og-image.png           (add this) 1200×630 social share preview
│   └── ... any other static file that needs a stable, predictable URL
├── src/
│   ├── assets/
│   │   ├── images/
│   │   │   ├── hero/           background/hero imagery for the homepage
│   │   │   └── illustrations/  empty-state art, 404 page, how-to-use step graphics
│   │   └── videos/              hero background loop, how-to-use demo clips
│   ├── i18n/                    English + French strings (locales/en.json, fr.json)
│   ├── context/ThemeContext.jsx dark/light mode, persisted to localStorage
│   ├── components/layout/       Navbar, Footer, Layout wrapper
│   └── pages/                   one file per route (currently placeholders —
│                                  real design pass comes next)
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

This is the **scaffold**: routing, dark/light, EN/FR, and the logo/asset
pipeline all work end-to-end (verified with `npm run build` and a live
dev server), but every page is a placeholder. The real visual design —
hero section, destination cards, the map, auth forms, profile portal,
how-to-use — comes next, once the brand direction (colors/type derived
from your logo) is locked in.
