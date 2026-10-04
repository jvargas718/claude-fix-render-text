"""Find the blur that makes new type as soft as the render's own lettering.

Usage: uv run --with pillow --with numpy --with scipy python match_softness.py IMAGE REF_BOX NEW_BOX
  IMAGE    a flat snapshot containing both the original (reference) lettering and the new type
  REF_BOX  x0,y0,x1,y1 around correct, original render text on the same surface (e.g. a heading)
  NEW_BOX  x0,y0,x1,y1 around the new, crisp type
Prints the Gaussian blur radius (px) to apply to the new type, plus the grain level of the render.
Sharpness metric: 90th-percentile gradient magnitude divided by the text/background contrast.
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


def crop(img, spec):
    x0, y0, x1, y1 = [int(float(v)) for v in spec.split(",")]
    return img[y0:y1, x0:x1]


def sharpness(lum):
    g = np.hypot(ndi.sobel(lum, 0), ndi.sobel(lum, 1))
    contrast = np.percentile(lum, 98) - np.percentile(lum, 20)
    return np.percentile(g, 90) / max(contrast, 1)


img = np.asarray(Image.open(sys.argv[1]).convert("L")).astype(float)
ref, new = crop(img, sys.argv[2]), crop(img, sys.argv[3])
target = sharpness(ref)
best = min(((abs(sharpness(ndi.gaussian_filter(new, s)) - target), s) for s in np.arange(0, 3.01, 0.1)))
flat = ref[ref < np.percentile(ref, 40)]
grain = float(np.std(flat - ndi.median_filter(ref, 5)[ref < np.percentile(ref, 40)]))
print(f"reference sharpness {target:.3f}  new type sharpness {sharpness(new):.3f}")
print(f"blur_radius_px {best[1]:.1f}")
print(f"grain_std {grain:.2f}  (Add Noise amount ~ {grain / 2.55:.1f}%)")
