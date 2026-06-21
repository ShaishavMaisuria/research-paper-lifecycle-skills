#!/usr/bin/env python3
"""Build a deterministic Q&A drill plan for a talk, defense, or poster.

Sizes the drill to the real Q&A slot (how many live exchanges fit, how many
questions to prep), picks an audience-persona lineup — calibrated to the
venue family when a venues/conferences/<venue>.yml profile is given — and
emits the round-by-round drill plan plus a transcript skeleton that
grade_answers.py can score. Markdown by default; --json for machines.

This script is deterministic and makes NO network calls. Slot lengths are
historical norms and are NOT stored in venue profiles: the agent MUST
re-verify the actual talk slot and Q&A length against the venue's live
presenter instructions (start from the profile's cfp_url / website) before
the user rehearses to the wrong clock.

Usage:
    python3 qa_drill.py --minutes 3
    python3 qa_drill.py --venue venues/conferences/sigspatial-2026.yml \
        --setting conference-talk --minutes 4
    python3 qa_drill.py --setting defense --json

Exit codes: 0 ok, 2 bad arguments / missing or unparsable profile.
"""
from __future__ import annotations

import argparse
import json
import math
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


def find_venues_dir(venue_path: pathlib.Path):
    for parent in venue_path.resolve().parents:
        if (parent / "families").is_dir() or (parent / "schema.yml").is_file():
            return parent
        if (parent / "venues" / "families").is_dir():
            return parent / "venues"
    return None


def load_profile(venue_path):
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
    return prof


# ---------------------------------------------------------------------------
# Personas. Question stems are deliberately NAMELESS about prior work:
# the agent fills in real, verified papers (find-papers + verify-citations)
# or keeps the attack generic. Never invent a citation for a drill question.
# ---------------------------------------------------------------------------

