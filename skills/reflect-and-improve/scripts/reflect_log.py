#!/usr/bin/env python3
"""reflect_log.py — durable lessons + before/after scoring for reflect-and-improve.

Manages a per-paper `.paper-memory/` directory so the toolkit's self-critique
loop is backed by data, not vibes:

  append    add a deduplicated, dated lesson to lessons.md
            (dedupe key = skill + normalized issue)
  recurring read lessons.md and print recurring (cross-paper) patterns,
            most-frequent first — call this at the start of a reflection
  score     record a before/after score for one (skill, metric); prints the
            delta and a KEEP / REVERT / TIE verdict so "did it get better"
            is a number. Lower-is-better metrics are auto-detected (count,
            error, errors, hedge, words-over, failures) or set with
            --lower-is-better / --higher-is-better
  prune     drop stale `this-paper` lessons (older than --stale-days) and
            enforce a cap of --keep most-recent this-paper entries;
            `recurring`-scope lessons are NEVER pruned
  show      print all lessons (optionally --skill / --scope filtered)

Stdlib only. No network. Files are plain Markdown / NDJSON so a human can read
and hand-edit them. Reflection is only worth its cost when there is a
measurable target — `score` is what makes the target measurable.

Examples:
  python3 reflect_log.py append  --memory .paper-memory --skill polish-prose \\
      --scope recurring --issue "abstract over-hedges the contribution" \\
      --rec "state the result as a claim once, then qualify in the body"
  python3 reflect_log.py recurring --memory .paper-memory
  python3 reflect_log.py score   --memory .paper-memory --skill polish-prose \\
      --metric hedge-count --before 11 --after 6
  python3 reflect_log.py prune   --memory .paper-memory --keep 50 --stale-days 365

Exit codes:
  0  success (for `score`: also 0 on KEEP or TIE)
  1  a measurable REGRESSION was recorded (score got worse) — the regression
     guard; a nonzero exit lets a wrapper refuse to keep the change
  2  bad arguments / unusable memory directory
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys

LESSONS = "lessons.md"
SCORES = "scores.ndjson"

# Substrings that mark a metric as lower-is-better (fewer = better).
_LOWER_HINTS = (
    "count", "error", "errors", "hedge", "fail", "failure", "failures",
    "violation", "violations", "over", "warnings", "warn", "todo", "passive",
)

LESSONS_HEADER = (
    "# Paper memory — lessons\n\n"
    "Accumulated, deduplicated lessons from the research-paper toolkit.\n"
    "Skills APPEND here when they catch something and READ here at start to\n"
    "personalize advice and avoid repeating it. Managed by reflect_log.py;\n"
    "safe to hand-edit. Local only — add `.paper-memory/` to .gitignore\n"
    "unless you want it versioned.\n\n"
    "Format per line:\n"
    "`- [YYYY-MM-DD] (skill | scope) issue -> recommendation`\n\n"
)

# Matches a lesson line written by `_fmt_lesson`. Tolerant of hand-edits.
# `issue` is greedy and `rec` forbids an internal "->" so the split lands on
# the LAST "->": issues may themselves contain "->" (e.g. "A -> B mapping is
# unclear") without corrupting the parse or the dedupe key.
_LESSON_RE = re.compile(
    r"^- \[(?P<date>\d{4}-\d{2}-\d{2})\] \((?P<skill>[^|]+?)\s*\|\s*"
    r"(?P<scope>this-paper|recurring)\)\s*(?P<issue>.+)\s*->\s*"
    r"(?P<rec>(?:(?!\s*->\s*).)+?)\s*$"
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _die(msg: str, code: int = 2) -> "NoReturn":  # type: ignore[name-defined]
    print(f"reflect_log: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _today() -> str:
    return _dt.date.today().isoformat()


def _norm(s: str) -> str:
    """Normalize free text for dedupe: lowercase, collapse whitespace/punct."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _ensure_memory(path: str, create: bool) -> str:
    if os.path.isdir(path):
        return path
    if create:
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:  # pragma: no cover - filesystem dependent
            _die(f"cannot create memory dir {path!r}: {e}")
        return path
    _die(
        f"memory directory not found: {path!r}\n"
        "  create it (the skill makes one per paper) or pass --memory <dir>"
    )


def _lessons_path(mem: str) -> str:
    return os.path.join(mem, LESSONS)


def _scores_path(mem: str) -> str:
    return os.path.join(mem, SCORES)


def _fmt_lesson(rec: dict) -> str:
    return (
        f"- [{rec['date']}] ({rec['skill']} | {rec['scope']}) "
        f"{rec['issue']} -> {rec['rec']}"
    )


