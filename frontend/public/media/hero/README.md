# Homepage hero media

This is the one place in the app right now with real code already wired up
to display your media — `src/components/layout/Hero.jsx`. **You don't need
to touch any code.** Just save your files here, using these exact names:

| File | Required? | Spec |
|---|---|---|
| `hero-bg.jpg` | Yes, if you want any hero image at all | 1920×1080 (16:9), JPG, aim for under ~300KB. Also doubles as the video's poster frame and as the fallback shown while the video loads. |
| `hero-bg.mp4` | Optional | Same 1920×1080 frame, 5–10 seconds, **no audio track** (it's always muted), loop-friendly (first and last frame should look similar), H.264 codec, aim for under ~5MB after compression (use `ffmpeg` or HandBrake — ask me if you want exact compression commands). |

## What to actually shoot/source, given the logo's palette

Deep slate/charcoal-teal background with warm gold light — so look for:
- **Golden-hour or blue-hour** light (sunrise/sunset), not harsh midday sun.
- A recognizable Cameroon landmark or landscape: Mount Cameroon's silhouette,
  Kribi's coastline, Rhumsiki's peaks, or a wide shot over Yaoundé/Douala at
  dusk. Depth (foreground + a hazy background) reads better once the
  homepage headline text sits on top of it.
- Avoid busy/cluttered shots (crowds, signage, text) — the text overlay
  needs a calm-enough area to stay readable, and `Hero.jsx` already dims
  the media to 60% opacity over the dark gradient to help with this, but
  a business a smart choice of image gives it much better contrast.

## What happens if you don't add these yet

Nothing breaks. `Hero.jsx` shows the brand gradient alone (matching the
logo's slate tones) — you already saw this in the last build. Add the
files whenever they're ready; no rebuild step beyond your normal
`npm run build` / `npm run dev` is needed.

## Not wired up yet (next design pass, not needed before this commit)

`public/media/illustrations/` and `public/media/how-to-use/` exist as
placeholders for later — the pages that would use them (empty states, 404,
the how-to-use walkthrough) are still plain placeholders themselves. I'll
give you exact filenames for those once we actually build those pages, the
same way I just did for the hero. No need to source anything for them yet.
