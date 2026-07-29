# Logo assets

## What's here now (real, derived from your uploaded logo)

| File | Used where | Notes |
|---|---|---|
| `logo-icon.png` | Master 1024×1024 source | Cropped from your uploaded artwork, background padding removed |
| `logo-full.png` | Navbar + footer | 256×256, referenced directly in `Navbar.jsx` / `Footer.jsx` |
| `favicon.png` | Browser tab icon | 512×512 |
| `og-image.png` | Social share preview (link unfurls on WhatsApp/Twitter/etc.) | 1200×630, composed on your brand's slate gradient with a matching wordmark |

## Nice-to-have upgrades, not blockers

- **A true vector (SVG or high-res transparent PNG) version of the icon.**
  What we're using now was cropped from your JPG, so it inherits a small
  amount of JPEG compression softness and its own baked-in background —
  fine at the sizes used today, but if you ever have the original design
  file (Figma/Illustrator/Canva export), export a transparent PNG or SVG
  and drop it in as `logo-icon.png` — everything else derives from it.
- **A dark-mode variant** (`logo-full-dark.png`) — not urgent since the
  icon's own background is already dark, so it holds up fine on both a
  light and dark navbar. Skip unless you want a lighter alternate mark.
