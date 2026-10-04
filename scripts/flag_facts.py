"""Flag text that looks like a fact, spec, claim or legal mark, so it is never 'fixed' by guessing.

Usage: python3 flag_facts.py DETECTED.json [PROPOSED.json]
  DETECTED.json  output of detect_text (what the render literally says)
  PROPOSED.json  optional {"render text": "proposed text"} map; proposed text is checked too
Prints one line per flagged item: category, the text, and why. Exit code 0 always.
Categories:
  number   digits, sizes, units (mL, oz, g, %, mg, SPF, x, mm, W, V, mAh, fps, GB...)
  claim    marketing or health claims (free from, clinically, dermatologist, organic, vegan, cruelty, natural, safe,
           hypoallergenic, certified, proven, guaranteed, best, #1, award...)
  legal    ®, ™, ©, warnings, Prop 65, patent, FCC, CE, UL, recycling codes, "made in", "distributed by"
  contact  URLs, emails, @handles, phone numbers, addresses
  code     barcodes, model / style / lot numbers, long digit or alphanumeric runs
"""
import json, re, sys

RULES = [
    ("legal", r"[®™©]|\b(warning|caution|prop(osition)?\s*65|patent|pat\.|fcc|\bce\b|\bul\b|rohs|made in|distributed by|manufactured (by|for)|keep out of reach|not for|recycl|\bpp\b|\bpet\b|\bhdpe\b)"),
    ("contact", r"(https?://|www\.|\.com\b|\.co\b|\.io\b|@\w|[\w.-]+@[\w.-]+|\+?\d[\d\s().-]{7,}\d|\b(street|st\.|ave|avenue|suite|blvd|road|rd\.)\b)"),
    ("code", r"(\b\d{8,14}\b|\b(sku|upc|ean|lot|batch|exp|model|style|ref|no\.)\b|\b[A-Z]{1,4}-?\d{3,}\b)"),
    ("number", r"(\d|\b(ml|fl\s?oz|oz|mg|kg|lbs?|spf|mm|cm|inch|watts?|mah|fps|gb|tb|hz|pcs|count|pack of)\b|%|×)"),
    ("claim", r"\b(free|clinically|clinical|dermatolog\w*|tested|organic|vegan|cruelty|natural|non[- ]?toxic|safe|hypoallergenic|certified|proven|guarantee\w*|best|#1|no\.?\s?1|award\w*|recommended|approved|sustainab\w*|eco|biodegradable|compostable|recyclable|fda|usda|gmp|sensitive skin|all skin types|reduces?|prevents?|cures?|treats?|heals?|boosts?|repairs?|anti[- ]?\w+|whiten\w*|instant\w*)\b"),
]

def flags(text):
    out = []
    for cat, rx in RULES:
        m = re.search(rx, text, re.I)
        if m: out.append((cat, m.group(0)))
    return out

if __name__ == "__main__":
    det = json.load(open(sys.argv[1]))
    prop = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    seen = 0
    for d in det:
        t = d["text"]
        for label, s in (("render", t), ("proposed", prop.get(t))):
            if not s: continue
            for cat, hit in flags(s):
                print(f"{cat:8s} [{label}] {s!r}   (matched {hit!r})"); seen += 1
    print(f"\n{seen} flag(s). Flagged lines need the user's decision: confirm, neutral wording, placeholder, or remove.")
