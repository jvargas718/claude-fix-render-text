"""Numbered crop sheet of the lines Claude needs the user to decide on (one image, answer all at once).

Usage: uv run --with pillow python question_sheet.py IMAGE DETECTED.json OUT.jpg IDX[,IDX...] [--pad 18] [--scale 2]
  IDX are 0-based indices into DETECTED.json, in the order they should be numbered. Use a range like 8-13 to ask about
  a whole paragraph as one question (crop covers all its lines).
Each row shows: the number, the zoomed crop of the line in context, and what the render literally says.
Send the sheet with a short list like:  "1  After 2weltio tey, irer use   →  your copy / filler / remove ?"
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
img = Image.open(sys.argv[1]).convert("RGB"); det = json.load(open(sys.argv[2])); out = sys.argv[3]
idx = []
for part in sys.argv[4].split(","):
    a, _, b = part.partition("-"); idx.append(list(range(int(a), int(b or a) + 1)))
pad = int(sys.argv[sys.argv.index("--pad") + 1]) if "--pad" in sys.argv else 18
scale = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 2.0
try:
    F = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 30, index=1); f2 = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 24, index=0)
except OSError:
    F = f2 = ImageFont.load_default()
rows = []
for n, grp in enumerate(idx, 1):
    boxes = [det[i]["bbox"] for i in grp]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes); x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    said = " / ".join(det[i]["text"] for i in grp)
    crop = img.crop((int(x0 - pad), int(y0 - pad), int(x1 + pad), int(y1 + pad)))
    crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    w = 90 + max(crop.width, 700); h = crop.height + 70
    r = Image.new("RGB", (w, h), (248, 247, 244)); d = ImageDraw.Draw(r)
    d.ellipse((18, 18, 70, 70), fill=(30, 30, 32)); d.text((44, 44), str(n), font=F, fill=(206, 242, 72), anchor="mm")
    r.paste(crop, (90, 10)); d.text((90, crop.height + 22), "render says: " + (said if len(said) < 90 else said[:87] + "…"), font=f2, fill=(90, 90, 90))
    rows.append(r)
W = max(r.width for r in rows); sheet = Image.new("RGB", (W, sum(r.height for r in rows) + 10 * len(rows)), "white")
y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.height + 10
if sheet.width > 1600: sheet = sheet.resize((1600, int(sheet.height * 1600 / sheet.width)), Image.LANCZOS)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); sheet.save(out, quality=90); print(out, sheet.size, len(rows), "questions")
