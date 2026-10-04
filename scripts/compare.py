"""Before/after sheet for checking a fix.

Usage: uv run --with pillow python compare.py BEFORE AFTER OUT.jpg x0,y0,x1,y1 [x0,y0,x1,y1 ...]
Each box becomes one row: before on the left, after on the right, scaled to <= 1600 px wide overall.
"""
import sys
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
before, after = Image.open(sys.argv[1]).convert("RGB"), Image.open(sys.argv[2]).convert("RGB")
rows = []
for spec in sys.argv[4:]:
    box = tuple(int(float(v)) for v in spec.split(","))
    a, b = before.crop(box), after.crop(box)
    row = Image.new("RGB", (a.width * 2 + 16, a.height), "white")
    row.paste(a, (0, 0)); row.paste(b, (a.width + 16, 0)); rows.append(row)
W = max(r.width for r in rows)
sheet = Image.new("RGB", (W, sum(r.height for r in rows) + 16 * (len(rows) - 1)), "white")
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height + 16
if sheet.width > 1600:
    sheet = sheet.resize((1600, int(sheet.height * 1600 / sheet.width)), Image.LANCZOS)
sheet.save(sys.argv[3], quality=90)
print(sys.argv[3], sheet.size)
