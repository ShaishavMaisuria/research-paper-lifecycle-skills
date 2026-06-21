#!/usr/bin/env python3
"""Render paper-workspace/ into a single self-contained dashboard.html.

Stdlib only. No network, no external assets — the HTML inlines its own CSS so
it opens offline in any browser and renders in light or dark mode. Re-run it any
time to refresh; it reads whatever is currently in the workspace.

Reads (all optional, degrades gracefully):
  paper-workspace/INDEX.md            running log: "DATE · skill · path · summary"
  paper-workspace/<stage>/*           artifacts grouped by lifecycle stage
  .paper-memory/profile.yml           paper title / target venue (flat keys only)
"""
import argparse
import html
import re
from pathlib import Path

STAGES = [
    ("research", "Search & read"),
    ("writing", "Write"),
    ("review", "Verify & review"),
    ("submission", "Submit & rebut"),
    ("presenting", "Present"),
]

CSS = """
:root{--bg:#ffffff;--fg:#0f172a;--muted:#64748b;--card:#f8fafc;--line:#e2e8f0;
--accent:#4f46e5;--done:#0d9488;--todo:#cbd5e1}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8b949e;
--card:#161b22;--line:#30363d;--accent:#a78bfa;--done:#2dd4bf;--todo:#30363d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
line-height:1.5}.wrap{max-width:1000px;margin:0 auto;padding:32px 24px}
h1{font-size:28px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 24px}
.bar{display:flex;gap:8px;margin:24px 0}.step{flex:1;text-align:center;font-size:13px;
font-weight:600;padding:10px 6px;border-radius:8px;background:var(--todo);color:#fff}
.step.done{background:var(--done)}.step small{display:block;font-weight:400;opacity:.85}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h3{margin:0 0 10px;font-size:15px}.art{font-size:14px;padding:6px 0;
border-top:1px solid var(--line)}.art a{color:var(--accent);text-decoration:none}
.art a:hover{text-decoration:underline}.empty{color:var(--muted);font-size:13px;font-style:italic}
.log{margin-top:28px}.log .row{font-size:13px;padding:8px 0;border-top:1px solid var(--line);
display:flex;gap:12px}.log .d{color:var(--muted);white-space:nowrap}
.foot{margin-top:32px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}
.pill{display:inline-block;background:var(--accent);color:#fff;font-size:12px;
font-weight:600;padding:2px 10px;border-radius:999px;margin-left:8px}
"""


def read_profile(root: Path) -> dict:
    p = root.parent / ".paper-memory" / "profile.yml"
    out = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^([a-z_]+):\s*(.+)$", line.strip())
            if m:
                out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def list_artifacts(stage_dir: Path):
    if not stage_dir.is_dir():
        return []
    return sorted(f for f in stage_dir.rglob("*") if f.is_file() and f.name != ".gitkeep")


def parse_index(root: Path):
    idx = root / "INDEX.md"
    rows = []
    if idx.is_file():
        for line in idx.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = [p.strip() for p in line.split("·")]
            if len(parts) >= 3 and re.match(r"\d{4}-\d{2}-\d{2}", parts[0]):
                rows.append(parts)
    return rows


def esc(s: str) -> str:
    return html.escape(str(s))


def build(root: Path) -> str:
    profile = read_profile(root)
    title = profile.get("title") or "Paper workspace"
    venue = profile.get("target_venue") or profile.get("venue") or ""

    steps = []
    for key, label in STAGES:
        arts = list_artifacts(root / key)
        steps.append((key, label, arts))
    done = sum(1 for _, _, a in steps if a)

    parts = [f"<!doctype html><html><head><meta charset='utf-8'>",
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>",
             f"<title>{esc(title)} — dashboard</title><style>{CSS}</style></head><body><div class='wrap'>"]
    parts.append(f"<h1>{esc(title)}{f'<span class=pill>{esc(venue)}</span>' if venue else ''}</h1>")
    parts.append(f"<p class='sub'>Progress dashboard · {done}/{len(STAGES)} stages have artifacts · "
                 f"refresh by re-running build_dashboard.py</p>")

    # progress bar
    parts.append("<div class='bar'>")
    for key, label, arts in steps:
        cls = "step done" if arts else "step"
        parts.append(f"<div class='{cls}'>{esc(label)}<small>{len(arts)} file(s)</small></div>")
    parts.append("</div>")

    # stage cards
    parts.append("<div class='grid'>")
    for key, label, arts in steps:
        parts.append(f"<div class='card'><h3>{esc(label)}</h3>")
        if arts:
            for f in arts:
                rel = f.relative_to(root.parent)
                parts.append(f"<div class='art'><a href='{esc(rel)}'>{esc(f.name)}</a></div>")
        else:
            parts.append("<div class='empty'>nothing here yet</div>")
        parts.append("</div>")
    parts.append("</div>")

    # timeline
    rows = parse_index(root)
    if rows:
        parts.append("<div class='log'><h3>Recent activity</h3>")
        for r in rows[:40]:
            d = esc(r[0]); rest = " · ".join(esc(x) for x in r[1:])
            parts.append(f"<div class='row'><span class='d'>{d}</span><span>{rest}</span></div>")
        parts.append("</div>")

    parts.append("<div class='foot'>Generated from paper-workspace/ by render-workspace-html. "
                 "Local file, never uploaded. Copilot, not pilot — you stay the author.</div>")
    parts.append("</div></body></html>")
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render paper-workspace/ into a self-contained dashboard.html.")
    ap.add_argument("--workspace", default="paper-workspace", help="workspace dir (default: paper-workspace)")
    ap.add_argument("--out", default=None, help="output HTML path (default: <workspace>/dashboard.html)")
    args = ap.parse_args()
    root = Path(args.workspace).resolve()
    if not root.is_dir():
        print(f"ERROR no workspace at {root} — run some skills first, or pass --workspace")
        return 1
    out = Path(args.out) if args.out else root / "dashboard.html"
    out.write_text(build(root), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
