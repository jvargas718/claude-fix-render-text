"""Precise geometry for text lines found by detect_text.

Usage: uv run --with pillow --with numpy --with scipy python measure_text.py IMAGE REGIONS.json > measured.json
REGIONS.json: [{"id": "b1_body1", "bbox": [x0, y0, x1, y1]}, ...]  (pad OCR boxes by ~10 px)
For each region: ink mask vs. local background, robust baseline fit, extents, sizes and ink colour.
Output per region: left, right, top, bottom, baseline_left (y at `left`), baseline_right, angle_deg
(positive = baseline falls to the right), x_height, cap_or_ascender, ink_rgb, bg_rgb, polarity.
"""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


def measure(img, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    reg = img[y0:y1, x0:x1].astype(float)
    lum = reg.mean(axis=2)
    bg = ndi.median_filter(lum, size=max(31, (y1 - y0) | 1))
    d = lum - bg
    polarity = "light" if np.percentile(d, 99) > -np.percentile(d, 1) else "dark"
    s = d if polarity == "light" else -d
    thr = max(12, 0.45 * np.percentile(s, 99.5))
    m = ndi.binary_opening(s > thr)
    if m.sum() < 20:
        return {"error": "no ink found"}
    cols = np.where(m.any(axis=0))[0]
    rows = np.where(m.any(axis=1))[0]
    # per-column lowest ink pixel; the baseline is the dominant lower envelope (descenders are outliers)
    bots = np.array([(c, np.where(m[:, c])[0].max()) for c in cols], float)
    tops = np.array([(c, np.where(m[:, c])[0].min()) for c in cols], float)
    fit = np.polyfit(bots[:, 0], bots[:, 1], 1)
    for _ in range(3):  # drop descenders/outliers and refit
        r = bots[:, 1] - np.polyval(fit, bots[:, 0])
        keep = np.abs(r) < max(2.0, 1.5 * np.median(np.abs(r)) + 1)
        if keep.sum() > 10:
            fit = np.polyfit(bots[keep, 0], bots[keep, 1], 1)
    base = lambda x: float(np.polyval(fit, x))
    h_above = np.polyval(fit, tops[:, 0]) - tops[:, 1]
    ink = reg[m & (s > np.percentile(s[m], 60))]
    bgpx = reg[~ndi.binary_dilation(m, iterations=4)]
    L, R = float(cols[0]), float(cols[-1])
    return {
        "left": x0 + L, "right": x0 + R, "top": y0 + float(rows[0]), "bottom": y0 + float(rows[-1]),
        "baseline_left": round(y0 + base(L), 1), "baseline_right": round(y0 + base(R), 1),
        "angle_deg": round(float(np.degrees(np.arctan(fit[0]))), 2),
        "x_height": round(float(np.percentile(h_above, 35)), 1),
        "cap_or_ascender": round(float(np.percentile(h_above, 90)), 1),
        "ink_rgb": [int(v) for v in np.median(ink, axis=0)],
        "bg_rgb": [int(v) for v in np.median(bgpx, axis=0)],
        "polarity": polarity,
    }


if __name__ == "__main__":
    img = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
    regions = json.load(open(sys.argv[2]))
    print(json.dumps({r["id"]: measure(img, r["bbox"]) for r in regions}, indent=1))
