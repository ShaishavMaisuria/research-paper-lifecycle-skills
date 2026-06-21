#!/usr/bin/env python3
"""Emit a venue-calibrated simulated-review form skeleton — stdlib only.

Reads a venue profile YAML (venues/conferences/<venue>.yml, merging its
family file from venues/families/), maps the venue family to a calibrated
reviewer panel (personas, harshness, score scale, review-form fields), and
prints the review-packet skeleton the agent fills in — as markdown (default)
or JSON (--json).

This script is deterministic and makes NO network calls. Scale anchors are
historical norms: the agent MUST re-verify them (and everything else) against
the live CFP / reviewer guidelines before the user relies on them.

Usage:
    python3 review_form.py venues/conferences/neurips-2026.yml --track Main
    python3 review_form.py venues/conferences/sigspatial-2026.yml \
        --track Demo --json

Exit codes: 0 ok, 2 bad arguments / missing or unparsable profile.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# YAML-subset parsing (same proven subset parser used across this repo's
# skills: nested mappings, block lists, inline lists, quoted scalars,
# `>`/`|` block scalars, comments). NOT a general YAML parser.
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$")


class ProfileError(Exception):
    """Raised on any parse/load problem; message is user-facing."""


def _cut_comment(s: str) -> str:
    out: list[str] = []
    in_s = in_d = False
    i = 0
    while i < len(s):
        c = s[i]
        if in_d:
            if c == "\\" and i + 1 < len(s):
                out.append(s[i : i + 2])
                i += 2
                continue
            if c == '"':
                in_d = False
            out.append(c)
        elif in_s:
            if c == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    out.append("''")
                    i += 2
                    continue
                in_s = False
            out.append(c)
        else:
            if c == '"':
                in_d = True
            elif c == "'":
                in_s = True
            elif c == "#" and (not out or out[-1] in " \t"):
                break
            out.append(c)
        i += 1
    return "".join(out)


def _read_quoted(v: str) -> str:
    q = v[0]
    body: list[str] = []
    i = 1
    while i < len(v):
        c = v[i]
        if q == '"' and c == "\\" and i + 1 < len(v):
            nxt = v[i + 1]
            body.append(nxt if nxt in ('"', "\\") else "\\" + nxt)
            i += 2
            continue
        if q == "'" and c == "'":
            if i + 1 < len(v) and v[i + 1] == "'":
                body.append("'")
                i += 2
                continue
            break
        if q == '"' and c == '"':
            break
        body.append(c)
        i += 1
    return "".join(body)


def _parse_scalar(v: str):
    v = v.strip()
    if v == "" or v in ("~", "null", "Null", "NULL"):
        return None
    if v[0] in ("'", '"'):
        return _read_quoted(v)
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in inner.split(",")]
    try:
        return int(v)
    except ValueError:
        return v


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_content(lines: list[str], i: int) -> int:
    while i < len(lines):
        cut = _cut_comment(lines[i])
        if cut.strip():
            return i
        i += 1
    return len(lines)


def _consume_block_scalar(lines: list[str], i: int, indent: int, marker: str):
    collected: list[str] = []
    while i < len(lines):
        raw = lines[i]
        if raw.strip() == "":
            collected.append("")
            i += 1
            continue
        if _indent(raw) <= indent:
            break
        collected.append(raw)
        i += 1
    while collected and collected[-1] == "":
        collected.pop()
    nonblank = [ln for ln in collected if ln.strip()]
    if not nonblank:
        return "", i
    dedent = min(_indent(ln) for ln in nonblank)
    body = [ln[dedent:] if ln.strip() else "" for ln in collected]
    if marker.startswith("|"):
        text = "\n".join(body)
    else:
        text = " ".join(ln.strip() for ln in body if ln.strip())
    return text.strip(), i


def _parse_node(lines: list[str], i: int, min_indent: int):
    j = _next_content(lines, i)
    if j >= len(lines):
        return None, j
    ind = _indent(_cut_comment(lines[j]))
    if ind < min_indent:
        return None, j
    stripped = _cut_comment(lines[j]).strip()
    if stripped == "-" or stripped.startswith("- "):
        return _parse_list(lines, j, ind)
    return _parse_mapping(lines, j, ind)


def _parse_mapping(lines: list[str], i: int, indent: int):
    data: dict = {}
    while True:
        j = _next_content(lines, i)
        if j >= len(lines):
            return data, j
        cut = _cut_comment(lines[j])
        ind = _indent(cut)
        if ind != indent:
            return data, j
        stripped = cut.strip()
        if stripped.startswith("- "):
            return data, j
        m = _KEY_RE.match(stripped)
        if not m:
            raise ProfileError(f"line {j + 1}: cannot parse mapping line: {stripped!r}")
        key, vt = m.group(1), (m.group(2) or "").strip()
        if vt in (">", ">-", "|", "|-"):
            data[key], i = _consume_block_scalar(lines, j + 1, indent, vt)
        elif vt == "":
            k = _next_content(lines, j + 1)
            if k < len(lines) and _indent(_cut_comment(lines[k])) > indent:
                data[key], i = _parse_node(lines, j + 1, indent + 1)
            else:
                data[key], i = None, j + 1
        else:
            data[key], i = _parse_scalar(vt), j + 1


def _parse_list(lines: list[str], i: int, indent: int):
    items: list = []
    while True:
        j = _next_content(lines, i)
        if j >= len(lines):
            return items, j
        cut = _cut_comment(lines[j])
        ind = _indent(cut)
        stripped = cut.strip()
        if ind != indent or not (stripped == "-" or stripped.startswith("- ")):
            return items, j
        content = stripped[1:].strip()
        if content and _KEY_RE.match(content):
            lines[j] = " " * (indent + 2) + content
            item, i = _parse_mapping(lines, j, indent + 2)
            items.append(item)
        else:
            items.append(_parse_scalar(content))
            i = j + 1


def parse_yaml(text: str):
    lines = text.splitlines()
    value, _ = _parse_node(lines, 0, 0)
    return value


def _deep_merge(base, over):
    """Conference values win, except explicit nulls fall back to family."""
    if over is None:
        return base
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _deep_merge(base.get(k), v)
        return out
    return over


def find_venues_dir(venue_path: pathlib.Path):
    for parent in venue_path.resolve().parents:
        if (parent / "families").is_dir() or (parent / "schema.yml").is_file():
            return parent
        if (parent / "venues" / "families").is_dir():
            return parent / "venues"
    return None


def load_profile(venue_path, venues_dir=None):
    """Load a conference profile, merging its family profile if present."""
    path = pathlib.Path(venue_path)
    if not path.is_file():
        raise ProfileError(f"venue profile not found: {path}")
    try:
        prof = parse_yaml(path.read_text(encoding="utf-8"))
    except ProfileError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ProfileError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(prof, dict):
        raise ProfileError(f"{path}: top level is not a mapping")

    notes: list[str] = []
    family = prof.get("family")
    if family:
        vdir = pathlib.Path(venues_dir) if venues_dir else find_venues_dir(path)
        fam_path = vdir / "families" / f"{family}.yml" if vdir else None
        if fam_path and fam_path.is_file():
            fam = parse_yaml(fam_path.read_text(encoding="utf-8"))
            if isinstance(fam, dict):
                merged = _deep_merge(fam, prof)
                merged["id"] = prof.get("id", merged.get("id"))
                prof = merged
                notes.append(f"merged family profile: {fam_path}")
        else:
            notes.append(
                f"family '{family}' profile not found (pass --venues-dir); "
                "using the conference profile alone"
            )
    return prof, notes


def pick_track(profile: dict, name):
    tracks = profile.get("tracks") or []
    tracks = [t for t in tracks if isinstance(t, dict)]
    if not tracks:
        return None, "profile lists no tracks; track calibration skipped"
    if name:
        hits = [t for t in tracks if name.lower() in str(t.get("name", "")).lower()]
        if len(hits) == 1:
            return hits[0], f"track: {hits[0].get('name')}"
        if not hits:
            avail = ", ".join(str(t.get("name")) for t in tracks)
            raise ProfileError(f"no track matches '{name}'; available: {avail}")
        avail = ", ".join(str(t.get("name")) for t in hits)
        raise ProfileError(f"--track '{name}' is ambiguous: {avail}")
    return tracks[0], (
        f"no --track given; defaulted to first track '{tracks[0].get('name')}'"
        + (f" of {len(tracks)}" if len(tracks) > 1 else "")
    )


# ---------------------------------------------------------------------------
# Calibration data: rubric, score scales, per-family reviewer panels
# ---------------------------------------------------------------------------

RUBRIC_SCALE = {"min": 1, "max": 5, "note": "per-dimension rubric subscores; anchors in references/rubrics.md"}

CORE_DIMENSIONS = [
    {
        "id": "novelty",
        "name": "Novelty / originality",
        "question": "Is the contribution new relative to the closest prior work, and is the delta articulated honestly?",
    },
    {
        "id": "soundness",
        "name": "Technical soundness",
        "question": "Do the claims follow from the evidence (proofs, experiments, baselines, ablations, statistics)?",
    },
    {
        "id": "reproducibility",
        "name": "Reproducibility",
        "question": "Could a competent reader re-implement and reproduce the results from what the paper (and stated artifacts) provide?",
    },
    {
        "id": "clarity",
        "name": "Clarity / presentation",
        "question": "Can the target reader follow the problem, method, and results without re-reading; are figures/tables/notation clean?",
    },
]

_ML10_SCALE = {
    "id": "ml-conf-10",
    "min": 1,
    "max": 10,
    "borderline_threshold": 6,
    "labels": {
        "1": "Trivial or wrong",
        "2": "Strong reject",
        "3": "Clear reject",
        "4": "Reject",
        "5": "Borderline reject",
        "6": "Borderline accept (marginally above threshold)",
        "7": "Accept",
        "8": "Strong accept",
        "9": "Very strong accept",
        "10": "Award quality",
    },
    "confidence": "1-5 reviewer confidence (5 = absolutely certain)",
    "note": (
        "HISTORICAL NORM for NeurIPS-style venues; anchors and even the "
        "numeric range change year to year (ICLR has used 1/3/5/6/8/10). "
        "Re-verify against the current reviewer guidelines."
    ),
}

_CONF_6_SCALE = {
    "id": "pc-conf-6",
    "min": 1,
    "max": 6,
    "borderline_threshold": 4,
    "labels": {
        "1": "Strong reject",
        "2": "Reject",
        "3": "Weak reject",
        "4": "Weak accept",
        "5": "Accept",
        "6": "Strong accept",
    },
    "confidence": "1-4 reviewer expertise (4 = expert)",
    "note": (
        "Generic PC-style scale; the real form is submission-system dependent "
        "(EasyChair -3..+3, HotCRP 1-5 overall merit, CMT venue-defined). "
        "Re-verify against the venue's actual review form."
    ),
}

_CHI_5_SCALE = {
    "id": "chi-5",
    "min": 1,
    "max": 5,
    "borderline_threshold": 3.5,
    "labels": {
        "5": "A — Accept",
        "4": "ARR — Accept with required (minor) revisions",
        "3": "RR — Revise & Resubmit (5-week revision cycle)",
        "2": "RRX — R&R unlikely to succeed",
        "1": "X — Reject",
    },
    "confidence": "1-4 reviewer expertise (4 = expert)",
    "note": (
        "CHI 2026 uses a 5-point A/ARR/RR/RRX/X scale with a single-round "
        "Revise & Resubmit; up to ~50% of R&R papers are still rejected in "
        "round 2, so treat RR as genuinely borderline. Re-verify against the "
        "current CHI guide to reviewing."
    ),
}

_JOURNAL_4_SCALE = {
    "id": "journal-4",
    "min": 1,
    "max": 4,
    "borderline_threshold": 2.5,
    "labels": {
        "4": "Accept",
        "3": "Minor revision",
        "2": "Major revision",
        "1": "Reject",
    },
    "confidence": "1-4 reviewer expertise (4 = expert)",
    "note": (
        "Standard journal recommendation categories; 'major revision' is the "
        "borderline band — it keeps the paper alive but usually adds a full "
        "review cycle. Re-verify against the journal's reviewer form."
    ),
}

DEFAULT_FORM_FIELDS = [
    "summary (in the reviewer's own words — misreadings here are diagnostic)",
    "strengths (bulleted, specific)",
    "weaknesses (bulleted; each grounded in a quoted line or section number)",
    "questions for the authors (answerable in a rebuttal)",
    "rubric subscores (novelty / soundness / reproducibility / clarity, 1-5)",
    "overall score (venue scale)",
    "confidence / expertise",
]

FAMILY_CALIBRATION = {
    "neurips-style": {
        "label": "NeurIPS-style ML conference (OpenReview, double-blind, threaded rebuttal)",
        "harshness": 5,
        "meta_role": "Area Chair (AC) — writes the meta-review, hunts for a champion among reviewers",
        "scale": _ML10_SCALE,
        "form_fields": DEFAULT_FORM_FIELDS
        + ["limitations & societal impact assessment (checklist-aware)"],
        "personas": [
            {
                "id": "R1",
                "archetype": "The Methods Purist",
                "harshness": 4,
                "emphasis": ["soundness", "novelty"],
                "stance": "Theory-first; trusts nothing that is not proven or ablated.",
                "hunts": [
                    "assumptions used but never stated",
                    "claims stronger than what the theorem/experiment shows",
                    "notation abuse, undefined symbols, hand-wavy 'it can be shown'",
                ],
            },
            {
                "id": "R2",
                "archetype": "The Empirical Skeptic",
                "harshness": 5,
                "emphasis": ["soundness", "reproducibility"],
                "stance": "Classic harsh Reviewer 2; assumes results are cherry-picked until proven otherwise.",
                "hunts": [
                    "missing or stale baselines; unfair tuning budgets",
                    "single-seed results, no error bars, no significance tests",
                    "benchmark selection that conveniently omits the hard datasets",
                    "missing ablations for every claimed component",
                ],
            },
            {
                "id": "R3",
                "archetype": "The Overloaded Skimmer",
                "harshness": 3,
                "emphasis": ["clarity"],
                "stance": "Six papers due tonight; reads abstract, intro, figures, tables, conclusion. If the paper can be misread, this reviewer misreads it.",
                "hunts": [
                    "contribution not findable in the first two pages",
                    "figure 1 that does not explain the method",
                    "tables whose best numbers are not the paper's",
                ],
            },
            {
                "id": "R4",
                "archetype": "The Adjacent-Field Expert",
                "harshness": 4,
                "emphasis": ["novelty"],
                "stance": "Knows the neighboring literature better than the authors; allergic to inflated novelty claims.",
                "hunts": [
                    "'first to do X' claims with plausible prior art",
                    "missing related-work threads from adjacent communities",
                    "the 'this is just X + Y' reduction",
                ],
            },
        ],
    },
    "acm-sigconf": {
        "label": "ACM SIG conference (sigconf proceedings; DB/KDD/Web/GIS culture)",
        "harshness": 4,
        "meta_role": "PC meta-reviewer / discussion lead — reconciles reviews, drafts the summary",
        "scale": _CONF_6_SCALE,
        "form_fields": DEFAULT_FORM_FIELDS,
        "personas": [
            {
                "id": "R1",
                "archetype": "The Baseline Hawk",
                "harshness": 4,
                "emphasis": ["soundness", "novelty"],
                "stance": "Demands comparison against the strongest published system, not a strawman.",
                "hunts": [
                    "missing comparison to the current best-known method",
                    "non-standard benchmarks where standard ones exist",
                    "speedups reported against unoptimized baselines",
                ],
            },
            {
                "id": "R2",
                "archetype": "The Scalability Skeptic",
                "harshness": 4,
                "emphasis": ["soundness"],
                "stance": "Systems mindset: toy data proves nothing.",
                "hunts": [
                    "experiments only on small or synthetic datasets",
                    "no complexity analysis or scalability experiment",
                    "real-world deployment claims without real-world data",
                ],
            },
            {
                "id": "R3",
                "archetype": "The Artifact Reviewer",
                "harshness": 3,
                "emphasis": ["reproducibility", "clarity"],
                "stance": "Reads with the reproducibility committee's checklist in mind (SIGMOD ARI culture).",
                "hunts": [
                    "no code/data availability statement",
                    "missing parameter settings, hardware, or dataset versions",
                    "results that depend on private data with no fallback",
                ],
            },
        ],
    },
    "ieee-conf": {
        "label": "IEEE conference (CMT-style review, often with a revision round)",
        "harshness": 4,
        "meta_role": "PC meta-reviewer — for revision-round venues (ICDE) drafts the required-changes list",
        "scale": _CONF_6_SCALE,
        "form_fields": DEFAULT_FORM_FIELDS
        + ["required changes for the revision round (if the venue has one)"],
        "personas": [
            {
                "id": "R1",
                "archetype": "The Baseline Hawk",
                "harshness": 4,
                "emphasis": ["soundness", "novelty"],
                "stance": "Demands comparison against the strongest published system, not a strawman.",
                "hunts": [
                    "missing comparison to the current best-known method",
                    "evaluation metrics chosen to flatter the approach",
                ],
            },
            {
                "id": "R2",
                "archetype": "The Scalability Skeptic",
                "harshness": 4,
                "emphasis": ["soundness"],
                "stance": "Systems mindset: toy data proves nothing.",
                "hunts": [
                    "experiments only on small or synthetic datasets",
                    "no complexity analysis or scalability experiment",
                ],
            },
            {
                "id": "R3",
                "archetype": "The Revision-Round Planner",
                "harshness": 3,
                "emphasis": ["reproducibility", "clarity"],
                "stance": "Writes reviews as a concrete, checkable list of required changes.",
                "hunts": [
                    "fixable-but-unfixed gaps (missing experiment, unclear section)",
                    "claims that need softening rather than new work",
                    "missing statements the venue mandates (e.g. AI-use acknowledgement)",
                ],
            },
        ],
    },
    "acm-manuscript-chi": {
        "label": "CHI-style SIGCHI venue (1AC/2AC + externals, Revise & Resubmit)",
        "harshness": 4,
        "meta_role": "1AC — knows author identities, synthesizes reviews, weighs contribution relative to length",
        "scale": _CHI_5_SCALE,
        "form_fields": DEFAULT_FORM_FIELDS
        + ["contribution-vs-length judgment (CHI has no hard page limit)"],
        "personas": [
            {
                "id": "2AC",
                "archetype": "The Methods Rigorist (2AC)",
                "harshness": 4,
                "emphasis": ["soundness"],
                "stance": "Study-design first: sampling, power, IRB/ethics, stats or qualitative-coding rigor.",
                "hunts": [
                    "underpowered studies presented as conclusive",
                    "missing ethics/IRB statement for human-subjects work",
                    "quant stats misapplied; qual claims without coding methodology",
                ],
            },
            {
                "id": "Ext1",
                "archetype": "The Contribution Skeptic",
                "harshness": 4,
                "emphasis": ["novelty", "clarity"],
                "stance": "Asks 'what does the HCI community learn from this?' and expects the framing to answer it.",
                "hunts": [
                    "implications-for-design sections that restate the findings",
                    "novelty claims relative to a thin slice of related work",
                ],
            },
            {
                "id": "Ext2",
                "archetype": "The Generalizability Prober",
                "harshness": 3,
                "emphasis": ["soundness", "reproducibility"],
                "stance": "Probes whether findings travel beyond the studied population/context.",
                "hunts": [
                    "WEIRD-sample findings stated as universal",
                    "limitations section that dodges the real limitation",
                ],
            },
        ],
    },
    "lncs": {
        "label": "Springer LNCS venue (3 shortish reviews, single-blind common)",
        "harshness": 3,
        "meta_role": "PC chair summary",
        "scale": _CONF_6_SCALE,
        "form_fields": DEFAULT_FORM_FIELDS,
        "personas": [
            {
                "id": "R1",
                "archetype": "The Correctness Checker",
                "harshness": 3,
                "emphasis": ["soundness"],
                "stance": "Verifies the core technical claim; short, pointed reviews.",
                "hunts": ["the one lemma/experiment the paper actually rests on"],
            },
            {
                "id": "R2",
                "archetype": "The Prior-Work Mapper",
                "harshness": 3,
                "emphasis": ["novelty"],
                "stance": "Places the paper against the venue's own recent proceedings.",
                "hunts": ["overlap with last year's papers at the same venue"],
            },
            {
                "id": "R3",
                "archetype": "The Fit-and-Clarity Reader",
                "harshness": 2,
                "emphasis": ["clarity"],
                "stance": "Judges scope fit and readability for the venue audience.",
                "hunts": ["scope mismatch with the CFP topics", "impenetrable notation"],
            },
        ],
    },
    "ieee-journal": {
        "label": "IEEE journal (TKDE-style; AE + 3 reviewers, revision cycles)",
        "harshness": 4,
        "meta_role": "Associate Editor — converts reviews into a decision letter with a mandatory-changes list",
        "scale": _JOURNAL_4_SCALE,
        "form_fields": DEFAULT_FORM_FIELDS
        + ["delta over any prior conference version (journals require substantial extension)"],
        "personas": [
            {
                "id": "R1",
                "archetype": "The Completeness Reviewer",
                "harshness": 4,
                "emphasis": ["soundness", "novelty"],
                "stance": "Expects journal depth: full proofs, extended experiments, complete treatment.",
                "hunts": [
                    "conference-length evaluation in a journal submission",
                    "insufficient delta over the authors' own conference version",
                ],
            },
            {
                "id": "R2",
                "archetype": "The Detail Auditor",
                "harshness": 4,
                "emphasis": ["soundness", "clarity"],
                "stance": "Line-by-line audit; produces numbered, fixable comment lists (the major-revision machine).",
                "hunts": [
                    "equation/figure/table inconsistencies",
                    "every unsupported sentence in the abstract and conclusion",
                ],
            },
            {
                "id": "R3",
                "archetype": "The Positioning Reviewer",
                "harshness": 3,
                "emphasis": ["novelty", "reproducibility"],
                "stance": "Checks the survey of related work is current and the contribution is honestly placed.",
                "hunts": ["related work that stops two years ago", "missing reproducibility material"],
            },
        ],
    },
}
# ACM journals review like IEEE journals for simulation purposes.
FAMILY_CALIBRATION["acm-journal"] = dict(
    FAMILY_CALIBRATION["ieee-journal"],
    label="ACM journal (TODS-style; AE + 3 reviewers, revision cycles)",
)

DEFAULT_CALIBRATION = {
    "label": "Generic peer-reviewed venue (family not recognized — calibration is a guess)",
    "harshness": 3,
    "meta_role": "Meta-reviewer summary",
    "scale": _CONF_6_SCALE,
    "form_fields": DEFAULT_FORM_FIELDS,
    "personas": FAMILY_CALIBRATION["acm-sigconf"]["personas"],
}

# Track-name substrings -> calibration adjustments. First match wins.
TRACK_MODIFIERS = [
    (
        ("demo", "poster"),
        {
            "harshness_delta": -2,
            "max_reviewers": 2,
            "note": (
                "Demo/poster-track calibration: fewer, lighter reviews. Judges ask "
                "'will attendees learn something / does it actually run', not "
                "'is this a complete research contribution'. Novelty bar is "
                "lower; a working, well-explained artifact beats a grand claim."
            ),
            "extra_questions": [
                "Does the paper say what a visitor will see and do during the demo?",
                "Is the system plausibly functional (screenshots, link, architecture)?",
            ],
        },
    ),
    (
        ("short",),
        {
            "harshness_delta": -1,
            "note": (
                "Short-paper calibration: contribution judged relative to length; "
                "reviewers punish a long paper squeezed into short form more than "
                "a genuinely small, crisp idea."
            ),
            "extra_questions": [
                "Is this a complete small contribution, or a truncated full paper?"
            ],
        },
    ),
    (
        ("industrial", "industry", "application", "applied"),
        {
            "harshness_delta": -1,
            "note": (
                "Industry/applications-track calibration: novelty bar lower, "
                "deployment-evidence bar higher. Reviewers want real systems, "
                "real data, lessons learned — not a research paper in disguise."
            ),
            "extra_questions": [
                "Is there evidence of real deployment or real users/data?",
                "Are the lessons learned actionable for practitioners?",
            ],
        },
    ),
    (
        ("vision", "blue sky", "blue-sky"),
        {
            "harshness_delta": -1,
            "note": (
                "Vision-track calibration: judged on boldness, argument quality, "
                "and community impact of the proposed direction — not on "
                "completed experiments."
            ),
            "extra_questions": [
                "Is the vision genuinely forward-looking rather than a survey?",
                "Does the paper argue feasibility and a research agenda?",
            ],
        },
    ),
]


def calibrate(profile: dict, track):
    """Build the calibration block for a merged profile + resolved track."""
    notes: list[str] = []
    family = str(profile.get("family") or "")
    cal = FAMILY_CALIBRATION.get(family)
    if cal is None:
        cal = DEFAULT_CALIBRATION
        notes.append(
            f"family '{family or '(none)'}' has no calibration entry; using the "
            "generic panel — treat harshness and the scale as rough guesses"
        )
    cal = json.loads(json.dumps(cal))  # deep copy
    cal["family_key"] = family or None

    track_name = str((track or {}).get("name") or "")
    cal["track_note"] = None
    cal["extra_questions"] = []
    if track_name:
        low = track_name.lower()
        for keys, mod in TRACK_MODIFIERS:
            if any(k in low for k in keys):
                cal["harshness"] = max(1, min(5, cal["harshness"] + mod["harshness_delta"]))
                cal["track_note"] = mod["note"]
                cal["extra_questions"] = mod.get("extra_questions", [])
                if "max_reviewers" in mod:
                    cal["personas"] = cal["personas"][: mod["max_reviewers"]]
                notes.append(f"track '{track_name}' matched modifier {keys[0]!r}")
                break
    return cal, notes


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def build_packet(profile: dict, track, cal: dict, notes: list[str]) -> dict:
    review = profile.get("review") or {}
    return {
        "venue": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "family": profile.get("family"),
            "cfp_url": profile.get("cfp_url"),
            "blind": review.get("blind"),
            "submission_system": review.get("submission_system"),
            "rebuttal_format": review.get("rebuttal_format"),
            "rebuttal_limit": review.get("rebuttal_limit"),
        },
        "track": track,
        "calibration": {
            "family_key": cal.get("family_key"),
            "label": cal["label"],
            "harshness": cal["harshness"],
            "harshness_scale": "1 (lenient demo-track) .. 5 (NeurIPS main-track)",
            "reviewer_count": len(cal["personas"]),
            "meta_role": cal["meta_role"],
            "track_note": cal.get("track_note"),
        },
        "scale": cal["scale"],
        "rubric_scale": RUBRIC_SCALE,
        "dimensions": CORE_DIMENSIONS,
        "extra_questions": cal.get("extra_questions", []),
        "personas": cal["personas"],
        "form_fields": cal["form_fields"],
        "verify": {
            "cfp_url": profile.get("cfp_url"),
            "instruction": (
                "Profiles and scale anchors are a starting point, never ground "
                "truth. Re-verify the review process (scale, blind level, "
                "rebuttal format, reviewer guidelines) against the live CFP "
                "before relying on this simulation."
            ),
        },
        "disclaimer": (
            "This is a pre-submission simulation, not a prediction of the real "
            "review outcome."
        ),
        "notes": notes,
    }


def render_markdown(p: dict) -> str:
    v, c, s = p["venue"], p["calibration"], p["scale"]
    track = p.get("track") or {}
    out = []
    out.append(f"# Simulated review packet — {v.get('name') or v.get('id')}")
    out.append("")
    out.append(f"> {p['disclaimer']}")
    out.append(f"> Re-verify against the live CFP first: {p['verify']['cfp_url']}")
    out.append("")
    out.append("## Venue facts (from the merged profile)")
    out.append("")
    out.append(f"- Family: `{v.get('family')}` — {c['label']}")
    if track:
        out.append(f"- Track: {track.get('name')} (page limit: {track.get('page_limit')})")
    out.append(f"- Blind level: {v.get('blind')}  |  System: {v.get('submission_system')}")
    out.append(f"- Rebuttal: {v.get('rebuttal_format')} ({v.get('rebuttal_limit')})")
    out.append(f"- Panel harshness: {c['harshness']}/5 ({c['harshness_scale']})")
    if c.get("track_note"):
        out.append(f"- Track calibration: {c['track_note']}")
    out.append("")
    out.append(f"## Score scale — `{s['id']}` (re-verify; {s.get('note', '')})")
    out.append("")
    for k in sorted(s["labels"], key=lambda x: float(x), reverse=True):
        out.append(f"- **{k}** — {s['labels'][k]}")
    out.append(f"- Borderline threshold: **{s['borderline_threshold']}**  |  Confidence: {s.get('confidence')}")
    out.append("")
    out.append("## Reviewer panel")
    out.append("")
    out.append("| ID | Archetype | Harshness | Emphasis | Hunts for |")
    out.append("|---|---|---|---|---|")
    for r in p["personas"]:
        out.append(
            f"| {r['id']} | {r['archetype']} | {r['harshness']}/5 "
            f"| {', '.join(r['emphasis'])} | {'; '.join(r['hunts'])} |"
        )
    out.append(f"| meta | {c['meta_role']} | — | synthesis | reviewer disagreement, missing champion |")
    out.append("")
    out.append("## Review form (fill one per reviewer, independently)")
    out.append("")
    for r in p["personas"]:
        out.append(f"### {r['id']} — {r['archetype']}")
        out.append("")
        out.append(f"*Stance:* {r['stance']}")
        out.append("")
        for field in p["form_fields"]:
            out.append(f"- **{field}**: _todo_")
        for q in p.get("extra_questions", []):
            out.append(f"- **track question** — {q}: _todo_")
        out.append("")
    out.append(f"### Meta-review — {c['meta_role']}")
    out.append("")
    out.append("- **synthesis of the reviews**: _todo_")
    out.append("- **biggest shared concern**: _todo_")
    out.append("- **is there a champion?**: _todo_")
    out.append("- **decision lean**: _todo_")
    out.append("")
    out.append("## Scores file for `aggregate_scores.py`")
    out.append("")
    out.append("Fill and save as `scores.json`, then run "
               "`python3 scripts/aggregate_scores.py scores.json`:")
    out.append("")
    template = {
        "scale": {
            "min": s["min"],
            "max": s["max"],
            "borderline_threshold": s["borderline_threshold"],
        },
        "rubric_scale": {"min": RUBRIC_SCALE["min"], "max": RUBRIC_SCALE["max"]},
        "reviews": [
            {
                "id": r["id"],
                "persona": r["archetype"],
                "overall": None,
                "confidence": None,
                "scores": {d["id"]: None for d in CORE_DIMENSIONS},
            }
            for r in p["personas"]
        ],
    }
    out.append("```json")
    out.append(json.dumps(template, indent=2))
    out.append("```")
    if p["notes"]:
        out.append("")
        out.append("## Loader notes")
        out.append("")
        for n in p["notes"]:
            out.append(f"- {n}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Emit a venue-calibrated simulated-review form skeleton (personas, "
            "score scale, rubric) from a venues/conferences/<venue>.yml "
            "profile. Markdown by default; --json for machine-readable output. "
            "Deterministic, offline; scale anchors are historical norms that "
            "must be re-verified against the live CFP."
        )
    )
    ap.add_argument("venue", help="path to venues/conferences/<venue>.yml")
    ap.add_argument("--track", help="track name substring (e.g. Demo, Research)")
    ap.add_argument("--venues-dir", help="venues/ root (auto-discovered by default)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = ap.parse_args()
    try:
        profile, notes = load_profile(args.venue, args.venues_dir)
        track, tnote = pick_track(profile, args.track)
        notes.append(tnote)
        cal, cnotes = calibrate(profile, track)
        notes.extend(cnotes)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    packet = build_packet(profile, track, cal, notes)
    if args.json:
        json.dump(packet, sys.stdout, indent=2, default=str)
        print()
    else:
        print(render_markdown(packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
