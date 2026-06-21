#!/usr/bin/env python3
"""Shared helpers for the verify-results scripts (artifact reproduction audit).

Stdlib only. Holds the Finding record, the common CLI/report plumbing, number
and metric parsing, and a tolerance-aware numeric comparison used by all three
checkers (extract_claims, audit_repo, compare_metrics) so they behave alike.

This module is a library, not a checker. Run one of:
    extract_claims.py, audit_repo.py, compare_metrics.py
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import re
import sys

SEVERITIES = ("ERROR", "WARN", "INFO")


@dataclasses.dataclass
class Finding:
    """One audit observation. `where` is a free-form locator (file:line, a repo
    path, or a claim id) so the same record works for source, repo, and
    metric-comparison checks."""
    severity: str  # ERROR | WARN | INFO
    check: str  # e.g. "repo/missing-requirements" or "metric/mismatch"
    where: str  # file:line, repo path, or claim id
    message: str

    def format(self) -> str:
        return f"[{self.severity:5}] {self.check:30} {self.where} — {self.message}"


# ---------------------------------------------------------------------------
# Number / percentage parsing
# ---------------------------------------------------------------------------

# A signed decimal, optionally with thousands separators and a trailing %.
_NUM_RE = re.compile(
    r"(?<![\w.])"  # not preceded by a word char or dot (avoid mid-token)
    r"([+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[+-]?\d+(?:\.\d+)?|[+-]?\.\d+)"
    r"\s*(%?)"
)


def parse_number(token: str):
    """Parse a single human-written number ('92.4', '1,234', '88%', '.5').

    Returns (value: float, is_percent: bool) or None if not a number.
    Percentages are returned as their face value (88% -> 88.0, is_percent=True),
    not 0.88 — comparison normalizes both sides instead.
    """
    token = token.strip()
    m = _NUM_RE.fullmatch(token)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        return float(raw), bool(m.group(2))
    except ValueError:
        return None


def find_numbers(text: str):
    """Yield (value, is_percent, span) for every number-looking token in text."""
    for m in _NUM_RE.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        yield val, bool(m.group(2)), m.span()


def _as_fraction(value: float, is_percent: bool, scale_hint: str | None) -> float:
    """Normalize a metric onto a 0..1-ish scale when we can tell it is a rate.

    Only rescales when we are confident: an explicit % sign, or a value > 1
    paired with a percent-like metric name. Otherwise returns the value
    unchanged (raw metrics like loss=2.31 or time=140.5 must NOT be rescaled).
    """
    if is_percent:
        return value / 100.0
    if scale_hint == "percent" and value > 1.0:
        return value / 100.0
    return value


def compare_values(
    paper_val: float,
    paper_pct: bool,
    run_val: float,
    run_pct: bool,
    *,
    rel_tol: float,
    abs_tol: float,
    scale_hint: str | None = None,
) -> tuple[str, float]:
    """Tolerance-aware comparison. Returns (status, normalized_abs_diff).

    status is "match" | "mismatch". A match means the two agree within
    max(rel_tol*|paper|, abs_tol) AFTER normalizing percent vs fraction — i.e.
    the difference is small enough not to change the paper's claim. Exact
    equality is never required (ACM/SIGMOD/ETAPS: agreement within tolerance).
    """
    p = _as_fraction(paper_val, paper_pct, scale_hint)
    r = _as_fraction(run_val, run_pct, scale_hint)
    diff = abs(p - r)
    tol = max(rel_tol * abs(p), abs_tol)
    return ("match" if diff <= tol else "mismatch"), diff


# ---------------------------------------------------------------------------
# Metric-name heuristics (used to label/scale extracted claims)
# ---------------------------------------------------------------------------

# Lowercased metric keywords -> a coarse scale hint. "percent" => 0..100-ish
# rates; "raw" => leave untouched. Used only as a hint; never to invent values.
METRIC_KEYWORDS = {
    "accuracy": "percent", "acc": "percent", "top-1": "percent",
    "top-5": "percent", "top1": "percent", "top5": "percent",
    "precision": "percent", "recall": "percent", "f1": "percent",
    "f-score": "percent", "auc": "raw", "auroc": "raw", "map": "percent",
    "miou": "percent", "iou": "percent", "dice": "percent", "bleu": "raw",
    "rouge": "raw", "error rate": "percent", "err": "percent",
    "ppl": "raw", "perplexity": "raw", "loss": "raw", "mse": "raw",
    "rmse": "raw", "mae": "raw", "psnr": "raw", "ssim": "raw",
    "throughput": "raw", "latency": "raw", "speedup": "raw", "fps": "raw",
    "wer": "percent", "cer": "percent", "ndcg": "raw", "mrr": "raw",
    "em": "percent", "exact match": "percent", "win rate": "percent",
}


def guess_metric(text: str) -> tuple[str | None, str | None]:
    """Return (matched_keyword, scale_hint) for the first metric keyword in
    `text` (lowercased), else (None, None)."""
    low = text.lower()
    # longest keywords first so "error rate" wins over "err"
    for kw in sorted(METRIC_KEYWORDS, key=len, reverse=True):
        if kw in low:
            return kw, METRIC_KEYWORDS[kw]
    return None, None


# ---------------------------------------------------------------------------
# Common CLI and reporting
# ---------------------------------------------------------------------------


def add_common_args(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument(
        "--strict", action="store_true",
        help="exit 1 on WARN findings too, not just ERROR",
    )
    return ap


def report(tool: str, findings: list[Finding], notes: list[str], args,
           extra: dict | None = None) -> int:
    """Print findings (text or JSON); return the process exit code.

    Exit: 1 if any ERROR (or any WARN under --strict), else 0.
    """
    findings = sorted(
        findings, key=lambda f: (SEVERITIES.index(f.severity), f.check, f.where)
    )
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
    if args.json:
        payload = {
            "tool": tool,
            "findings": [dataclasses.asdict(f) for f in findings],
            "notes": notes,
            "summary": counts,
        }
        if extra:
            payload.update(extra)
        json.dump(payload, sys.stdout, indent=2, default=str)
        print()
    else:
        print(f"== {tool} ==")
        for note in notes:
            print(f"  note: {note}")
        if not findings:
            print("  no findings — clean.")
        for f in findings:
            print("  " + f.format())
        print(
            f"  summary: {counts['ERROR']} error(s), {counts['WARN']} warning(s), "
            f"{counts['INFO']} info"
        )
        print("  reminder: a clean audit means CONSISTENT, not independently "
              "reproduced — the author still runs the artifact.")
    if counts["ERROR"] or (getattr(args, "strict", False) and counts["WARN"]):
        return 1
    return 0


def isclose(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="verifylib.py",
        description=(
            "Shared library for the verify-results scripts — not a checker "
            "itself. Run one of: extract_claims.py, audit_repo.py, "
            "compare_metrics.py."
        ),
    )
    parser.parse_args()
    parser.print_help()
    sys.exit(0)
