#!/usr/bin/env python3
"""Build catalog.json from a clone of ashishpatel26/500-AI-Agents-Projects.

Usage: build_catalog.py <repo_dir> <output.json>
"""
import json, re, sys
from pathlib import Path

LINK = re.compile(r"\]\((https?://[^)\s]+)\)")


def tables(lines):
    """Yield (section, header, rows) for each markdown table."""
    section, i = "", 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            section = ln.lstrip("# ").strip()
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1]):
            hdr = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows, i = [], i + 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i].strip().strip("|"))
                i += 1
            yield section, hdr, rows
            continue
        i += 1


def clean(cell):
    cell = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cell)
    cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)
    return re.sub(r"[*`]", "", cell).strip()


def main(repo, out):
    repo = Path(repo)
    items = []
    lines = (repo / "README.md").read_text(encoding="utf-8").splitlines()
    for section, hdr, rows in tables(lines):
        if hdr[0] != "Use Case":
            continue
        framework = "Industry" if section.startswith("Industry") else section
        for r in rows:
            cells = r.split("|")
            links = [u for u in LINK.findall(cells[-1]) if "shields.io" not in u] if len(cells) > 3 else []
            if len(cells) < 4 or not links:
                continue
            name = re.sub(r"^[^\w(\[]+", "", clean(cells[0])).strip()
            items.append({"name": name, "industry": clean(cells[1]),
                          "description": clean(cells[2]), "framework": framework,
                          "url": links[0]})
    idx = repo / "agents" / "README.md"
    if idx.exists():
        for section, hdr, rows in tables(idx.read_text(encoding="utf-8").splitlines()):
            if hdr[:2] != ["#", "Agent"]:
                continue
            for r in rows:
                c = [x.strip() for x in r.split("|")]
                m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", c[1])
                if not m:
                    continue
                items.append({"name": m.group(1), "industry": c[4], "framework": c[2],
                              "description": f"Runnable agent (LLM: {c[3]}, difficulty {c[5]})",
                              "url": "https://github.com/ashishpatel26/500-AI-Agents-Projects/tree/main/agents/"
                                     + m.group(2).strip("/"),
                              "local": "agents/" + m.group(2).strip("/")})
    Path(out).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} entries -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
