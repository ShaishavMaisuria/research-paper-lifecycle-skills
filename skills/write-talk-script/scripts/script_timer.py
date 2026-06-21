#!/usr/bin/env python3
"""Re-time a draft talk script: per-slide word counts, cumulative timing
marks, cut-list savings, and an over/under verdict.

Script file format (full conventions in references/script-craft.md):
  - one "## " heading per slide; text before the first "## " is ignored
    (front matter); other heading levels are treated as unspoken notes
  - [bracketed stage directions] and <!-- comments --> are not spoken
    and are excluded from word counts (so inline timing marks like
    [4:30] cost nothing)
  - a cut block is the lines between '<!-- CUT: label -->' and
    '<!-- END CUT -->' (each marker alone on its own line, no nesting,
    no crossing slide boundaries); its words are counted in the slide
    AND reported separately as time saved when dropped

Give the slot via --minutes/--qa, or via --budget budget.json (the
--json output of word_budget.py) to also compare slide-by-slide.

Stdlib only. No network.

Usage:
    python3 script_timer.py talk-script.md --minutes 15 --qa 3
    python3 script_timer.py talk-script.md --budget budget.json
    python3 script_timer.py talk-script.md --wpm 118 --json

Exit codes: 0 within budget (or no slot given); 1 scripted time exceeds
speaking time; 2 bad arguments, unreadable file, or malformed cut markers.
"""

import argparse
import json
import re
import sys

