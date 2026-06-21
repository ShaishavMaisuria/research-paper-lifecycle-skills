#!/usr/bin/env python3
"""Parse raw peer-review text into a structured triage JSON skeleton.

Accepts review text pasted or exported from OpenReview, EasyChair, CMT, or
HotCRP (auto-detected, or forced with --format). Splits the text into
reviewers, extracts score fields (rating, confidence, soundness, ...),
canonicalizes sections (summary / strengths / weaknesses / questions /
limitations / comments), and breaks concern-bearing sections into individual
concern items with stable ids (R1.1, R1.2, ...).

The output is a SKELETON: `classification`, `severity`, `effort`,
`evidence_anchor`, and `response_strategy` are emitted as null and must be
filled in by the agent (see references/triage-rubric.md), then rendered with
build_matrix.py.

Stdlib only. No network access. Review text is processed transiently —
never commit it to a repository.

Usage:
    python3 parse_reviews.py reviews.txt [-o triage.json]
        [--format auto|openreview|easychair|cmt|hotcrp] [--min-words N]

Exit codes: 0 ok, 1 no reviews/concerns detected, 2 bad arguments or
unreadable input.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

CLASSIFICATIONS = [
    "misunderstanding",
    "real-flaw",
    "requested-experiment",
    "clarification",
    "disagreement",
]
SEVERITIES = ["critical", "major", "minor"]
EFFORTS = ["low", "medium", "high"]

# ---------------------------------------------------------------------------
# Reviewer-boundary detection
# ---------------------------------------------------------------------------

# (format-hint, regex). A matching LINE starts a new reviewer block; group 1,
# when present, is the reviewer label.
HEADER_PATTERNS = [
    ("openreview", re.compile(
        r"^\s*Official\s+Review\s+of\s+(?:Submission|Paper)\s*#?\d*\s+by\s+(.+?)\s*$",
        re.I)),
    ("easychair", re.compile(
        r"^\s*-{3,}\s*REVIEW\s+(\d+)\s*-{3,}\s*$", re.I)),
    ("hotcrp", re.compile(
        r"^\s*[=*]*\s*Review\s+#(\d+[A-Z]\d*)\b.*$")),
    ("cmt", re.compile(
        r"^\s*Reviewer\s*#\s*(\d+)\s*[:\-]?\s*$", re.I)),
    ("openreview", re.compile(
        r"^\s*(Reviewer\s+[A-Za-z0-9]{4}(?:\s*\(.*\))?)\s*$")),
    ("generic", re.compile(
        r"^\s*(?:={3,}\s*)?Review(?:er)?\s*#?\s*(\d+)\s*(?:={3,})?\s*[:\-]?\s*$",
        re.I)),
    ("meta", re.compile(
        r"^\s*[-=]*\s*(Meta[- ]?Review(?:er)?(?:\s+by\s+.+?)?|Area\s+Chair(?:\s+.+?)?)\s*[-=:]*\s*$",
        re.I)),
]

# ---------------------------------------------------------------------------
# Section canonicalization
# ---------------------------------------------------------------------------

SECTION_ALIASES = {
    "summary": [
        "summary", "paper summary", "summary of the paper",
        "summary of contributions", "summary and contributions",
        "brief summary",
    ],
    "strengths": [
        "strengths", "strong points", "pros", "reasons to accept",
        "positives", "strengths of the paper",
    ],
    "weaknesses": [
        "weaknesses", "weak points", "cons", "reasons to reject",
        "major weaknesses", "minor weaknesses", "concerns",
        "major concerns", "minor concerns", "major comments",
        "minor comments", "weaknesses of the paper",
    ],
    "questions": [
        "questions", "questions for the authors", "questions to the authors",
        "questions for authors", "questions to authors", "clarifications",
        "clarification questions", "questions and suggestions",
    ],
    "limitations": [
        "limitations", "limitations and societal impact", "societal impact",
        "ethics", "ethical concerns", "ethics review", "ethics flag",
    ],
    "comments": [
        "comments", "detailed comments", "comments for authors",
        "comments to authors", "comments for author",
        "comments to the authors", "comments for the authors",
        "additional comments", "other comments", "overall evaluation",
        "detailed review", "additional feedback", "suggestions",
        "minor issues", "typos", "strengths and weaknesses",
        "comments, suggestions and typos",
    ],
}
_ALIAS_TO_CANON = {a: c for c, names in SECTION_ALIASES.items() for a in names}

# Sections mined for individual concerns (summary/strengths are context only).
CONCERN_SECTIONS = ["weaknesses", "questions", "limitations", "comments", "other"]

SCORE_FIELDS = {
    "rating", "overall rating", "overall evaluation", "overall merit",
    "overall score", "score", "overall", "confidence",
    "reviewer's confidence", "reviewer confidence", "reviewer expertise",
    "expertise", "soundness", "presentation", "contribution", "novelty",
    "significance", "technical quality", "clarity", "originality",
    "reproducibility", "recommendation", "overall recommendation",
    "correctness", "impact", "relevance",
}

# Submission metadata echoed into review exports (EasyChair/CMT) — not concerns.
IGNORE_FIELDS = {"paper", "paper id", "title", "authors", "submission",
                 "track", "subject areas", "keywords"}

_FIELD_LINE = re.compile(r"^\s*[-=*#]*\s*([A-Za-z][A-Za-z' ,/]{1,40}?)\s*:\s*(.*)$")
_DECORATION = re.compile(r"^\s*[-=_*#~+]{3,}\s*$")
_BANNER_LINE = re.compile(r"^\s*[-=*#]{0,40}\s*([A-Za-z][A-Za-z' ,/&]{1,40}?)\s*[-=*#:]{0,40}\s*$")

_ITEM_MARKER = re.compile(
    r"^\s*(?:[-*•+]\s+|\(?\d{1,2}[.)]\s+|[WQCwqc]\d{1,2}\s*[:.)]\s+)")


def _norm_heading(s):
    s = re.sub(r"[-=*#_]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip(":").strip().lower()
    return s


def _looks_like_score(value):
    v = value.strip()
    if not v or len(v) > 120:
        return False
    if re.match(r"^[+-]?\d", v):
        return True
    return v.lower() in {
        "accept", "reject", "weak accept", "weak reject", "borderline",
        "strong accept", "strong reject", "high", "medium", "low",
    }


def detect_format(text):
    """Best-effort platform detection; returns (name, scores-dict)."""
    weights = {
        "openreview": [
            (r"Official Review of", 4), (r"^\s*Soundness\s*:", 2),
            (r"^\s*Presentation\s*:", 2), (r"^\s*Contribution\s*:", 2),
            (r"acceptance threshold", 2), (r"^\s*Rating\s*:", 1),
            (r"^\s*Reviewer\s+[A-Za-z0-9]{4}\s*$", 2),
        ],
        "easychair": [
            (r"-{3,}\s*REVIEW\s+\d+\s*-{3,}", 4),
            (r"OVERALL EVALUATION\s*:", 3),
            (r"REVIEWER'S CONFIDENCE\s*:", 3),
        ],
        "hotcrp": [
            (r"Review\s+#\d+[A-Z]\b", 4), (r"Overall merit\s*:", 3),
            (r"Reviewer expertise\s*:", 3), (r"Comments for author", 2),
        ],
        "cmt": [
            (r"^\s*Reviewer\s*#\s*\d+\s*$", 3), (r"Meta-?Reviewer", 2),
            (r"^\s*Q\d+[.:]", 1),
        ],
    }
    scores = {}
    for fmt, pats in weights.items():
        scores[fmt] = sum(
            w * len(re.findall(p, text, re.I | re.M)) for p, w in pats)
    best = max(scores, key=lambda k: scores[k])
    return (best if scores[best] > 0 else "unknown"), scores


def split_reviewers(lines, forced_format):
    """Return list of (label, role, [lines]) blocks."""
    blocks = []
    current_label, current_role, current = None, "reviewer", []

    def flush():
        if current_label is not None or any(l.strip() for l in current):
            blocks.append((current_label, current_role, list(current)))

    for line in lines:
        matched = None
        for hint, pat in HEADER_PATTERNS:
            if forced_format not in ("auto", None) and hint not in (
                    forced_format, "generic", "meta"):
                continue
            m = pat.match(line)
            if m:
                matched = (hint, m)
                break
        if matched:
            hint, m = matched
            flush()
            label = (m.group(1) or "").strip() if m.groups() else ""
            if hint == "easychair" or (hint == "generic" and label.isdigit()):
                label = "Review %s" % label
            elif hint == "hotcrp":
                label = "Review #%s" % label
            elif hint == "cmt" and label.isdigit():
                label = "Reviewer #%s" % label
            current_label = label or "Review %d" % (len(blocks) + 1)
            current_role = "meta" if hint == "meta" else "reviewer"
            current = []
        else:
            current.append(line)
    flush()

    # Drop a label-less preamble block (paper title etc.) when real blocks
    # follow; otherwise treat the whole text as a single unlabeled review.
    labeled = [b for b in blocks if b[0] is not None]
    if labeled:
        return labeled
    return [("Review 1", "reviewer", blocks[0][2])] if blocks else []


def parse_block(lines):
    """One reviewer block -> (scores, sections{canon: text}, headings_seen)."""
    scores = {}
    sections = {}
    headings = {}
    cur_canon, cur_heading = "other", None
    buf = {}

    def emit(canon, text_lines):
        text = "\n".join(text_lines).strip("\n")
        if text.strip():
            buf.setdefault(canon, []).append(text)

    pending = []
    for line in lines:
        if _DECORATION.match(line):
            continue  # pure ----/==== decoration lines
        m = _FIELD_LINE.match(line)
        if m:
            name, value = _norm_heading(m.group(1)), m.group(2).strip()
            if name in IGNORE_FIELDS and value:
                continue  # PAPER:/TITLE:/AUTHORS: metadata echoes
            if name in SCORE_FIELDS and _looks_like_score(value):
                scores[name] = value
                continue
            if name in _ALIAS_TO_CANON:
                emit(cur_canon, pending)
                pending = [value] if value else []
                cur_canon, cur_heading = _ALIAS_TO_CANON[name], m.group(1).strip()
                headings.setdefault(cur_canon, cur_heading)
                continue
        b = _BANNER_LINE.match(line)
        if b:
            name = _norm_heading(b.group(1))
            if name in _ALIAS_TO_CANON:
                emit(cur_canon, pending)
                pending = []
                cur_canon, cur_heading = _ALIAS_TO_CANON[name], b.group(1).strip()
                headings.setdefault(cur_canon, cur_heading)
                continue
            if name in SCORE_FIELDS:
                continue  # bare score banner with no value — ignore
        pending.append(line)
    emit(cur_canon, pending)

    for canon, parts in buf.items():
        sections[canon] = "\n\n".join(parts)
    return scores, sections, headings


def extract_items(section_text, min_words):
    """Split a section into individual concern texts."""
    lines = section_text.split("\n")
    marker_idx = [i for i, l in enumerate(lines) if _ITEM_MARKER.match(l)]
    items = []
    if len(marker_idx) >= 2:
        preamble = "\n".join(lines[:marker_idx[0]]).strip()
        if preamble:
            items.append(preamble)
        bounds = marker_idx + [len(lines)]
        for a, b in zip(bounds[:-1], bounds[1:]):
            chunk = lines[a:b]
            chunk[0] = _ITEM_MARKER.sub("", chunk[0])
            items.append("\n".join(chunk).strip())
    else:
        items = [_ITEM_MARKER.sub("", p.strip(), count=1)
                 for p in re.split(r"\n\s*\n", section_text)]

    out = []
    for it in items:
        text = re.sub(r"\s+", " ", it).strip()
        if text and len(text.split()) >= min_words:
            out.append(text)
    return out


def build_skeleton(raw_text, source, forced_format, min_words):
    fmt, fmt_scores = detect_format(raw_text)
    if forced_format not in ("auto", None):
        fmt = forced_format
    blocks = split_reviewers(raw_text.split("\n"), forced_format)

    reviewers, concern_total = [], 0
    for ri, (label, role, lines) in enumerate(blocks, 1):
        scores, sections, headings = parse_block(lines)
        rid = "R%d" % ri
        concerns = []
        for canon in CONCERN_SECTIONS:
            if canon not in sections:
                continue
            for text in extract_items(sections[canon], min_words):
                concern_total += 1
                concerns.append({
                    "id": "%s.%d" % (rid, len(concerns) + 1),
                    "reviewer": label,
                    "source_section": canon,
                    "source_heading": headings.get(canon),
                    "text": text,
                    "classification": None,
                    "severity": None,
                    "effort": None,
                    "evidence_anchor": None,
                    "response_strategy": None,
                    "notes": None,
                })
        reviewers.append({
            "id": rid,
            "label": label,
            "role": role,
            "scores": scores,
            "sections": sections,
            "concerns": concerns,
        })

    return {
        "source_file": source,
        "format_detected": fmt,
        "format_signal_scores": fmt_scores,
        "reviewer_count": len(reviewers),
        "concern_count": concern_total,
        "schema": {
            "classification": CLASSIFICATIONS,
            "severity": SEVERITIES,
            "effort": EFFORTS,
        },
        "reviewers": reviewers,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Parse raw OpenReview/EasyChair/CMT/HotCRP review text "
                    "into a structured triage JSON skeleton.")
    ap.add_argument("input", help="text file with the raw reviews")
    ap.add_argument("-o", "--output",
                    help="write JSON here (default: stdout)")
    ap.add_argument("--format", default="auto",
                    choices=["auto", "openreview", "easychair", "cmt", "hotcrp"],
                    help="force the source platform (default: auto-detect)")
    ap.add_argument("--min-words", type=int, default=6,
                    help="ignore concern fragments shorter than N words "
                         "(default: 6)")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.input)
    if not path.is_file():
        print("error: input file not found: %s" % path, file=sys.stderr)
        return 2
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print("error: cannot read %s: %s" % (path, e), file=sys.stderr)
        return 2
    if not raw.strip():
        print("error: %s is empty — paste the review text into it first"
              % path, file=sys.stderr)
        return 1

    doc = build_skeleton(raw, str(path), args.format, args.min_words)
    if doc["reviewer_count"] == 0 or doc["concern_count"] == 0:
        print("error: no reviews/concerns detected (format guess: %s). "
              "Check the paste, or retry with --format / --min-words 3."
              % doc["format_detected"], file=sys.stderr)
        return 1

    payload = json.dumps(doc, indent=2, ensure_ascii=False)
    if args.output:
        pathlib.Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    print("parsed %d reviewer(s), %d concern(s) [format: %s] -> %s"
          % (doc["reviewer_count"], doc["concern_count"],
             doc["format_detected"], args.output or "stdout"),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
