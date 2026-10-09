#!/usr/bin/env python3
"""Search the bundled catalog: search.py [-f framework] [-i industry] [-n 15] words..."""
import argparse, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("words", nargs="*")
p.add_argument("-f", "--framework")
p.add_argument("-i", "--industry")
p.add_argument("-n", type=int, default=15)
p.add_argument("--list-facets", action="store_true")
a = p.parse_args()
data = json.loads((Path(__file__).parent.parent / "catalog.json").read_text(encoding="utf-8"))
if a.list_facets:
    for k in ("framework", "industry"):
        print(k + ":", ", ".join(sorted({d[k] for d in data})))
    raise SystemExit
def score(d):
    if a.framework and a.framework.lower() not in d["framework"].lower(): return 0
    if a.industry and a.industry.lower() not in d["industry"].lower(): return 0
    hay = " ".join(d[k] for k in ("name", "industry", "description", "framework")).lower()
    return sum(hay.count(w.lower()) for w in a.words) if a.words else 1
hits = sorted(((score(d), d) for d in data), key=lambda t: -t[0])
for s, d in [h for h in hits if h[0]][: a.n]:
    print(f"- {d['name']} [{d['framework']} / {d['industry']}] {d['description']}\n  {d['url']}")