PERSONAS = {
    "hostile-skeptic": {
        "name": "The Hostile Skeptic",
        "tone": "hostile",
        "probes": "the central claim's validity; assumes the result is oversold",
        "stems": [
            "Your headline claim only holds under <condition the paper glosses over> — isn't the honest claim much weaker?",
            "If I remove <component>, how much of the gain survives — and did you actually run that?",
            "Why should I believe this isn't just <simpler explanation> in disguise?",
        ],
        "good_answer": "concedes the true scope without surrendering the contribution; cites the paper's own evidence",
    },
    "methods-stickler": {
        "name": "The Methods Stickler",
        "tone": "hostile",
        "probes": "experimental hygiene: baselines, tuning budgets, seeds, splits",
        "stems": [
            "How did you tune the baselines — same budget as your method, or out of the box?",
            "How many runs is each number, and what's the variance?",
            "Why this dataset/split and not the standard one?",
        ],
        "good_answer": "exact numbers from memory (runs, seeds, budgets); no hand-waving",
    },
    "statistician": {
        "name": "The Statistician",
        "tone": "hostile",
        "probes": "significance, error bars, multiple comparisons, power",
        "stems": [
            "Is that improvement statistically significant, and under what test?",
            "You compare against many baselines on many datasets — did you correct for multiple comparisons?",
        ],
        "good_answer": "names the test and effect size, or honestly says single-run and what that limits",
    },
    "theorist": {
        "name": "The Theory Prober",
        "tone": "hostile",
        "probes": "assumptions, proof sketches, failure modes outside the assumptions",
        "stems": [
            "What exactly breaks when assumption <X> fails?",
            "Is the bound tight, and does the empirical behavior match it?",
        ],
        "good_answer": "states assumptions crisply, knows the failure boundary, separates proved from observed",
    },
    "adjacent-expert": {
        "name": "The Adjacent-Field Expert",
        "tone": "hostile",
        "probes": "novelty against neighboring literatures the authors may not read",
        "stems": [
            "This looks equivalent to <verified prior work or 'a classic technique in field Y'> — what's genuinely new?",
            "The <other community> solved a very similar problem — did you compare?",
        ],
        "good_answer": "a rehearsed one-sentence delta versus the closest prior work; never bluffs familiarity",
    },
    "big-picture": {
        "name": "The Big-Picture Senior",
        "tone": "curious",
        "probes": "why it matters, where it goes, what generalizes",
        "stems": [
            "Stepping back — what does this change about how we should think about <problem>?",
            "Where does this line of work go in five years?",
            "What's the one thing you'd want the community to take away?",
        ],
        "good_answer": "a 30-second answer-first vision statement, not a re-summary of the talk",
    },
    "newcomer": {
        "name": "The Confused Newcomer",
        "tone": "curious",
        "probes": "whether the speaker can explain the core idea in plain language",
        "stems": [
            "I'm not from this area — can you explain in one minute what problem you're solving and why it's hard?",
            "What does <jargon term from the talk> actually mean here?",
        ],
        "good_answer": "zero jargon, one concrete example, no condescension",
    },
    "practitioner": {
        "name": "The Industry Practitioner",
        "tone": "curious",
        "probes": "deployment reality: cost, latency, scale, integration, licensing",
        "stems": [
            "What would it cost me to run this in production, and at what scale does it break?",
            "What's the engineering effort to integrate this with an existing system?",
        ],
        "good_answer": "honest numbers or honest 'untested beyond N'; separates research prototype from product",
    },
    "reproducibility-auditor": {
        "name": "The Reproducibility Auditor",
        "tone": "curious",
        "probes": "code, data, artifacts, exact settings",
        "stems": [
            "Is the code and data available, and can I reproduce Table <N> from it tonight?",
            "Which parts of the pipeline are NOT in the release?",
        ],
        "good_answer": "exact artifact status (what is and is not released, and why), no over-promising",
    },
    "ethicist": {
        "name": "The Ethics Prober",
        "tone": "hostile",
        "probes": "harms, consent, dual use, affected populations",
        "stems": [
            "Who could be harmed if this works exactly as described?",
            "How did you handle consent / IRB for the data you collected?",
        ],
        "good_answer": "engages seriously, names the mitigation, never jokes it away",
    },
    "self-promoter": {
        "name": "The Self-Promoter",
        "tone": "curveball",
        "probes": "nothing — a comment about their own work disguised as a question",
        "stems": [
            "This is really more of a comment — in my own work on <their topic> we found <claim>... so, thoughts?",
        ],
        "good_answer": "30-second redirect: find the one answerable kernel, answer it, offer to talk after",
    },
    "rambler": {
        "name": "The Rambler",
        "tone": "curveball",
        "probes": "composure — a three-part question with a buried premise",
        "stems": [
            "Three things: first <minor detail>, second <flawed premise>, and third <real question> — also, could this work for <unrelated domain>?",
        ],
        "good_answer": "decomposes out loud ('there are three questions there'), answers the real one first, corrects the premise politely",
    },
}

# Persona lineups keyed by venue family (first entries get more questions).
FAMILY_LINEUPS = {
    "neurips-style": {
        "label": "NeurIPS-style ML audience: theory + stats heavy, novelty-allergic",
        "lineup": [
            "hostile-skeptic", "theorist", "statistician", "adjacent-expert",
            "newcomer", "big-picture", "self-promoter",
        ],
    },
    "acm-sigconf": {
        "label": "ACM SIG conference audience: systems/scalability culture, baseline hawks",
        "lineup": [
            "hostile-skeptic", "methods-stickler", "newcomer", "big-picture",
            "practitioner", "reproducibility-auditor", "rambler",
        ],
    },
    "ieee-conf": {
        "label": "IEEE conference audience: systems/scalability culture, baseline hawks",
        "lineup": [
            "hostile-skeptic", "methods-stickler", "newcomer", "big-picture",
            "practitioner", "reproducibility-auditor", "rambler",
        ],
    },
    "acm-manuscript-chi": {
        "label": "CHI-style HCI audience: methods + ethics + generalizability",
        "lineup": [
            "ethicist", "methods-stickler", "newcomer", "big-picture",
            "adjacent-expert", "self-promoter",
        ],
    },
    "lncs": {
        "label": "LNCS-style audience: correctness and placement against the venue's own proceedings",
        "lineup": [
            "methods-stickler", "adjacent-expert", "theorist", "newcomer", "big-picture",
        ],
    },
}