def _read_lessons(mem: str) -> list[dict]:
    p = _lessons_path(mem)
    out: list[dict] = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            m = _LESSON_RE.match(line.rstrip("\n"))
            if not m:
                continue
            d = m.groupdict()
            # The greedy `issue` group can keep trailing space before "->";
            # strip every field so display, storage, and dedupe stay clean.
            for k in ("skill", "issue", "rec"):
                d[k] = d[k].strip()
            out.append(d)
    return out


def _write_lessons(mem: str, lessons: list[dict]) -> None:
    p = _lessons_path(mem)
    body = LESSONS_HEADER + "\n".join(_fmt_lesson(x) for x in lessons) + "\n"
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(body)


def _fmt_num(x: float) -> str:
    """Print integer-valued floats without a trailing .0; keep real decimals."""
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _lower_is_better(metric: str, flag: str | None) -> bool:
    if flag == "lower":
        return True
    if flag == "higher":
        return False
    m = metric.lower()
    return any(h in m for h in _LOWER_HINTS)


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_append(args) -> int:
    mem = _ensure_memory(args.memory, create=True)
    issue = args.issue.strip()
    rec = args.rec.strip()
    if not issue or not rec:
        _die("--issue and --rec must both be non-empty")

    lessons = _read_lessons(mem)
    key = (args.skill.strip().lower(), _norm(issue))
    for ex in lessons:
        if (ex["skill"].lower(), _norm(ex["issue"])) == key:
            # Duplicate. Refresh date + recommendation; upgrade scope if asked.
            ex["date"] = _today()
            ex["rec"] = rec
            if args.scope == "recurring":
                ex["scope"] = "recurring"
            _write_lessons(mem, lessons)
            print(f"deduped: refreshed existing lesson for "
                  f"({args.skill} | {ex['scope']}) {issue!r}")
            return 0

    new = {
        "date": _today(),
        "skill": args.skill.strip(),
        "scope": args.scope,
        "issue": issue,
        "rec": rec,
    }
    lessons.append(new)
    _write_lessons(mem, lessons)
    print("appended: " + _fmt_lesson(new))
    return 0


def cmd_recurring(args) -> int:
    mem = _ensure_memory(args.memory, create=False)
    lessons = [x for x in _read_lessons(mem) if x["scope"] == "recurring"]
    if args.skill:
        lessons = [x for x in lessons if x["skill"].lower() == args.skill.lower()]
    if not lessons:
        print("no recurring lessons logged yet")
        return 0

    # Surface the most-repeated patterns first (by normalized issue).
    freq: dict[str, int] = {}
    for x in lessons:
        freq[_norm(x["issue"])] = freq.get(_norm(x["issue"]), 0) + 1
    lessons.sort(key=lambda x: (-freq[_norm(x["issue"])], x["date"]))

    print(f"recurring lessons ({len(lessons)}):")
    for x in lessons:
        n = freq[_norm(x["issue"])]
        tag = f" (x{n})" if n > 1 else ""
        print(f"  {_fmt_lesson(x)}{tag}")
    return 0


def cmd_show(args) -> int:
    mem = _ensure_memory(args.memory, create=False)
    lessons = _read_lessons(mem)
    if args.skill:
        lessons = [x for x in lessons if x["skill"].lower() == args.skill.lower()]
    if args.scope:
        lessons = [x for x in lessons if x["scope"] == args.scope]
    if not lessons:
        print("no matching lessons")
        return 0
    for x in sorted(lessons, key=lambda x: x["date"]):
        print(_fmt_lesson(x))
    return 0


