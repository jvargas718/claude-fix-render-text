"""Proofread the finished image against the approved copy.

Usage: python3 proofread.py DETECTED.json APPROVED.json
DETECTED.json: output of `detect_text <finished image>`.
APPROVED.json: ["exact approved line", ...]
Reports, for every approved line, the best-matching detected line and a similarity score.
Anything below 0.9 needs a human look (OCR misreads tiny or steep text, so a low score is a flag, not proof of an error).
"""
import json, sys
from difflib import SequenceMatcher

det = [d["text"] for d in json.load(open(sys.argv[1]))]
norm = lambda s: " ".join(s.lower().replace("®", "").replace("™", "").split())
bad = 0
for line in json.load(open(sys.argv[2])):
    best = max(det, key=lambda t: SequenceMatcher(None, norm(t), norm(line)).ratio(), default="")
    score = SequenceMatcher(None, norm(best), norm(line)).ratio()
    flag = "OK  " if score >= 0.9 else "CHECK"
    bad += score < 0.9
    print(f"{flag} {score:.2f}  approved: {line!r}  found: {best!r}")
print(f"\n{bad} line(s) need a look.")