SLIDE_RE = re.compile(r"^##\s+(.+?)\s*$")
HEADING_RE = re.compile(r"^#{1,6}\s")
CUT_OPEN_RE = re.compile(r"^\s*<!--\s*CUT(?::\s*(.*?))?\s*-->\s*$", re.IGNORECASE)
CUT_CLOSE_RE = re.compile(r"^\s*<!--\s*END\s+CUT\s*-->\s*$", re.IGNORECASE)
COMMENT_RE = re.compile(r"<!--.*?-->")
BRACKET_RE = re.compile(r"\[[^\]]*\]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def mmss(seconds):
    seconds = int(round(seconds))
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return "%s%d:%02d" % (sign, seconds // 60, seconds % 60)


def count_words(text):
    text = COMMENT_RE.sub(" ", text)
    text = BRACKET_RE.sub(" ", text)
    return len(WORD_RE.findall(text))


def parse_script(path):
    """Return (slides, cuts). slides: [{n,title,line,words}]. cuts:
    [{label,slide_n,line,words}]. Raises ValueError on malformed cuts."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        raise IOError("cannot read script %s: %s" % (path, exc))

    slides, cuts = [], []
    current, open_cut, in_comment = None, None, False
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")

        m = CUT_OPEN_RE.match(line)
        if m:
            if open_cut is not None:
                raise ValueError("%s:%d: CUT opened inside another CUT (opened "
                                 "at line %d); cuts cannot nest"
                                 % (path, lineno, open_cut["line"]))
            if current is None:
                raise ValueError("%s:%d: CUT marker before the first '## ' slide "
                                 "heading" % (path, lineno))
            label = m.group(1) or "cut-%d" % (len(cuts) + 1)
            open_cut = {"label": label, "slide_n": current["n"],
                        "line": lineno, "words": 0}
            continue
        if CUT_CLOSE_RE.match(line):
            if open_cut is None:
                raise ValueError("%s:%d: END CUT without a matching CUT marker"
                                 % (path, lineno))
            cuts.append(open_cut)
            open_cut = None
            continue

        m = SLIDE_RE.match(line)
        if m and not in_comment:
            if open_cut is not None:
                raise ValueError("%s:%d: slide heading inside CUT opened at line "
                                 "%d; close the cut before the next slide"
                                 % (path, lineno, open_cut["line"]))
            current = {"n": len(slides) + 1, "title": m.group(1),
                       "line": lineno, "words": 0}
            slides.append(current)
            continue

        # multi-line HTML comments: drop wholly-commented spans
        if in_comment:
            if "-->" in line:
                line = line.split("-->", 1)[1]
                in_comment = False
            else:
                continue
        if "<!--" in line and "-->" not in line.split("<!--", 1)[1]:
            line = line.split("<!--", 1)[0]
            in_comment = True

        if current is None or HEADING_RE.match(line):
            continue  # front matter before first slide / unspoken note heading
        n = count_words(line)
        if n:
            current["words"] += n
            if open_cut is not None:
                open_cut["words"] += n

    if open_cut is not None:
        raise ValueError("%s: CUT opened at line %d is never closed (add "
                         "'<!-- END CUT -->')" % (path, open_cut["line"]))
    if not slides:
        raise ValueError("%s has no '## ' slide headings; format the script with "
                         "one '## ' heading per slide" % path)
    return slides, cuts


def load_budget(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            budget = json.load(fh)
    except OSError as exc:
        raise IOError("cannot read budget %s: %s" % (path, exc))
    except ValueError as exc:
        raise IOError("%s is not valid JSON (expected word_budget.py --json "
                      "output): %s" % (path, exc))
    for key in ("wpm", "speaking_minutes", "slides"):
        if key not in budget:
            raise IOError("%s is missing %r — expected word_budget.py --json "
                          "output" % (path, key))
    return budget


def analyze(slides, cuts, wpm, speaking_minutes, budget):
    clock = 0.0
    budget_slides = budget["slides"] if budget else None
    rows = []
    for i, s in enumerate(slides):
        secs = s["words"] / wpm * 60.0
        row = {"n": s["n"], "title": s["title"], "words": s["words"],
               "seconds": round(secs, 1), "time": mmss(secs),
               "starts_at": mmss(clock)}
        if budget_slides and i < len(budget_slides):
            target = budget_slides[i]["words"]
            row["budget_words"] = target
            if target and s["words"] > target * 1.10:
                row["status"] = "OVER"
            elif target and s["words"] < target * 0.90:
                row["status"] = "UNDER"
            else:
                row["status"] = "OK"
        rows.append(row)
        clock += secs

    total_words = sum(s["words"] for s in slides)
    cut_words = sum(c["words"] for c in cuts)
    est_seconds = total_words / wpm * 60.0
    result = {
        "wpm": wpm,
        "total_words": total_words,
        "est_seconds": round(est_seconds, 1),
        "est_time": mmss(est_seconds),
        "slides": rows,
        "cuts": [{"label": c["label"], "slide": c["slide_n"], "words": c["words"],
                  "saves": mmss(c["words"] / wpm * 60.0)} for c in cuts],
        "with_all_cuts_time": mmss((total_words - cut_words) / wpm * 60.0),
        "cut_share": round(cut_words / total_words, 3) if total_words else 0.0,
    }
    if speaking_minutes is not None:
        margin = speaking_minutes * 60.0 - est_seconds
        result["speaking_minutes"] = speaking_minutes
        result["margin_seconds"] = round(margin, 1)
        result["verdict"] = "WITHIN BUDGET" if margin >= 0 else "OVER BUDGET"
        if margin < 0 and cuts:
            result["cuts_rescue"] = ((total_words - cut_words) / wpm * 60.0
                                     <= speaking_minutes * 60.0)
    return result


def print_markdown(r, path):
    print("# Script timing — %s @ %d wpm" % (path, r["wpm"]))
    print()
    has_budget = any("budget_words" in s for s in r["slides"])
    if has_budget:
        print("| # | Slide | words | budget | time | starts at | status |")
        print("|---|-------|-------|--------|------|-----------|--------|")
        for s in r["slides"]:
            print("| %d | %s | %d | %s | %s | %s | %s |"
                  % (s["n"], s["title"], s["words"],
                     s.get("budget_words", "—"), s["time"], s["starts_at"],
                     s.get("status", "—")))
    else:
        print("| # | Slide | words | time | starts at |")
        print("|---|-------|-------|------|-----------|")
        for s in r["slides"]:
            print("| %d | %s | %d | %s | %s |"
                  % (s["n"], s["title"], s["words"], s["time"], s["starts_at"]))
    print()
    print("- Spoken total: %d words ≈ %s at %d wpm."
          % (r["total_words"], r["est_time"], r["wpm"]))
    if "speaking_minutes" in r:
        print("- Speaking time available: %s → margin %s."
              % (mmss(r["speaking_minutes"] * 60), mmss(r["margin_seconds"])))
    if r["cuts"]:
        print("- Cut list (%d blocks, %.0f%% of the talk):"
              % (len(r["cuts"]), r["cut_share"] * 100))
        for c in r["cuts"]:
            print("  - slide %d, '%s': %d words, saves %s"
                  % (c["slide"], c["label"], c["words"], c["saves"]))
        print("- With ALL cuts applied: ≈ %s." % r["with_all_cuts_time"])
    else:
        print("- No cut blocks marked. Mark 10–15%% of the talk with "
              "'<!-- CUT: label -->' … '<!-- END CUT -->'.")
    if "verdict" in r:
        print()
        print("VERDICT: %s" % r["verdict"])
        if r["verdict"] == "OVER BUDGET" and r["cuts"] and r.get("cuts_rescue"):
            print("(Applying every marked cut brings the talk back under: %s.)"
                  % r["with_all_cuts_time"])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Re-time a draft talk script: per-slide words, timing "
        "marks, cut savings, over/under verdict.")
    parser.add_argument("script", help="talk script markdown file "
                        "(one '## ' heading per slide)")
    parser.add_argument("--wpm", type=int, default=None,
                        help="speaking pace (default: the budget file's wpm, "
                        "else 130)")
    parser.add_argument("--minutes", type=float, default=None,
                        help="total slot minutes (with --qa) if no --budget")
    parser.add_argument("--qa", type=float, default=0.0,
                        help="Q&A minutes inside the slot (default 0)")
    parser.add_argument("--budget", default=None,
                        help="budget JSON from 'word_budget.py --json' for "
                        "slide-by-slide comparison")
    parser.add_argument("--json", action="store_true",
                        help="emit the analysis as JSON")
    args = parser.parse_args(argv)

    budget = None
    if args.budget:
        try:
            budget = load_budget(args.budget)
        except IOError as exc:
            return fail(str(exc))

    wpm = args.wpm or (int(budget["wpm"]) if budget else 130)
    if not (60 <= wpm <= 220):
        return fail("--wpm must be between 60 and 220 (got %d)" % wpm)

    speaking = None
    if args.minutes is not None:
        if args.qa < 0 or args.minutes - args.qa <= 0:
            return fail("--minutes minus --qa must be positive")
        speaking = args.minutes - args.qa
    elif budget:
        speaking = float(budget["speaking_minutes"])

    try:
        slides, cuts = parse_script(args.script)
    except (IOError, ValueError) as exc:
        return fail(str(exc))

    result = analyze(slides, cuts, wpm, speaking, budget)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_markdown(result, args.script)
    return 1 if result.get("verdict") == "OVER BUDGET" else 0


if __name__ == "__main__":
    sys.exit(main())
