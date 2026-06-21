#!/usr/bin/env python3
"""Extract the paper's reported numeric claims into a reviewable ledger.

Scans a LaTeX paper for numbers that look like reported results — cells inside
tabular environments and numbers sitting next to a metric keyword (accuracy,
F1, BLEU, latency, speedup, ...) — and writes a claims ledger the author can
confirm/edit before it is cross-checked against the artifact's own output by
compare_metrics.py.

This is a STARTING POINT, not ground truth: the author is the author. The
ledger is meant to be reviewed and corrected (drop spurious numbers like years
or citation counts, label which table/metric each number is). It never invents
a number that is not in the source.

Usage:
    python3 extract_claims.py paper.tex [--min 0] [--max ...] [--json]
    python3 extract_claims.py paper.tex --ledger claims.json   # write ledger

Exit codes: 0 ran (claims may be empty), 2 usage/load failure.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verifylib as vl

# Numbers that are almost never reported metrics — filter to cut noise.
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_TABULAR_BEGIN = re.compile(r"\\begin\{(table\*?|tabular\*?|tabularx|longtable|threeparttable)\}")
_TABULAR_END = re.compile(r"\\end\{(table\*?|tabular\*?|tabularx|longtable|threeparttable)\}")
_CAPTION_RE = re.compile(r"\\caption\s*\{")


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        buf = []
        i = 0
        while i < len(line):
            c = line[i]
            if c == "\\" and i + 1 < len(line):
                buf.append(line[i:i + 2]); i += 2; continue
            if c == "%":
                break
            buf.append(c); i += 1
        out.append("".join(buf))
    return "\n".join(out)


def _nearest_metric(line: str, span: tuple[int, int]):
    """Find the metric keyword whose occurrence on `line` is closest to the
    number at `span`. Returns (keyword, scale_hint) or (None, None). This keeps
    a line like 'BLEU 34.7 ... latency 12.5 ms' from labeling both numbers the
    same: each number takes its nearest keyword."""
    low = line.lower()
    best = None
    best_dist = None
    mid = (span[0] + span[1]) / 2
    for kw in vl.METRIC_KEYWORDS:
        start = 0
        while True:
            idx = low.find(kw, start)
            if idx < 0:
                break
            kwmid = idx + len(kw) / 2
            dist = abs(kwmid - mid)
            # prefer keywords; on ties, the longer (more specific) keyword wins
            if best_dist is None or dist < best_dist or (
                dist == best_dist and len(kw) > len(best)
            ):
                best, best_dist = kw, dist
            start = idx + 1
    if best is None:
        return None, None
    return best, vl.METRIC_KEYWORDS[best]


def _caption_text(line: str) -> str | None:
    m = _CAPTION_RE.search(line)
    if not m:
        return None
    # crude balanced-brace grab from the caption opener
    depth = 0
    out = []
    for ch in line[m.end() - 1:]:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        out.append(ch)
    return "".join(out).strip()


def extract(tex_path: str, *, lo: float | None, hi: float | None) -> tuple[list[dict], list[str]]:
    path = pathlib.Path(tex_path)
    if not path.exists():
        raise FileNotFoundError(f"tex file not found: {tex_path}")
    text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()

    claims: list[dict] = []
    notes: list[str] = []
    in_table = 0
    table_idx = 0
    cur_caption = None
    cur_metric_hint = None

    for n, line in enumerate(lines, start=1):
        if _TABULAR_BEGIN.search(line):
            if in_table == 0:
                table_idx += 1
                cur_caption = None
                cur_metric_hint = None
            in_table += 1
        cap = _caption_text(line)
        if cap and in_table:
            cur_caption = cap
            kw, hint = vl.guess_metric(cap)
            cur_metric_hint = kw

        for val, is_pct, span in vl.find_numbers(line):
            tok = line[span[0]:span[1]].strip()
            # noise filters
            if _YEAR_RE.match(re.sub(r"[+\-]", "", tok.split()[0])) and not is_pct:
                continue
            if lo is not None and val < lo:
                continue
            if hi is not None and val > hi:
                continue
            context = line.strip()
            # Per-number labeling: take the metric keyword nearest this number on
            # the line; fall back to the table caption's metric, if any.
            near_kw, near_hint = _nearest_metric(line, span)
            metric = near_kw or cur_metric_hint
            scale = near_hint or (vl.METRIC_KEYWORDS.get(metric) if metric else None)
            # Only keep numbers that are plausibly results: inside a table, OR
            # adjacent to a metric keyword. Bare numbers in prose with no metric
            # are skipped (too noisy).
            if not in_table and not near_kw:
                continue
            claims.append({
                "id": f"c{len(claims) + 1}",
                "source": f"{path.name}:{n}",
                "table": table_idx if in_table else None,
                "caption": cur_caption,
                "metric": metric,
                "scale_hint": scale,
                "value": val,
                "is_percent": is_pct,
                "raw": tok,
                "context": context[:160],
                "confirmed": False,
            })

        if _TABULAR_END.search(line) and in_table:
            in_table -= 1

    if not claims:
        notes.append("no result-like numbers found — point the script at the "
                     "main results .tex (or its \\input file), or add metric "
                     "keywords near the numbers")
    else:
        notes.append(f"{len(claims)} candidate claim(s) extracted from "
                     f"{table_idx} table environment(s) — REVIEW and confirm "
                     "before comparing; drop years/counts, fix metric labels")
    return claims, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tex", help="paper .tex file (or the results \\input file)")
    ap.add_argument("--min", type=float, default=None,
                    help="ignore numbers below this value (e.g. 0)")
    ap.add_argument("--max", type=float, default=None,
                    help="ignore numbers above this value")
    ap.add_argument("--ledger", help="also write the claims ledger to this JSON path")
    vl.add_common_args(ap)
    args = ap.parse_args()

    try:
        claims, notes = extract(args.tex, lo=args.min, hi=args.max)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.ledger:
        try:
            pathlib.Path(args.ledger).write_text(
                json.dumps({"claims": claims}, indent=2), encoding="utf-8"
            )
            notes.append(f"ledger written to {args.ledger}")
        except OSError as exc:
            print(f"error: could not write ledger: {exc}", file=sys.stderr)
            return 2

    findings = [
        vl.Finding(
            "INFO", "claim/extracted", c["source"],
            f"{c['metric'] or 'number'}={c['raw']} "
            f"(table {c['table']})" if c["table"] else
            f"{c['metric'] or 'number'}={c['raw']}",
        )
        for c in claims
    ]
    return vl.report("extract_claims", findings, notes, args,
                     extra={"claims": claims, "tex": args.tex})


if __name__ == "__main__":
    sys.exit(main())
