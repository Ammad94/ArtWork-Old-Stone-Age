#!/usr/bin/env python3
"""Build the game-ready 176x392 RGBA sprite from the painted master illustration.

Pipeline:
  1. Load master PNG (flat white backdrop).
  2. Estimate backdrop color from border pixels; build a distance map.
  3. Flood-label the near-white region connected to the image border -> background.
  4. Build an anti-aliased alpha matte: opaque core, soft 2px transition band
     where edge pixels were blended with the backdrop; un-premultiply (defringe)
     those edge pixels so no white halo survives.
  5. Crop to the character bounding box, scale (aspect preserved) to fit a
     176x392 frame with ~5% margin on every side, centered.
  6. Downscale in premultiplied-alpha space (LANCZOS) for clean edges.
  7. Save 32-bit RGBA PNG @72 DPI + QA previews.
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "assets/characters/hero_caveman/source/hero_caveman_idle_front_master.png"
OUT = "assets/characters/hero_caveman/hero_caveman_idle_front_176x392.png"
QA_CHECKER = "assets/characters/hero_caveman/source/qa_transparency_check.png"
QA_UPSCALE = "assets/characters/hero_caveman/source/qa_sprite_4x.png"

W, H = 176, 392
MARGIN = 0.05          # ~5% margin on each side
SCALE_SUPERSAMPLE = 4  # compose at 4x, then downscale

def main():
    img = Image.open(SRC).convert("RGB")
    rgb = np.asarray(img, dtype=np.float64) / 255.0
    h, w, _ = rgb.shape
    print(f"master: {w}x{h}")

    # --- 1. backdrop color = median of a 6px border ring -------------------
    ring = np.concatenate([
        rgb[:6].reshape(-1, 3), rgb[-6:].reshape(-1, 3),
        rgb[:, :6].reshape(-1, 3), rgb[:, -6:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    print(f"backdrop color ~ #{int(bg[0]*255):02x}{int(bg[1]*255):02x}{int(bg[2]*255):02x}")

    # --- 2. distance map + background flood label --------------------------
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))          # 0 = identical to backdrop
    near_white = dist < 0.16                              # loose tolerance
    labels, n = ndimage.label(near_white)
    border_labels = set(np.unique(np.concatenate(
        [labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    border_labels.discard(0)
    bg_mask = np.isin(labels, list(border_labels))
    print(f"background covers {bg_mask.mean()*100:.1f}% of frame")

    # --- 3. alpha matte with soft anti-aliased transition band -------------
    core = ~bg_mask
    band = ndimage.binary_dilation(bg_mask, iterations=2) & core
    alpha = np.ones((h, w), dtype=np.float64)
    alpha[bg_mask] = 0.0
    # edge pixels: alpha grows with distance from backdrop color
    t = np.clip(dist[band] / 0.35, 0.0, 1.0)
    alpha[band] = t ** 0.85
    # safety: never let isolated interior specks go transparent
    alpha[ndimage.binary_erosion(core, iterations=2)] = 1.0

    # --- 4. defringe: un-premultiply edge pixels against backdrop ----------
    out = rgb.copy()
    a3 = alpha[..., None]
    safe = np.clip(a3, 1e-3, 1.0)
    out = np.where(a3 < 1.0, np.clip((rgb - bg * (1.0 - a3)) / safe, 0, 1), rgb)

    rgba = np.dstack([out, alpha])
    ys, xs = np.nonzero(alpha > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = rgba[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    print(f"character bbox: {cw}x{ch} (aspect {cw/ch:.3f})")

    # --- 5. fit into frame with ~5% margins, centered ----------------------
    S = SCALE_SUPERSAMPLE
    avail_w = (W * (1 - 2 * MARGIN)) * S
    avail_h = (H * (1 - 2 * MARGIN)) * S
    scale = min(avail_w / cw, avail_h / ch)
    nw, nh = int(round(cw * scale)), int(round(ch * scale))
    char = np.asarray(Image.fromarray(
        (crop * 255).astype(np.uint8), "RGBA").resize((nw, nh), Image.LANCZOS),
        dtype=np.float64) / 255.0

    canvas = np.zeros((H * S, W * S, 4), dtype=np.float64)
    ox = (W * S - nw) // 2
    oy = (H * S - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = char

    # --- 6. premultiplied downscale (no fringing) --------------------------
    prem = canvas.copy()
    prem[..., :3] *= prem[..., 3:4]
    small = np.dstack([
        np.asarray(Image.fromarray((premul_chan * 255).astype(np.uint8), "L")
                   .resize((W, H), Image.LANCZOS), dtype=np.float64) / 255.0
        for premul_chan in prem.transpose(2, 0, 1)])  # -> (H, W, 4)
    a = small[..., 3]
    rgb_s = np.where(a[..., None] > 1e-3,
                     np.clip(small[..., :3] / np.clip(a[..., None], 1e-3, 1), 0, 1),
                     0.0)
    final = np.dstack([rgb_s, a])
    final_u8 = (np.clip(final, 0, 1) * 255 + 0.5).astype(np.uint8)

    sprite = Image.fromarray(final_u8, "RGBA")
    sprite.save(OUT, dpi=(72, 72))
    print(f"saved {OUT}: {sprite.size} mode={sprite.mode}")

    # --- 7. QA: margins + previews -----------------------------------------
    aa = np.asarray(sprite)[..., 3] / 255.0
    ys, xs = np.nonzero(aa > 0.02)
    print(f"final margins: left {xs.min()/W*100:.1f}% right {(W-1-xs.max())/W*100:.1f}% "
          f"top {ys.min()/H*100:.1f}% bottom {(H-1-ys.max())/H*100:.1f}%")
    print(f"alpha: opaque px {(aa > 0.99).sum()}, partial px {((aa > 0.02) & (aa < 0.99)).sum()}")

    # checkerboard composite, 4x nearest, to inspect transparency
    n4 = 8
    checker = np.indices((H, W)).sum(axis=0) // n4 % 2
    board = np.where(checker[..., None], 0.62, 0.35)
    comp = board * (1 - aa[..., None]) + final[..., :3] * aa[..., None]
    qa = Image.fromarray((comp * 255).astype(np.uint8), "RGB").resize(
        (W * 4, H * 4), Image.NEAREST)
    qa.save(QA_CHECKER)
    Image.fromarray(final_u8, "RGBA").resize((W * 4, H * 4), Image.NEAREST).save(QA_UPSCALE)
    print("QA previews written")
    return 0

if __name__ == "__main__":
    sys.exit(main())