DEFAULT_LINEUP = {
    "label": "Generic CS-conference audience (no family calibration matched)",
    "lineup": [
        "hostile-skeptic", "methods-stickler", "adjacent-expert",
        "newcomer", "big-picture", "practitioner",
    ],
}

SETTINGS = {
    "conference-talk": {
        "label": "Conference talk Q&A (session chair fields 2-4 questions)",
        "default_minutes": 3.0,
        "target_seconds": 45,
        "max_seconds": 75,
        "note": "Chairs cut you off, not the questioner. Long answers steal your own question slots.",
    },
    "lightning": {
        "label": "Lightning / spotlight talk",
        "default_minutes": 1.0,
        "target_seconds": 30,
        "max_seconds": 45,
        "note": "Many lightning formats have NO live Q&A — verify; questions then move to the poster/hallway.",
    },
    "keynote": {
        "label": "Keynote / invited talk",
        "default_minutes": 10.0,
        "target_seconds": 60,
        "max_seconds": 120,
        "note": "Audience expects opinions and vision, not just results; big-picture questions dominate.",
    },
    "poster": {
        "label": "Poster session (continuous 1-2h conversation)",
        "default_minutes": 90.0,
        "target_seconds": 60,
        "max_seconds": 120,
        "note": "Not slot-bound: also rehearse the 2-minute and 5-minute pitch; expect the same question dozens of times.",
    },
    "defense": {
        "label": "Thesis defense / viva",
        "default_minutes": 60.0,
        "target_seconds": 90,
        "max_seconds": 180,
        "note": "Committee follows up on your answers; depth beats speed. Expect chains of 2-3 follow-ups per topic.",
    },
    "job-talk": {
        "label": "Faculty / industry job talk",
        "default_minutes": 15.0,
        "target_seconds": 60,
        "max_seconds": 120,
        "note": "Interruptions DURING the talk are normal; rehearse resuming the thread after each answer.",
    },
}

ROUNDS = [
    {
        "id": "warm-up",
        "name": "Warm-up: curious clarifications",
        "share": 0.20,
        "tones": ["curious"],
        "rule": "Friendly questions first; goal is answer-first structure and a clean plain-language pitch.",
    },
    {
        "id": "hostile-gauntlet",
        "name": "Hostile gauntlet",
        "share": 0.35,
        "tones": ["hostile"],
        "rule": "Hardest personas back-to-back; goal is composure and conceding-without-collapsing.",
    },
    {
        "id": "dreaded",
        "name": "Dreaded-question finale",
        "share": 0.25,
        "tones": ["hostile", "curious"],
        "rule": "The 'questions you hope nobody asks' from the weakness inventory (references/dreaded-questions.md); honest pre-built answers only.",
    },
    {
        "id": "rapid-fire",
        "name": "Rapid-fire",
        "share": 0.20,
        "tones": ["hostile", "curious"],
        "rule": "Any persona, 30-second answer cap regardless of setting; train the stop.",
    },
    {
        "id": "curveballs",
        "name": "Curveballs",
        "fixed": 2,
        "tones": ["curveball"],
        "rule": "The self-promoter and the rambler; train the redirect and the decomposition, not the content.",
    },
]


