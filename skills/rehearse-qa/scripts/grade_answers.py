#!/usr/bin/env python3
"""Grade a Q&A drill transcript: timing, hedge openers, filler, buried answers.

Transcript format (qa_drill.py emits a matching skeleton):
  - each exchange starts with a "## Q" heading carrying the question text:
        ## Q1: How did you tune the baselines?
    ("## Q:", "## Q3:", "## Q3." all work; the question must be on the
    heading line)
  - everything until the next "## " heading is the spoken answer
  - [bracketed lines] like "[persona: hostile-skeptic]" are metadata and
    <!-- comments --> are notes; neither counts as spoken words
  - "## " headings that are not Q-headings end the previous exchange and
    are otherwise ignored

Checks per answer (all deterministic, stdlib only, no network):
  - estimated speaking time at --wpm (default 140, conversational pace)
    vs --target (aim) and --max (hard cap) seconds
  - unanswered questions (empty answer body)
  - hedge openers ("great question", "um", "I guess"...) in the first words
  - filler density ("um", "you know", "sort of"...; flagged at >= 3)
  - buried answers: a closed (yes/no) question whose first sentence never
    commits ("yes", "no", "not yet", "it depends"...)

Usage:
    python3 grade_answers.py transcript.md
    python3 grade_answers.py transcript.md --target 45 --max 75 --json

Exit codes: 0 all answers land (warnings allowed), 1 at least one answer is
unanswered or over the hard cap (run another round), 2 bad arguments,
unreadable file, or no Q-blocks found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

Q_RE = re.compile(r"^##\s*Q\d*\s*[:.]\s*(.+?)\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^##\s")
META_LINE_RE = re.compile(r"^\s*\[[^\]]*\]\s*$")
PERSONA_RE = re.compile(r"^\s*\[\s*persona\s*:\s*([^\]]+?)\s*\]\s*$", re.IGNORECASE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
BRACKET_RE = re.compile(r"\[[^\]]*\]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

HEDGE_OPENERS = [
    "great question",
    "good question",
    "that's a great",
    "that's a good",
    "thats a great",
    "thats a good",
    "interesting question",
    "um",
    "uh",
    "er",
    "hmm",
    "so basically",
    "i think maybe",
    "i guess",
    "i mean",
    "well, you know",
    "to be honest",
]

FILLERS = [
    "um",
    "uh",
    "er",
    "you know",
    "sort of",
    "kind of",
    "i mean",
    "i guess",
    "basically",
    "like i said",
]

CLOSED_STARTERS = {
    "is", "are", "was", "were", "am", "do", "does", "did", "have", "has",
    "had", "can", "could", "will", "would", "should", "shall", "may",
    "might", "must", "isn't", "aren't", "wasn't", "weren't", "don't",
    "doesn't", "didn't", "haven't", "hasn't", "can't", "couldn't",
    "won't", "wouldn't", "shouldn't",
}

COMMIT_RE = re.compile(
    r"\b(yes|no|nope|yeah|correct|right|exactly|absolutely|partly|"
    r"partially|mostly|largely|not yet|not really|it depends|"
    r"short answer|in short|we did|we do|we don't|we didn't|we have|"
    r"we haven't|we can|we cannot|we can't|it does|it doesn't|"
    r"it is|it isn't|that's right|that's not)\b",
    re.IGNORECASE,
)


def fail(msg: str) -> int:
    sys.stderr.write(f"error: {msg}\n")
    return 2


def spoken_text(lines: list[str]) -> str:
    body = "\n".join(
        ln for ln in lines if not META_LINE_RE.match(ln)
    )
    body = COMMENT_RE.sub(" ", body)
    body = BRACKET_RE.sub(" ", body)
    return body.strip()


def parse_transcript(text: str):
    """Return a list of {question, persona, answer_lines} blocks."""
    blocks = []
    current = None
    for raw in text.splitlines():
        m = Q_RE.match(raw)
        if m:
            current = {"question": m.group(1), "persona": None, "lines": []}
            blocks.append(current)
            continue
        if HEADING_RE.match(raw):
            current = None  # non-question section: stop collecting
            continue
        if current is not None:
            pm = PERSONA_RE.match(raw)
            if pm and current["persona"] is None:
                current["persona"] = pm.group(1)
            current["lines"].append(raw)
    return blocks


def first_sentence(text: str) -> str:
    parts = SENT_SPLIT_RE.split(text.strip(), maxsplit=1)
    return parts[0] if parts else ""


def count_fillers(text: str) -> int:
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    total = 0
    for f in FILLERS:
        total += len(re.findall(r"(?<![a-z'])" + re.escape(f) + r"(?![a-z'])", low))
    return total


def is_closed_question(q: str) -> bool:
    words = WORD_RE.findall(q.lower())
    return bool(words) and words[0] in CLOSED_STARTERS


def grade_block(block: dict, wpm: float, target: int, cap: int) -> dict:
    answer = spoken_text(block["lines"])
    words = len(WORD_RE.findall(answer))
    seconds = round(words / wpm * 60, 1) if words else 0.0
    flags: list[str] = []
    if words == 0:
        flags.append("unanswered")
    else:
        if seconds > cap:
            flags.append(f"over-cap ({seconds:.0f}s > {cap}s hard cap)")
        elif seconds > target:
            flags.append(f"over-target ({seconds:.0f}s > {target}s aim)")
        opener = " ".join(answer.lower().split()[:8])
        for h in HEDGE_OPENERS:
            if opener.startswith(h) or f" {h}" in f" {opener}"[: len(h) + 3]:
                flags.append(f"hedge-opener ({h!r})")
                break
        fillers = count_fillers(answer)
        if fillers >= 3:
            flags.append(f"filler-heavy ({fillers} filler phrases)")
        if is_closed_question(block["question"]) and not COMMIT_RE.search(
            first_sentence(answer)
        ):
            flags.append("buried-answer (closed question; first sentence never commits)")
    return {
        "question": block["question"],
        "persona": block["persona"],
        "words": words,
        "est_seconds": seconds,
        "flags": flags,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Grade a Q&A drill transcript ('## Q: ...' blocks): speaking time "
            "vs target/cap, unanswered questions, hedge openers, filler "
            "density, and buried answers to yes/no questions. Deterministic, "
            "offline. Exit 1 means run another drill round."
        )
    )
    ap.add_argument("transcript", help="markdown transcript (see --help header)")
    ap.add_argument("--wpm", type=float, default=140,
                    help="conversational speaking pace (default 140)")
    ap.add_argument("--target", type=int, default=60,
                    help="aim: seconds per answer (default 60)")
    ap.add_argument("--max", dest="cap", type=int, default=90,
                    help="hard cap: seconds per answer (default 90)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    if args.wpm <= 0:
        return fail("--wpm must be > 0")
    if args.target <= 0 or args.cap <= 0:
        return fail("--target and --max must be > 0")
    if args.cap < args.target:
        return fail(f"--max ({args.cap}) is below --target ({args.target})")
    try:
        text = open(args.transcript, encoding="utf-8").read()
    except OSError as exc:
        return fail(f"cannot read transcript: {exc}")

    blocks = parse_transcript(text)
    if not blocks:
        return fail(
            "no question blocks found — each exchange must start with a "
            "'## Q: <question>' heading (qa_drill.py emits a skeleton)"
        )

    results = [grade_block(b, args.wpm, args.target, args.cap) for b in blocks]
    answered = [r for r in results if r["words"] > 0]
    hard_fails = [
        r for r in results
        if any(f == "unanswered" or f.startswith("over-cap") for f in r["flags"])
    ]
    clean = [r for r in results if not r["flags"]]
    avg = round(sum(r["est_seconds"] for r in answered) / len(answered), 1) if answered else 0.0

    summary = {
        "questions": len(results),
        "answered": len(answered),
        "clean": len(clean),
        "flagged": len(results) - len(clean),
        "hard_fails": len(hard_fails),
        "avg_answer_seconds": avg,
        "settings": {"wpm": args.wpm, "target": args.target, "max": args.cap},
        "verdict": (
            "ready: every answer lands inside the hard cap"
            if not hard_fails
            else "not ready: re-drill the flagged answers"
        ),
    }
    report = {"summary": summary, "answers": results}

    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print(f"# Q&A drill grade — {args.transcript}")
        print()
        print(
            f"{summary['questions']} questions | {summary['answered']} answered | "
            f"{summary['clean']} clean | {summary['hard_fails']} hard fails | "
            f"avg {summary['avg_answer_seconds']}s "
            f"(target {args.target}s, cap {args.cap}s @ {args.wpm:g} wpm)"
        )
        print()
        for i, r in enumerate(results, 1):
            tag = "OK " if not r["flags"] else "FIX"
            persona = f" [{r['persona']}]" if r["persona"] else ""
            print(f"{tag} Q{i}{persona}: {r['question']}")
            print(f"     {r['words']} words ≈ {r['est_seconds']}s")
            for f in r["flags"]:
                print(f"     - {f}")
        print()
        print(f"Verdict: {summary['verdict']}")
    return 0 if not hard_fails else 1


if __name__ == "__main__":
    sys.exit(main())
