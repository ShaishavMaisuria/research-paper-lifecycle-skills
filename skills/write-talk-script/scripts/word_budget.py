#!/usr/bin/env python3
"""Per-slide word budget and timing marks for a conference talk slot.

Given the slot length, the Q&A minutes inside the slot, and a speaking
pace (default 130 wpm -- a deliberate conference pace), prints how many
words the talk and each slide can afford, plus the cumulative timing
mark (m:ss) at which each slide should start. A small safety buffer is
reserved so the scripted talk lands early, never at the bell.

Slides come from --slides N (even time split) or from an outline file
(--outline): every markdown heading, bullet, or numbered line is one
slide, and a trailing "| <minutes>" pins that slide's duration; the
remaining time is split evenly across unpinned slides.

Slot lengths are NOT in venue profiles -- presenter instructions and the
acceptance email are the ground truth, and they change year to year.
--venue-profile only adds venue context and the live URL to re-verify
against; the minutes always come from you.

Stdlib only. No network.

Usage:
    python3 word_budget.py --minutes 15 --qa 3 --slides 12
    python3 word_budget.py --minutes 15 --qa 3 --outline outline.md --json
    python3 word_budget.py --minutes 5 --wpm 140 --slides 4

Exit codes: 0 ok; 2 bad arguments, unreadable file, or impossible budget
(e.g. pinned slide minutes exceed the available speaking time).
"""

import argparse
import json
import re
import sys

