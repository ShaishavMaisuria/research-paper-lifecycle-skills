#!/usr/bin/env python3
"""Render a classified triage JSON into the prioritized response matrix.

Input is the JSON produced by parse_reviews.py AFTER the agent has filled
`classification`, `severity`, `effort` (and ideally `evidence_anchor` and
`response_strategy`) on every concern. This script is the deterministic half:
it validates the enums, computes priority scores and response bands,
renders the severity x effort matrix and the per-reviewer plan, and
optionally allocates a per-review character/word budget.

Priority score (documented in references/triage-rubric.md — keep in sync):
    severity   critical=30  major=20  minor=10
    class      misunderstanding=+6  real-flaw=+4  requested-experiment=+3
               clarification=+2     disagreement=+1
    effort     low=+3  medium=+2  high=+1   (quick wins first within a band)

Response band:
    must-address   critical, or major with classification != disagreement
    should-address remaining major, or minor misunderstandings
    brief          everything else

Stdlib only. No network access.

Usage:
    python3 build_matrix.py triage.json [--format md|json] [-o out.md]
        [--budget N] [--budget-unit chars|words] [--allow-incomplete]

Exit codes: 0 ok, 1 validation failure (unclassified/invalid concerns),
2 bad arguments or unreadable input.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

SEV_SCORE = {"critical": 30, "major": 20, "minor": 10}
CLS_SCORE = {
    "misunderstanding": 6,
    "real-flaw": 4,
    "requested-experiment": 3,
    "clarification": 2,
    "disagreement": 1,
}
EFF_SCORE = {"low": 3, "medium": 2, "high": 1}

CLS_LABEL = {
    "misunderstanding": "Misunderstanding",
    "real-flaw": "Real flaw",
    "requested-experiment": "Requested experiment",
    "clarification": "Clarification",
    "disagreement": "Disagreement",
}

# Accept a few human spellings and normalize.
_NORMALIZE = {
    "real flaw": "real-flaw", "flaw": "real-flaw",
    "requested experiment": "requested-experiment",
    "experiment": "requested-experiment",
    "new experiment": "requested-experiment",
    "misreading": "misunderstanding",
    "subjective": "disagreement", "taste": "disagreement",
    "med": "medium", "moderate": "medium",
}


def _norm(value):
    if value is None:
        return None
    v = str(value).strip().lower()
    return _NORMALIZE.get(v, v)


def band_of(severity, classification):
    if severity == "critical":
        return "must-address"
    if severity == "major":
        return ("must-address" if classification != "disagreement"
                else "should-address")
    if severity == "minor" and classification == "misunderstanding":
        return "should-address"
    return "brief"


def priority_of(severity, classification, effort):
    return (SEV_SCORE[severity] + CLS_SCORE[classification]
            + EFF_SCORE[effort])


def validate(doc, allow_incomplete):
    """Returns (concern_rows, problems). Each row gets priority/band added."""
    problems, rows = [], []
    reviewers = doc.get("reviewers")
    if not isinstance(reviewers, list) or not reviewers:
        return [], ["no `reviewers` array in input — is this the JSON from "
                    "parse_reviews.py?"]
    for rev in reviewers:
        for c in rev.get("concerns", []):
            cid = c.get("id", "?")
            cls = _norm(c.get("classification"))
            sev = _norm(c.get("severity"))
            eff = _norm(c.get("effort"))
            errs = []
            if cls not in CLS_SCORE:
                errs.append("classification=%r (allowed: %s)"
                            % (c.get("classification"),
                               "/".join(CLS_SCORE)))
            if sev not in SEV_SCORE:
                errs.append("severity=%r (allowed: %s)"
                            % (c.get("severity"), "/".join(SEV_SCORE)))
            if eff not in EFF_SCORE:
                errs.append("effort=%r (allowed: %s)"
                            % (c.get("effort"), "/".join(EFF_SCORE)))
            row = dict(c)
            row["reviewer_label"] = rev.get("label", rev.get("id", "?"))
            row["reviewer_id"] = rev.get("id", "?")
            if errs:
                problems.append("%s: %s" % (cid, "; ".join(errs)))
                row.update(classification=cls if cls in CLS_SCORE else None,
                           severity=sev if sev in SEV_SCORE else None,
                           effort=eff if eff in EFF_SCORE else None,
                           priority=0, band="unclassified")
                if allow_incomplete:
                    rows.append(row)
            else:
                row.update(classification=cls, severity=sev, effort=eff,
                           priority=priority_of(sev, cls, eff),
                           band=band_of(sev, cls))
                rows.append(row)
    return rows, problems


def _trunc(text, n=110):
    text = " ".join(str(text or "").split()).replace("|", "\\|")
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def allocate_budget(rows, budget, unit):
    """Per-reviewer proportional allocation; 15% reserved for framing."""
    alloc = {}
    by_rev = {}
    for r in rows:
        by_rev.setdefault(r["reviewer_id"], []).append(r)
    step = 50 if unit == "chars" else 10
    for rev_id, items in by_rev.items():
        usable = budget * 0.85
        total = sum(max(r["priority"], 1) for r in items)
        for r in items:
            share = usable * max(r["priority"], 1) / total
            alloc[r["id"]] = max(step, int(round(share / step)) * step)
    return alloc


def render_md(doc, rows, problems, budget, unit):
    out = []
    out.append("# Review triage matrix")
    out.append("")
    out.append("Source: `%s` (platform: %s) — %d reviewer(s), %d concern(s)."
               % (doc.get("source_file", "?"),
                  doc.get("format_detected", "?"),
                  doc.get("reviewer_count", len(doc.get("reviewers", []))),
                  len(rows)))
    out.append("")

    # Per-reviewer summary -------------------------------------------------
    out.append("## Reviewers")
    out.append("")
    out.append("| Reviewer | Role | Scores | Concerns | Misund. | Real flaw "
               "| Experiment | Clarif. | Disagr. |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for rev in doc.get("reviewers", []):
        mine = [r for r in rows if r["reviewer_id"] == rev.get("id")]
        counts = {k: sum(1 for r in mine if r["classification"] == k)
                  for k in CLS_SCORE}
        scores = "; ".join("%s: %s" % (k, v)
                           for k, v in rev.get("scores", {}).items()) or "—"
        out.append("| %s | %s | %s | %d | %d | %d | %d | %d | %d |" % (
            rev.get("label", "?"), rev.get("role", "reviewer"),
            _trunc(scores, 60), len(mine), counts["misunderstanding"],
            counts["real-flaw"], counts["requested-experiment"],
            counts["clarification"], counts["disagreement"]))
    out.append("")

    # Severity x effort grid ----------------------------------------------
    out.append("## Severity × effort grid")
    out.append("")
    out.append("| | Effort: low | Effort: medium | Effort: high |")
    out.append("|---|---|---|---|")
    for sev in ("critical", "major", "minor"):
        cells = []
        for eff in ("low", "medium", "high"):
            ids = [r["id"] for r in rows
                   if r["severity"] == sev and r["effort"] == eff]
            cells.append(", ".join(ids) if ids else "—")
        out.append("| **%s** | %s | %s | %s |" % (sev, *cells))
    out.append("")

    # Full matrix ----------------------------------------------------------
    ordered = sorted(rows, key=lambda r: (-r["priority"], r["id"]))
    out.append("## Concern matrix (highest priority first)")
    out.append("")
    hdr = "| Pri | ID | Reviewer | Class | Sev | Effort | Concern | Strategy |"
    if budget:
        hdr += " Budget |"
    out.append(hdr)
    out.append("|---|---|---|---|---|---|---|---|" + ("---|" if budget else ""))
    alloc = allocate_budget(rows, budget, unit) if budget else {}
    for r in ordered:
        line = "| %d | %s | %s | %s | %s | %s | %s | %s |" % (
            r["priority"], r["id"], _trunc(r["reviewer_label"], 22),
            CLS_LABEL.get(r["classification"], "UNCLASSIFIED"),
            r["severity"] or "—", r["effort"] or "—",
            _trunc(r.get("text")), _trunc(r.get("response_strategy") or "—", 80))
        if budget:
            line += " ~%d %s |" % (alloc.get(r["id"], 0), unit)
        out.append(line)
    out.append("")

    # Response plan ---------------------------------------------------------
    out.append("## Response plan")
    out.append("")
    for band, title in (("must-address", "Must address (acceptance hinges on these)"),
                        ("should-address", "Should address"),
                        ("brief", "Brief acknowledgement / batch at the end"),
                        ("unclassified", "Unclassified — finish triage first")):
        members = [r for r in ordered if r["band"] == band]
        if not members:
            continue
        out.append("### %s" % title)
        out.append("")
        for r in members:
            anchor = (" — evidence: %s" % r["evidence_anchor"]
                      ) if r.get("evidence_anchor") else ""
            out.append("- **%s** [%s, %s/%s] %s%s" % (
                r["id"], CLS_LABEL.get(r["classification"], "UNCLASSIFIED"),
                r["severity"] or "—", r["effort"] or "—",
                _trunc(r.get("response_strategy") or r.get("text"), 130),
                anchor))
        out.append("")

    if budget:
        out.append("Budget: %d %s per review; ~15%% reserved for the "
                   "opening/closing frame. Allocations are guidance, not "
                   "quotas." % (budget, unit))
        out.append("")
    if problems:
        out.append("## Validation problems (rendered with --allow-incomplete)")
        out.append("")
        for p in problems:
            out.append("- %s" % p)
        out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render a classified triage JSON (from parse_reviews.py) "
                    "into a prioritized severity x effort response matrix.")
    ap.add_argument("input", help="triage JSON with classifications filled in")
    ap.add_argument("-o", "--output", help="write report here (default: stdout)")
    ap.add_argument("--format", default="md", choices=["md", "json"],
                    help="output format (default: md)")
    ap.add_argument("--budget", type=int, default=None,
                    help="per-review response budget to allocate "
                         "(e.g. 10000 for NeurIPS OpenReview)")
    ap.add_argument("--budget-unit", default="chars",
                    choices=["chars", "words"], help="unit for --budget")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="render even if some concerns are unclassified")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.input)
    if not path.is_file():
        print("error: input file not found: %s" % path, file=sys.stderr)
        return 2
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print("error: cannot parse %s as JSON: %s" % (path, e),
              file=sys.stderr)
        return 2
    if args.budget is not None and args.budget <= 0:
        print("error: --budget must be a positive integer", file=sys.stderr)
        return 2

    rows, problems = validate(doc, args.allow_incomplete)
    if problems and not args.allow_incomplete:
        print("error: %d concern(s) are unclassified or invalid — fill "
              "classification/severity/effort first (see "
              "references/triage-rubric.md), or pass --allow-incomplete:"
              % len(problems), file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        return 1
    if not rows:
        print("error: no concerns found in %s" % path, file=sys.stderr)
        return 1

    if args.format == "json":
        alloc = (allocate_budget(rows, args.budget, args.budget_unit)
                 if args.budget else {})
        for r in rows:
            if args.budget:
                r["budget"] = {"amount": alloc.get(r["id"], 0),
                               "unit": args.budget_unit}
        payload = json.dumps({
            "source_file": doc.get("source_file"),
            "concerns": sorted(rows, key=lambda r: (-r["priority"], r["id"])),
            "problems": problems,
        }, indent=2, ensure_ascii=False)
    else:
        payload = render_md(doc, rows, problems, args.budget,
                            args.budget_unit)

    if args.output:
        pathlib.Path(args.output).write_text(payload + "\n", encoding="utf-8")
        print("wrote %s" % args.output, file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
