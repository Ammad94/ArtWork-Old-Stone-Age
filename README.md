# ArtWork-Old-Stone-Age

Art assets for **Old Stone Age** — a 2D mobile survival game.
Style: high-detail realistic painted digital illustration (game concept-art quality).
Not cartoon, not anime, not pixel art.

## Assets

### Protagonist — hero caveman

| File | Description |
|---|---|
| `assets/characters/hero_caveman/hero_caveman_idle_front_176x392.png` | Game-ready sprite: standing idle pose, front view. 176×392 px, 32-bit RGBA PNG, 72 DPI, fully transparent background, character centered with ~5% margin, anti-aliased edges, no outline / drop shadow / glow. |
| `assets/characters/hero_caveman/source/hero_caveman_idle_front_master.png` | Source master painting (848×1264, flat white backdrop) the sprite is derived from. |
| `assets/characters/hero_caveman/source/qa_transparency_check.png` | QA preview: final sprite composited over a checkerboard (4× nearest) to verify alpha. |
| `assets/characters/hero_caveman/source/qa_sprite_4x.png` | QA preview: final sprite at 4× nearest for edge/detail inspection. |

Sprite technical spec (all character sprites should follow this):

- Size: 176 × 392 px (portrait), character centered, ~5% margin per side
- Color: 32-bit RGBA (8 bpc), PNG with true alpha transparency
- 72 DPI, screen use; anti-aliased silhouette; no outlines, shadows or glow
- Lighting baked in: soft volumetric key upper-front-left, warm rim/bounce right & back
- Palette: warm earth tones — browns, tans, ochres, cream, golden-warm highlights

## Tools

- `tools/make_sprite.py` — reproducible pipeline that derives the game-ready
  sprite from a master painting: backdrop keying (border flood-fill),
  defringed anti-aliased alpha matte, bbox crop, aspect-preserving fit into the
  176×392 frame with ~5% margins, premultiplied LANCZOS downscale, QA previews.
  Run with: `python tools/make_sprite.py` (requires Pillow, NumPy, SciPy).