def build_plan(args):
    notes: list[str] = []
    venue_block = None
    family = None

    if args.venue:
        prof = load_profile(args.venue)
        family = str(prof.get("family") or "") or None
        venue_block = {
            "id": prof.get("id"),
            "name": prof.get("name"),
            "family": family,
            "cfp_url": prof.get("cfp_url"),
            "website": prof.get("website"),
        }

    setting = SETTINGS[args.setting]
    minutes = args.minutes if args.minutes is not None else setting["default_minutes"]
    if minutes <= 0:
        raise ProfileError("--minutes must be > 0")
    spe = args.seconds_per_exchange
    if spe <= 0:
        raise ProfileError("--seconds-per-exchange must be > 0")

    if args.setting == "poster":
        capacity = None
        notes.append("poster sessions are continuous; capacity math skipped")
    else:
        capacity = max(1, math.floor(minutes * 60 / spe))

    # Prep roughly 3x what the live slot fits, clamped to a drillable session.
    base = capacity if capacity is not None else 8
    total = max(12, min(36, 3 * base))

    fam_cal = FAMILY_LINEUPS.get(family or "")
    if fam_cal is None:
        fam_cal = DEFAULT_LINEUP
        if family:
            notes.append(
                f"family '{family}' has no Q&A lineup; using the generic audience"
            )
        elif not args.venue:
            notes.append("no --venue given; using the generic audience lineup")
    lineup_ids = list(fam_cal["lineup"])
    # Settings with committees/interviews always include the heavyweights.
    if args.setting in ("defense", "job-talk"):
        for pid in ("hostile-skeptic", "big-picture", "adjacent-expert"):
            if pid not in lineup_ids:
                lineup_ids.insert(0, pid)
        notes.append(
            f"{args.setting}: lineup augmented with committee-style heavyweights"
        )
    # Curveball personas must exist for the curveball round.
    for pid in ("self-promoter", "rambler"):
        if pid not in lineup_ids:
            lineup_ids.append(pid)

    # Allocate questions to rounds (largest-remainder on shares; fixed rounds first).
    fixed_total = sum(r.get("fixed", 0) for r in ROUNDS)
    remaining = max(0, total - fixed_total)
    shares = [(r, r.get("share", 0.0)) for r in ROUNDS if "share" in r]
    raw = [(r, remaining * s) for r, s in shares]
    counts = {r["id"]: int(math.floor(x)) for r, x in raw}
    leftover = remaining - sum(counts.values())
    for r, x in sorted(raw, key=lambda t: t[1] - math.floor(t[1]), reverse=True):
        if leftover <= 0:
            break
        counts[r["id"]] += 1
        leftover -= 1
    for r in ROUNDS:
        if "fixed" in r:
            counts[r["id"]] = r["fixed"]

    # Assign persona quotas per round, cycling through tone-matching personas.
    rounds_out = []
    quotas: dict[str, int] = {pid: 0 for pid in lineup_ids}
    for r in ROUNDS:
        eligible = [
            pid for pid in lineup_ids if PERSONAS[pid]["tone"] in r["tones"]
        ] or lineup_ids
        assigned = [eligible[i % len(eligible)] for i in range(counts[r["id"]])]
        for pid in assigned:
            quotas[pid] += 1
        rounds_out.append(
            {
                "id": r["id"],
                "name": r["name"],
                "questions": counts[r["id"]],
                "rule": r["rule"],
                "answer_cap_seconds": 30
                if r["id"] == "rapid-fire"
                else setting["max_seconds"],
                "personas": assigned,
            }
        )

    personas_out = [
        dict(PERSONAS[pid], id=pid, questions=quotas[pid])
        for pid in lineup_ids
    ]

    return {
        "setting": {
            "id": args.setting,
            "label": setting["label"],
            "qa_minutes": minutes,
            "seconds_per_exchange": spe,
            "live_capacity": capacity,
            "target_seconds": setting["target_seconds"],
            "max_seconds": setting["max_seconds"],
            "note": setting["note"],
        },
        "venue": venue_block,
        "audience": {"label": fam_cal["label"], "family_key": family},
        "drill": {"total_questions": total, "rounds": rounds_out},
        "personas": personas_out,
        "verify": {
            "cfp_url": (venue_block or {}).get("cfp_url"),
            "instruction": (
                "Slot and Q&A lengths are NOT stored in venue profiles and "
                "change per year/track/session. Re-verify the talk slot, Q&A "
                "minutes, and session format against the venue's live "
                "presenter instructions (start from cfp_url/website) before "
                "rehearsing to this clock."
            ),
        },
        "citation_rule": (
            "Question stems that reference prior work must use REAL papers "
            "verified via find-papers + verify-citations, or stay nameless "
            "('a questioner claims prior work did X'). Never invent a citation."
        ),
        "grade_with": "python3 scripts/grade_answers.py transcript.md --target {t} --max {m}".format(
            t=setting["target_seconds"], m=setting["max_seconds"]
        ),
        "notes": notes,
    }


