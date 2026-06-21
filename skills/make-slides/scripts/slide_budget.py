#!/usr/bin/env python3
"""Compute a slide budget and storyboard allocation for a conference talk.

Given the talk slot in minutes, prints how many content slides the deck can
afford (~1 slide/minute of speaking time, never more than 1.25) and a
problem-first section allocation (minutes + slides per section), in either
the full-talk shape (12-20 min) or the lightning shape (<= 7 min).

Slot lengths are NOT in venue profiles — they live in presenter
instructions and acceptance emails and vary year to year. Passing
--venue-profile only adds venue context and the live URL to re-verify
against; the minutes always come from you.

Stdlib only. No network.

Usage:
    python3 slide_budget.py --minutes 15
    python3 slide_budget.py --minutes 15 --qa 3 \\
        --venue-profile venues/conferences/sigspatial-2026.yml
    python3 slide_budget.py --minutes 5 --format lightning --json

Exit codes: 0 ok; 2 bad arguments or unreadable profile.
"""

import argparse
import json
import re
import sys

# (section, share of speaking time, minimum slides)
FULL_PLAN = [
    ("Title & hook (who you are, one-line what)",            0.05, 1),
    ("The problem & why it matters",                         0.20, 2),
    ("Why existing approaches fall short",                   0.10, 1),
    ("The key idea (the one insight, no machinery)",         0.15, 1),
    ("How it works (only what's needed to believe results)", 0.25, 2),
    ("Does it work (headline results)",                      0.20, 2),
    ("Takeaway + where to find more",                        0.05, 1),
]
LIGHTNING_PLAN = [
    ("Title + the problem (merged, hook first)", 0.25, 1),
    ("The one idea",                             0.35, 1),
    ("The one result",                           0.25, 1),
    ("Takeaway + pointer (paper/poster/QR)",     0.15, 1),
]

PROFILE_FIELD_RE = re.compile(r"^(id|name|year|cfp_url|website):\s*(.+?)\s*$")


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


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


def build_budget(minutes, qa, fmt):
    speaking = minutes - qa
    if speaking <= 0:
        raise ValueError("Q&A (%g min) leaves no speaking time in a %g-min slot"
                         % (qa, minutes))
    if fmt == "auto":
        fmt = "lightning" if minutes <= 7 else "full"
    plan = LIGHTNING_PLAN if fmt == "lightning" else FULL_PLAN
    target = round(speaking)            # ~1 slide / speaking minute
    hard_max = int(speaking * 1.25)

    sections, total_slides = [], 0
    for name, share, min_slides in plan:
        mins = speaking * share
        slides = max(min_slides, round(mins))
        total_slides += slides
        sections.append({"section": name, "minutes": round(mins, 1),
                         "slides": slides})
    return {
        "format": fmt,
        "slot_minutes": minutes,
        "qa_minutes": qa,
        "speaking_minutes": speaking,
        "target_slides": target,
        "hard_max_slides": hard_max,
        "planned_slides": total_slides,
        "sections": sections,
    }


def print_markdown(budget, venue):
    b = budget
    print("# Slide budget — %g-minute slot (%s talk)" % (b["slot_minutes"], b["format"]))
    print()
    if venue:
        print("Venue: %s" % venue.get("name", venue.get("id", "?")))
        if venue.get("cfp_url"):
            print("RE-VERIFY the slot length and Q&A policy against the live venue")
            print("pages before building: %s" % venue["cfp_url"])
            print("(profiles do not encode talk slots — presenter instructions and")
            print("your acceptance email are the ground truth).")
        print()
    print("- Speaking time: %g min (%g-min slot minus %g min Q&A)"
          % (b["speaking_minutes"], b["slot_minutes"], b["qa_minutes"]))
    print("- Content-slide target: ~%d slides (pace ~1/min); hard max %d."
          % (b["target_slides"], b["hard_max_slides"]))
    print("- Backup slides after the final slide are free — they don't count.")
    print()
    print("| Section | minutes | slides |")
    print("|---------|---------|--------|")
    for s in b["sections"]:
        print("| %s | %.1f | %d |" % (s["section"], s["minutes"], s["slides"]))
    print("| **Total** | **%.1f** | **%d** |"
          % (b["speaking_minutes"], b["planned_slides"]))
    if b["planned_slides"] > b["hard_max_slides"]:
        print()
        print("NOTE: section minimums exceed the hard max for this slot — merge")
        print("sections (lightning shape) rather than speeding up.")
    print()
    print("One claim per slide: each slide's title is the sentence you want")
    print("remembered if the audience reads nothing else on it.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Slide budget + problem-first storyboard allocation for a "
        "conference talk slot (full 12-20 min shape or <=7 min lightning shape).")
    parser.add_argument("--minutes", type=float, required=True,
                        help="total slot length in minutes (from presenter "
                        "instructions / acceptance email)")
    parser.add_argument("--qa", type=float, default=None,
                        help="minutes of Q&A inside the slot (default: 3 for "
                        "slots > 7 min, 0 for lightning slots)")
    parser.add_argument("--format", choices=["auto", "full", "lightning"],
                        default="auto", help="talk shape (default: auto — "
                        "lightning when the slot is <= 7 min)")
    parser.add_argument("--venue-profile", default=None,
                        help="optional venues/conferences/<id>.yml for venue "
                        "context and the live URL to re-verify against")
    parser.add_argument("--json", action="store_true",
                        help="emit the budget as JSON instead of markdown")
    args = parser.parse_args(argv)

    if not (1 <= args.minutes <= 120):
        return fail("--minutes must be between 1 and 120 (got %g)" % args.minutes)
    qa = args.qa
    if qa is None:
        qa = 0.0 if args.minutes <= 7 else 3.0
    if qa < 0:
        return fail("--qa cannot be negative")

    venue = None
    if args.venue_profile:
        try:
            venue = read_profile_fields(args.venue_profile)
        except IOError as exc:
            return fail(str(exc))

    try:
        budget = build_budget(args.minutes, qa, args.format)
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
