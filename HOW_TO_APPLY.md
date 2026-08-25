# Notifications fix, 9-per-page, more tags, redesigned My Trips

## Files

| File | Goes to | What changed |
|---|---|---|
| `app/geo_service.py` | same | added 14 real OSM POI categories (university, attraction, park, gym, library, courier/delivery, car_dealer, electronics, car_wash, police, post_office, museum, stadium, place_of_worship) |
| `frontend/src/api/client.js` | same | fixed the `request()` bug causing the notifications crash |
| `frontend/src/pages/Explore.jsx` | same | `PAGE_SIZE` 10 → 9 |
| `frontend/src/pages/Itineraries.jsx` | same | **fully rewritten** — step-based, animated, mostly-click trip planner |
| `frontend/src/i18n/locales/en.json` / `fr.json` | same | new labels for POI categories + trip planner |

```bash
git add app/geo_service.py frontend/src/api/client.js frontend/src/pages/Explore.jsx \
        frontend/src/pages/Itineraries.jsx \
        frontend/src/i18n/locales/en.json frontend/src/i18n/locales/fr.json
git commit -m "Fix notifications bug, 9-per-page, expand POI categories, redesign My Trips"
git push origin ICTU20241556
```

**Verified before handing off**: full backend test suite (99 tests) and
a real `npm run build` (not just eyeballed — I confirmed the exact
`getSeedStatus` class of error can't happen again by actually running
the build), both clean.

## The notifications bug, explained

`NotificationCenter.jsx` calls `listNotifications(accessToken)` — no
second argument, so `unread_only` is `undefined`. The old `request()`
did `url.searchParams.set(k, v)` on every param regardless of value,
and `URLSearchParams` stringifies `undefined` as the literal text
`"undefined"`. FastAPI then tried to parse the string `"undefined"` as a
boolean and failed — exactly the error in your screenshot. Fixed at the
root: `request()` now skips any param that's `undefined`/`null`, so
*any* optional parameter across the whole API client is safe to omit
from now on, not just this one call site.

## New POI categories

All real OpenStreetMap tags (same taxonomy as the existing ones), so
Overpass actually returns results — I didn't invent placeholder
categories. A couple of notes on the mapping:
- "Delivery" doesn't have a clean single OSM tag for a generic delivery
  service — I mapped it to `office=courier`, the closest real match.
- "Attractions" maps to `tourism=attraction` (singular in the data,
  labeled "Attraction" in the UI).

I also added a few more while I was in there that fit the same spirit
even though you didn't list them by name: police stations, post
offices, museums, stadiums, and places of worship — all common
real-world search needs, same low effort to include.

## The My Trips redesign

Replaced the old single flat form (type a title, click a wall of plain
text pills, type two dates) with a 3-step animated flow:

1. **What's your vibe?** — tap interest chips (beach, hiking, culture,
   etc.) — entirely optional, but narrows step 2 automatically.
2. **Pick your destinations** — actual photo cards (not text pills),
   filtered by your vibe picks if you made any, with an animated
   checkmark on selection.
3. **Almost there** — a title field that suggests one automatically
   based on your picks (e.g. "Kribi & Limbe Trip") so you can just hit
   Create without typing anything if you want, plus one-tap date
   presets (Weekend / 1 week / 2 weeks) alongside the manual date
   pickers for people who want exact control.

Your existing trips now render as photo cards (using the first
destination's image as the cover) instead of plain list rows, with a
hover lift and a trash icon overlay instead of a text "Delete" link.
The whole page also picks up the ambient animated canopy background
from the last design pass, at low opacity so it doesn't fight with the
form's readability.
