#!/usr/bin/env python3
"""Time a poster pitch: word count vs the slot, with delivery flags.

Reads a pitch written in markdown/plain text and reports whether it fits
the stated length (2-minute and 5-minute pitches are the poster-session
standard) at a conversational pace. Poster delivery runs SLOWER than a
podium talk — you hold eye contact, point at the poster, and get
interrupted — so the default is 125 words/minute.

Not spoken (excluded from the count):
  - markdown headings (# ...) — they label sections of the pitch
  - [bracketed stage directions] like [point at hero figure]
  - <!-- comments -->

Also flags sentences over 35 words (hard to say in one breath) and a
missing closing question/invitation (a pitch should end by handing the
conversation to the visitor).

Stdlib only. No network.

Usage:
    python3 pitch_check.py poster/pitch-2min.md --minutes 2
    python3 pitch_check.py poster/pitch-5min.md --minutes 5 --wpm 130
    python3 pitch_check.py poster/pitch-2min.md --minutes 2 --json

Exit codes: 0 fits the slot (within +5%); 1 over the slot; 2 bad
arguments or unreadable file.
"""

import argparse
import json
import re
import sys

DEFAULT_WPM = 125
OVER_TOLERANCE = 1.05
UNDER_NOTE = 0.60
LONG_SENTENCE = 35


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def spoken_text(raw):
    text = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    text = "\n".join(l for l in text.splitlines()
                     if not l.lstrip().startswith("#"))
    text = re.sub(r"\[[^\]\n]*\]", " ", text)  # stage directions
    return text


def count_words(text):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text))


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return [p for p in parts if count_words(p) > 0]


def mmss(seconds):
    seconds = max(0, int(round(seconds)))
    return "%d:%02d" % (seconds // 60, seconds % 60)


def analyze(raw, minutes, wpm):
    text = spoken_text(raw)
    words = count_words(text)
    sents = sentences(text)
    long_sents = [(count_words(s), s) for s in sents
                  if count_words(s) > LONG_SENTENCE]
    est_seconds = words / wpm * 60.0
    budget_words = int(minutes * wpm)
    ends_with_question = bool(sents) and sents[-1].rstrip().endswith("?")
    return {
        "words": words,
        "sentences": len(sents),
        "wpm": wpm,
        "minutes": minutes,
        "budget_words": budget_words,
        "estimated_time": mmss(est_seconds),
        "estimated_seconds": round(est_seconds, 1),
        "over_budget": est_seconds > minutes * 60 * OVER_TOLERANCE,
        "under_note": est_seconds < minutes * 60 * UNDER_NOTE,
        "long_sentences": [{"words": w, "text": s[:90]} for w, s in long_sents],
        "ends_with_question": ends_with_question,
    }


def print_markdown(r, path):
    print("# Pitch timing — %s @ %d wpm" % (path, r["wpm"]))
    print()
    print("- %d spoken words; estimated %s for a %g-minute pitch "
          "(budget ~%d words)"
          % (r["words"], r["estimated_time"], r["minutes"], r["budget_words"]))
    if r["over_budget"]:
        print("- OVER BUDGET: cut ~%d words. Cut detail, not the hook or the"
              % max(0, r["words"] - r["budget_words"]))
        print("  headline number — visitors who want depth will ask.")
    elif r["under_note"]:
        print("- Well under the slot — fine for a pitch (it buys conversation")
        print("  time), but check nothing essential is missing: problem, key")
        print("  idea, headline number, invitation.")
    else:
        print("- Fits the slot.")
    for s in r["long_sentences"]:
        print("- LONG SENTENCE (%d words): \"%s…\" — split it; you have to say"
              % (s["words"], s["text"]))
        print("  this out loud while pointing at things.")
    if not r["ends_with_question"]:
        print("- Does not end with a question/invitation — hand the")
        print("  conversation over (\"Want to see how the scorer works?\").")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Time a poster pitch (2-min / 5-min) at a conversational "
        "pace; flags over-budget length, unsayable sentences, and a missing "
        "closing invitation.")
    parser.add_argument("pitch", help="path to the pitch markdown/text file")
    parser.add_argument("--minutes", type=float, required=True,
                        help="pitch length to check against (typically 2 or 5)")
    parser.add_argument("--wpm", type=int, default=DEFAULT_WPM,
                        help="speaking pace (default %d — poster delivery is "
                        "slower than podium pace)" % DEFAULT_WPM)
    parser.add_argument("--json", action="store_true",
                        help="emit the analysis as JSON instead of markdown")
    args = parser.parse_args(argv)

    if args.minutes <= 0:
        return fail("--minutes must be positive")
    if not (60 <= args.wpm <= 220):
        return fail("--wpm must be between 60 and 220 (got %d)" % args.wpm)
    try:
        with open(args.pitch, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as exc:
        return fail("cannot read %s: %s" % (args.pitch, exc))

    r = analyze(raw, args.minutes, args.wpm)
    if r["words"] == 0:
        return fail("no spoken words found in %s — is this the pitch file?"
                    % args.pitch)

    if args.json:
        json.dump(r, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_markdown(r, args.pitch)

    return 1 if r["over_budget"] else 0


if __name__ == "__main__":
    sys.exit(main())