# slides are '## ' headings, bullets, or numbered lines; a single-'#'
# document title is NOT a slide
OUTLINE_LINE_RE = re.compile(r"^\s*(?:#{2,6}\s+|[-*+]\s+|\d+[.)]\s+)(.+?)\s*$")
PROFILE_FIELD_RE = re.compile(r"^(id|name|year|cfp_url|website):\s*(.+?)\s*$")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def mmss(seconds):
    seconds = int(round(seconds))
    return "%d:%02d" % (seconds // 60, seconds % 60)


def read_profile_fields(path):
    """Read top-level scalar identity fields from a venue profile (no YAML lib)."""
    fields = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                m = PROFILE_FIELD_RE.match(line)
                if m:
                    value = m.group(2)
                    if " #" in value:
                        value = value.split(" #", 1)[0].rstrip()
                    fields[m.group(1)] = value.strip("'\"")
    except OSError as exc:
        raise IOError("cannot read venue profile %s: %s" % (path, exc))
    if "id" not in fields and "name" not in fields:
        raise IOError("%s does not look like a venue profile (no id:/name:)" % path)
    return fields


def parse_outline(path):
    """Return [(title, pinned_minutes_or_None), ...] from an outline file."""
    slides = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        raise IOError("cannot read outline %s: %s" % (path, exc))
    for lineno, raw in enumerate(lines, 1):
        m = OUTLINE_LINE_RE.match(raw)
        if not m:
            continue
        title, pinned = m.group(1), None
        if "|" in title:
            title, _, tail = title.rpartition("|")
            title = title.strip()
            tail = tail.strip().rstrip("m").rstrip()
            try:
                pinned = float(tail)
            except ValueError:
                raise ValueError(
                    "%s:%d: cannot parse pinned minutes %r (use 'Title | 2.5')"
                    % (path, lineno, tail))
            if pinned <= 0:
                raise ValueError("%s:%d: pinned minutes must be > 0" % (path, lineno))
        if not title:
            raise ValueError("%s:%d: empty slide title" % (path, lineno))
        slides.append((title, pinned))
    if not slides:
        raise ValueError(
            "%s contains no slide lines (use '## ' headings, '- ' bullets, or "
            "'1.' items; a single-'#' title line is not a slide)" % path)
    return slides


def build_budget(minutes, qa, wpm, buffer_minutes, slides):
    speaking = minutes - qa
    if speaking <= 0:
        raise ValueError("Q&A (%g min) leaves no speaking time in a %g-min slot"
                         % (qa, minutes))
    if buffer_minutes is None:
        buffer_minutes = 0.5 if speaking > 8 else 0.25
    scripted = speaking - buffer_minutes
    if scripted <= 0:
        raise ValueError("buffer (%g min) leaves no scripted time in %g speaking "
                         "minutes" % (buffer_minutes, speaking))

    pinned_total = sum(p for _, p in slides if p is not None)
    unpinned = [i for i, (_, p) in enumerate(slides) if p is None]
    if pinned_total > scripted + 1e-9:
        raise ValueError(
            "pinned slide minutes (%g) exceed scripted time (%g = %g slot - %g "
            "Q&A - %g buffer); unpin or shorten slides"
            % (pinned_total, scripted, minutes, qa, buffer_minutes))
    if unpinned:
        share = (scripted - pinned_total) / len(unpinned)
        if share <= 0:
            raise ValueError("pinned slides consume all scripted time; nothing "
                             "left for %d unpinned slides" % len(unpinned))
    else:
        share = 0.0

    out_slides, clock = [], 0.0
    for n, (title, pinned) in enumerate(slides, 1):
        mins = pinned if pinned is not None else share
        out_slides.append({
            "n": n,
            "title": title,
            "start": mmss(clock * 60),
            "minutes": round(mins, 2),
            "words": int(round(mins * wpm)),
        })
        clock += mins
    unallocated = scripted - clock
    return {
        "wpm": wpm,
        "slot_minutes": minutes,
        "qa_minutes": qa,
        "speaking_minutes": round(speaking, 2),
        "buffer_minutes": round(buffer_minutes, 2),
        "scripted_minutes": round(clock, 2),
        "unallocated_minutes": round(unallocated, 2) if unallocated > 0.05 else 0,
        "total_words": sum(s["words"] for s in out_slides),
        "qa_handoff": mmss(speaking * 60),
        "slides": out_slides,
    }


def print_markdown(b, venue):
    print("# Word budget — %g-min slot, %g-min Q&A, %d wpm"
          % (b["slot_minutes"], b["qa_minutes"], b["wpm"]))
    print()
    if venue:
        print("Venue: %s" % venue.get("name", venue.get("id", "?")))
        if venue.get("cfp_url"):
            print("RE-VERIFY the slot length and Q&A policy against the live venue")
            print("pages before scripting: %s" % venue["cfp_url"])
            print("(profiles do not encode talk slots — presenter instructions and")
            print("your acceptance email are the ground truth).")
        print()
    print("- Speaking time: %g min (slot minus Q&A); buffer reserved: %g min."
          % (b["speaking_minutes"], b["buffer_minutes"]))
    print("- Scripted time: %g min → total budget **%d words**."
          % (b["scripted_minutes"], b["total_words"]))
    if b["unallocated_minutes"]:
        print("- Unallocated: %g min (pinned slides total less than scripted time)."
              % b["unallocated_minutes"])
    print("- Q&A handoff mark: say your last line by %s." % b["qa_handoff"])
    print()
    print("| # | Slide | starts at | minutes | words |")
    print("|---|-------|-----------|---------|-------|")
    for s in b["slides"]:
        print("| %d | %s | %s | %.2f | %d |"
              % (s["n"], s["title"], s["start"], s["minutes"], s["words"]))
    print("| | **Total** | | **%.2f** | **%d** |"
          % (b["scripted_minutes"], b["total_words"]))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Per-slide word budget and timing marks for a conference "
        "talk slot (default pace 130 wpm).")
    parser.add_argument("--minutes", type=float, required=True,
                        help="total slot length in minutes, including any Q&A "
                        "inside it (from presenter instructions)")
    parser.add_argument("--qa", type=float, default=0.0,
                        help="minutes of Q&A inside the slot (default 0; if Q&A "
                        "is separate from your slot, leave it 0)")
    parser.add_argument("--wpm", type=int, default=130,
                        help="speaking pace in words per minute (default 130; "
                        "calibrate with a 1-minute read-aloud test)")
    parser.add_argument("--buffer", type=float, default=None,
                        help="safety buffer minutes reserved unscripted "
                        "(default: 0.5 when speaking time > 8 min, else 0.25)")
    parser.add_argument("--slides", type=int, default=None,
                        help="number of slides, split evenly (alternative to "
                        "--outline)")
    parser.add_argument("--outline", default=None,
                        help="outline file: one heading/bullet/numbered line per "
                        "slide, optional trailing '| <minutes>' to pin a slide")
    parser.add_argument("--venue-profile", default=None,
                        help="optional venues/conferences/<id>.yml for context "
                        "and the live URL to re-verify against")
    parser.add_argument("--json", action="store_true",
                        help="emit the budget as JSON (feed it to "
                        "script_timer.py --budget)")
    args = parser.parse_args(argv)

    if not (1 <= args.minutes <= 120):
        return fail("--minutes must be between 1 and 120 (got %g)" % args.minutes)
    if args.qa < 0:
        return fail("--qa cannot be negative")
    if not (60 <= args.wpm <= 220):
        return fail("--wpm must be between 60 and 220 (got %d)" % args.wpm)
    if args.buffer is not None and args.buffer < 0:
        return fail("--buffer cannot be negative")
    if (args.slides is None) == (args.outline is None):
        return fail("give exactly one of --slides N or --outline FILE")

    if args.outline:
        try:
            slides = parse_outline(args.outline)
        except (IOError, ValueError) as exc:
            return fail(str(exc))
    else:
        if args.slides < 1:
            return fail("--slides must be >= 1")
        slides = [("Slide %d" % i, None) for i in range(1, args.slides + 1)]

    venue = None
    if args.venue_profile:
        try:
            venue = read_profile_fields(args.venue_profile)
        except IOError as exc:
            return fail(str(exc))

    try:
        budget = build_budget(args.minutes, args.qa, args.wpm, args.buffer, slides)
    except ValueError as exc:
        return fail(str(exc))

    if args.json:
        if venue:
            budget["venue"] = venue
        json.dump(budget, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_markdown(budget, venue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