def render_markdown(p: dict) -> str:
    s = p["setting"]
    out = []
    title = (p["venue"] or {}).get("name") or s["label"]
    out.append(f"# Q&A drill plan — {title}")
    out.append("")
    out.append(f"> {p['verify']['instruction']}")
    if p["verify"]["cfp_url"]:
        out.append(f"> Start verification here: {p['verify']['cfp_url']}")
    out.append("")
    out.append("## Slot math")
    out.append("")
    out.append(f"- Setting: **{s['label']}** — {s['note']}")
    if s["live_capacity"] is not None:
        out.append(
            f"- A {s['qa_minutes']:g}-minute Q&A at ~{s['seconds_per_exchange']}s "
            f"per exchange fits **~{s['live_capacity']} live questions**."
        )
    out.append(
        f"- Answer targets: aim **{s['target_seconds']}s**, hard cap "
        f"**{s['max_seconds']}s** (rapid-fire round: 30s)."
    )
    out.append(
        f"- Drill size: **{p['drill']['total_questions']} questions** "
        "(~3x the live slot — most prepped questions are never asked, "
        "but the dreaded ones must be)."
    )
    out.append("")
    out.append(f"## Audience — {p['audience']['label']}")
    out.append("")
    out.append("| Persona | Tone | Probes | Qs |")
    out.append("|---|---|---|---|")
    for per in p["personas"]:
        out.append(
            f"| {per['name']} (`{per['id']}`) | {per['tone']} "
            f"| {per['probes']} | {per['questions']} |"
        )
    out.append("")
    out.append("Question stems (fill <placeholders> from the actual paper; "
               "prior-work references must be verified or stay nameless):")
    out.append("")
    for per in p["personas"]:
        out.append(f"- **{per['name']}** — good answer: {per['good_answer']}")
        for stem in per["stems"]:
            out.append(f"  - {stem}")
    out.append("")
    out.append("## Rounds")
    out.append("")
    for r in p["drill"]["rounds"]:
        out.append(
            f"### {r['name']} — {r['questions']} questions, "
            f"cap {r['answer_cap_seconds']}s"
        )
        out.append("")
        out.append(f"{r['rule']}")
        out.append("")
        out.append(f"Personas in order: {', '.join(r['personas']) or '—'}")
        out.append("")
    out.append("## Transcript skeleton (grade with grade_answers.py)")
    out.append("")
    out.append("Record each exchange below; the answer is what the speaker "
               "actually said (typed or transcribed). Then run:")
    out.append("")
    out.append(f"    {p['grade_with']}")
    out.append("")
    out.append("```markdown")
    n = 1
    for r in p["drill"]["rounds"]:
        out.append(f"<!-- round: {r['id']} -->")
        for pid in r["personas"]:
            out.append(f"## Q{n}: _question here_")
            out.append(f"[persona: {pid}]")
            out.append("_answer as spoken_")
            out.append("")
            n += 1
    out.append("```")
    if p["notes"]:
        out.append("")
        out.append("## Notes")
        out.append("")
        for note in p["notes"]:
            out.append(f"- {note}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build a deterministic Q&A drill plan: slot math, venue-calibrated "
            "audience personas, hostile/curious/dreaded/rapid-fire rounds, and "
            "a transcript skeleton for grade_answers.py. Offline; venue "
            "profile optional. Slot lengths must be re-verified against the "
            "venue's live presenter instructions."
        )
    )
    ap.add_argument(
        "--venue",
        help="optional path to venues/conferences/<venue>.yml for family calibration",
    )
    ap.add_argument(
        "--setting",
        default="conference-talk",
        choices=sorted(SETTINGS),
        help="presentation setting (default: conference-talk)",
    )
    ap.add_argument(
        "--minutes",
        type=float,
        help="Q&A length in minutes (default depends on --setting)",
    )
    ap.add_argument(
        "--seconds-per-exchange",
        type=int,
        default=90,
        help="seconds one question+answer exchange takes live (default 90)",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = ap.parse_args()
    try:
        plan = build_plan(args)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        json.dump(plan, sys.stdout, indent=2, default=str)
        print()
    else:
        print(render_markdown(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