def cmd_score(args) -> int:
    mem = _ensure_memory(args.memory, create=True)
    lower = _lower_is_better(args.metric, args.direction)
    direction = "lower-is-better" if lower else "higher-is-better"

    rec = {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "skill": args.skill,
        "metric": args.metric,
        "before": args.before,
        "after": args.after,
        "direction": direction,
        "note": args.note or "",
    }

    if args.after is None:
        # Baseline only.
        with open(_scores_path(mem), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"baseline recorded: {args.skill}/{args.metric} = "
              f"{_fmt_num(args.before)} ({direction})")
        return 0

    delta = args.after - args.before
    if delta == 0:
        verdict, code = "TIE", 0
    else:
        improved = (delta < 0) if lower else (delta > 0)
        verdict, code = ("KEEP", 0) if improved else ("REVERT", 1)
    rec["delta"] = delta
    rec["verdict"] = verdict

    with open(_scores_path(mem), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")

    sign = f"+{_fmt_num(delta)}" if delta > 0 else _fmt_num(delta)
    print(f"{args.skill}/{args.metric}: {_fmt_num(args.before)} -> "
          f"{_fmt_num(args.after)} (delta {sign}, {direction})")
    print(f"VERDICT: {verdict}")
    if verdict == "REVERT":
        print("  measurable REGRESSION — do NOT keep this change; recommend the "
              "prior version (regression guard).", file=sys.stderr)
    elif verdict == "TIE":
        print("  no measurable change — defer to author taste; do not iterate "
              "again just to move this number.")
    return code


def cmd_prune(args) -> int:
    mem = _ensure_memory(args.memory, create=False)
    lessons = _read_lessons(mem)
    if not lessons:
        print("nothing to prune")
        return 0

    recurring = [x for x in lessons if x["scope"] == "recurring"]
    this_paper = [x for x in lessons if x["scope"] != "recurring"]
    before_n = len(this_paper)

    # 1) drop stale this-paper lessons
    if args.stale_days is not None and args.stale_days >= 0:
        cutoff = _dt.date.today() - _dt.timedelta(days=args.stale_days)
        kept = []
        for x in this_paper:
            try:
                d = _dt.date.fromisoformat(x["date"])
            except ValueError:
                d = _dt.date.today()  # un-parseable date: keep, treat as fresh
            if d >= cutoff:
                kept.append(x)
        this_paper = kept

    # 2) cap most-recent this-paper lessons
    if args.keep is not None and args.keep >= 0:
        this_paper.sort(key=lambda x: x["date"])
        if len(this_paper) > args.keep:
            this_paper = this_paper[len(this_paper) - args.keep:]

    dropped = before_n - len(this_paper)
    # Preserve a stable, human-friendly order: recurring first, then by date.
    merged = sorted(recurring, key=lambda x: x["date"]) + sorted(
        this_paper, key=lambda x: x["date"]
    )
    _write_lessons(mem, merged)
    print(f"pruned {dropped} stale/over-cap this-paper lesson(s); "
          f"kept {len(this_paper)} this-paper + {len(recurring)} recurring "
          "(recurring are never pruned)")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reflect_log.py",
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Lower-is-better metrics (counts/errors/hedges) are auto-detected; "
        "override with --lower-is-better / --higher-is-better on `score`.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_mem(sp):
        sp.add_argument(
            "--memory", default=".paper-memory",
            help="path to the per-paper .paper-memory directory "
            "(default: .paper-memory)",
        )

    a = sub.add_parser("append", help="add a deduplicated, dated lesson")
    add_mem(a)
    a.add_argument("--skill", required=True,
                   help="the skill that surfaced the lesson, e.g. polish-prose")
    a.add_argument("--issue", required=True, help="the pattern/problem observed")
    a.add_argument("--rec", required=True, help="the recommendation/fix")
    a.add_argument("--scope", choices=["this-paper", "recurring"],
                   default="this-paper",
                   help="recurring lessons are surfaced proactively and never "
                   "pruned (default: this-paper)")
    a.set_defaults(func=cmd_append)

    r = sub.add_parser("recurring", help="print recurring patterns, frequent first")
    add_mem(r)
    r.add_argument("--skill", help="filter to one skill")
    r.set_defaults(func=cmd_recurring)

    s = sub.add_parser("show", help="print lessons (optionally filtered)")
    add_mem(s)
    s.add_argument("--skill", help="filter to one skill")
    s.add_argument("--scope", choices=["this-paper", "recurring"],
                   help="filter to one scope")
    s.set_defaults(func=cmd_show)

    c = sub.add_parser(
        "score", help="record before/after; print delta + KEEP/REVERT/TIE")
    add_mem(c)
    c.add_argument("--skill", required=True, help="skill that produced the change")
    c.add_argument("--metric", required=True,
                   help="what is measured, e.g. preflight-errors, hedge-count, "
                   "abstract-words, rubric-mean")
    c.add_argument("--before", required=True, type=float,
                   help="score before the change")
    c.add_argument("--after", type=float, default=None,
                   help="score after the change; omit to record a baseline only")
    c.add_argument("--note", help="optional free-text note")
    dirg = c.add_mutually_exclusive_group()
    dirg.add_argument("--lower-is-better", dest="direction",
                      action="store_const", const="lower",
                      help="fewer is better (override auto-detection)")
    dirg.add_argument("--higher-is-better", dest="direction",
                      action="store_const", const="higher",
                      help="more is better (override auto-detection)")
    c.set_defaults(func=cmd_score, direction=None)

    pr = sub.add_parser(
        "prune", help="drop stale/over-cap this-paper lessons (keeps recurring)")
    add_mem(pr)
    pr.add_argument("--keep", type=int, default=50,
                    help="max this-paper lessons to keep (most recent); "
                    "default 50")
    pr.add_argument("--stale-days", type=int, default=365,
                    help="drop this-paper lessons older than N days; default 365")
    pr.set_defaults(func=cmd_prune)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
