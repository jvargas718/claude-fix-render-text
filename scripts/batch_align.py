"""Carry an approved fix plan from the reference render to another render of the same product (colorway, re-export, reframe).

Usage: uv run --with pillow --with numpy --with opencv-python-headless python batch_align.py REF.png PLAN.json TARGET.png OUT_PLAN.json [--det TARGET_DETECTED.json]

PLAN.json (written once, from the approved reference fix):
  {"cleanup": [{"polys": [[[x,y],...],...], "radius":14, "passes":2, "feather":2, "noise":1.0, "blur":0}, ...],
   "lines":   [{"name":..., "text":..., "x":..., "baseline":..., "angle":..., "size":..., "hscale":..., "font":..., "rgb":[r,g,b]}, ...],
   "group": "Corrected text", "soften": {"radius":0.9, "noise":1.5},
   "color_box": [x0,y0,x1,y1],   # correct render lettering on the same face, to re-sample ink colour per image
   "check_quads": [[[x,y]x4], ...]}  # the garbled lines being replaced (for validation)
What it does:
  1. Finds the similarity transform REF -> TARGET (ORB features + RANSAC): scale, rotation, shift.
  2. Moves every cleanup polygon and text line with it (size scales, angle adds the rotation).
  3. Re-samples the ink colour from color_box in the target (colourways change print colours).
  4. With --det: checks the target's own detected text. Lines found inside the fix area that don't line up with a planned
     line are reported as NEEDS REVIEW (the AI may have rendered different text on this variant).
Prints a short report; exits 2 if alignment is unreliable (then fix that image by hand, as a reference job).
"""
import json, math, sys
import numpy as np, cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ref_p, plan_p, tgt_p, out_p = sys.argv[1:5]
det_p = sys.argv[sys.argv.index("--det") + 1] if "--det" in sys.argv else None
plan = json.load(open(plan_p))

def gray(p, s):
    im = Image.open(p).convert("L"); return np.asarray(im.resize((int(im.width * s), int(im.height * s)), Image.BILINEAR))
S = 0.5
a, b = gray(ref_p, S), gray(tgt_p, S)
orb = cv2.ORB_create(6000)
ka, da = orb.detectAndCompute(a, None); kb, db = orb.detectAndCompute(b, None)
m = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
good = [x for x, y in (p for p in m if len(p) == 2) if x.distance < 0.75 * y.distance]
src = np.float32([ka[g.queryIdx].pt for g in good]) / S; dst = np.float32([kb[g.trainIdx].pt for g in good]) / S
M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=5000, confidence=0.999)
n_in = int(inl.sum()) if inl is not None else 0
if M is None or n_in < 40:
    print(f"ALIGNMENT FAILED ({n_in} inliers). Treat {tgt_p} as its own reference job."); sys.exit(2)
scale = math.hypot(M[0, 0], M[1, 0]); rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
err = np.linalg.norm((src[inl.ravel() == 1] @ M[:, :2].T + M[:, 2]) - dst[inl.ravel() == 1], axis=1)
print(f"aligned: {n_in}/{len(good)} inliers, scale {scale:.4f}, rotation {rot:+.2f} deg, shift ({M[0,2]:+.1f}, {M[1,2]:+.1f}) px, median error {np.median(err):.2f} px")
def T(pt): x, y = pt; return [float(M[0, 0] * x + M[0, 1] * y + M[0, 2]), float(M[1, 0] * x + M[1, 1] * y + M[1, 2])]

out = json.loads(json.dumps(plan))
for c in out["cleanup"]:
    c["polys"] = [[T(p) for p in poly] for poly in c["polys"]]
    c["radius"] = max(4, round(c.get("radius", 14) * scale))
# ink colour from correct lettering on the same face
tgt = np.asarray(Image.open(tgt_p).convert("RGB")).astype(np.float32)
cb = plan.get("color_box")
rgb = None
if cb:
    corners = [T((cb[0], cb[1])), T((cb[2], cb[1])), T((cb[2], cb[3])), T((cb[0], cb[3]))]
    xs, ys = [p[0] for p in corners], [p[1] for p in corners]
    reg = tgt[int(min(ys)):int(max(ys)), int(min(xs)):int(max(xs))].reshape(-1, 3); lum = reg.mean(axis=1)
    bright = reg[lum > np.percentile(lum, 97)]; ref_ink = np.array(plan["lines"][0]["rgb"], np.float32)
    # the planned colour was chosen relative to the sampled heading colour on the reference; keep that ratio
    ref_reg = np.asarray(Image.open(ref_p).convert("RGB")).astype(np.float32)[int(cb[1]):int(cb[3]), int(cb[0]):int(cb[2])].reshape(-1, 3)
    ref_bright = ref_reg[ref_reg.mean(axis=1) > np.percentile(ref_reg.mean(axis=1), 97)].mean(axis=0)
    rgb = [int(max(0, min(255, v))) for v in bright.mean(axis=0) * (ref_ink / np.maximum(ref_bright, 1))]
for L in out["lines"]:
    L["x"], L["baseline"] = T((L["x"], L["baseline"]))
    L["angle"] = L["angle"] + rot; L["size"] = L["size"] * scale
    if rgb: L["rgb"] = rgb
out["check_quads"] = [[T(p) for p in q] for q in plan.get("check_quads", [])]
out["transform"] = {"matrix": M.tolist(), "scale": scale, "rotation": rot, "inliers": n_in}
print(f"ink colour: {rgb}" if rgb else "ink colour: kept from plan")

review = []
if det_p:
    det = json.load(open(det_p)); qs = out["check_quads"]
    if qs:
        cx = [sum(p[0] for p in q) / 4 for q in qs]; cy = [sum(p[1] for p in q) / 4 for q in qs]
        x0, x1, y0, y1 = min(cx) - 150, max(cx) + 150, min(cy) - 60, max(cy) + 60
        for d in det:
            q = d["quad"]; dx = (q["tl"][0] + q["br"][0]) / 2; dy = (q["tl"][1] + q["br"][1]) / 2
            if not (x0 <= dx <= x1 and y0 <= dy <= y1): continue
            near = min(math.hypot(dx - a_, dy - b_) for a_, b_ in zip(cx, cy))
            if near > 28 and not any(k.lower() == d["text"].lower() for k in plan.get("keep", [])):
                review.append(d["text"])
    print("NEEDS REVIEW: " + "; ".join(review) if review else "validation: every detected line in the fix area matches the plan")
out["needs_review"] = review
json.dump(out, open(out_p, "w"), indent=1); print("wrote", out_p)
