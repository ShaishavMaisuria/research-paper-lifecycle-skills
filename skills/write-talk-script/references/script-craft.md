# Script craft — writing a talk for the ear

How to draft the spoken prose once the word budget exists. The companion
file [timing-and-cuts.md](timing-and-cuts.md) covers pace math, buffers,
cut-list design, and rehearsal.

## Contents

1. [Script file format](#1-script-file-format)
2. [Spoken register: the rules](#2-spoken-register-the-rules)
3. [The first 30 seconds](#3-the-first-30-seconds)
4. [Transitions between slides](#4-transitions-between-slides)
5. [Talking through figures and tables](#5-talking-through-figures-and-tables)
6. [Saying numbers aloud](#6-saying-numbers-aloud)
7. [Closing and the takeaway](#7-closing-and-the-takeaway)
8. [Q&A handoff lines](#8-qa-handoff-lines)
9. [Lightning talks (7 minutes or less)](#9-lightning-talks-7-minutes-or-less)
10. [Non-native speakers and accessibility](#10-non-native-speakers-and-accessibility)

## 1. Script file format

This is the contract `scripts/script_timer.py` parses. Keep to it exactly.

- **One `## ` heading per slide**, in deck order:
  `## Slide 4 — Key idea`. Text before the first `## ` is front matter and
  is not counted. Deeper headings (`###`) are unspoken notes.
- **`[Square brackets]` are stage directions and timing marks** — not
  spoken, not counted: `[4:30]`, `[click]`, `[point at the red curve]`,
  `[pause 2s]`, `[look up]`. Parentheses ARE spoken — `(pause)` costs a
  word; write `[pause]`.
- **`<!-- comments -->` are not counted.** Use them for notes to self.
- **Cut blocks** wrap optional passages:

  ```
  <!-- CUT: related-work-depth -->
  Two sentences you can drop if the chair shows the 2-minute card.
  <!-- END CUT -->
  ```

  Each marker on its own line; no nesting; never across a `## ` boundary.
- **The transition is the last sentence of each slide section**, written
  out in full (see §4). The click happens on the transition, not after it.
- Top of each slide section, after the heading: the timing mark and budget
  as a stage direction, e.g. `[4:30 — budget 260 words]`.

## 2. Spoken register: the rules

Paper prose read aloud sounds like a hostage statement. Rewrite, don't
recite:

- **One idea per sentence.** If a sentence has a subordinate clause with
  its own subordinate clause, split it.
- **Subject–verb–object, early.** The listener cannot re-read; front-load
  who does what.
- **Use contractions** ("we don't", "it's") — written-out forms sound
  robotic when read.
- **Say "we" and "you".** "We found X" beats "It was found that X". "You
  might wonder…" recruits the audience.
- **Signpost relentlessly.** Spoken talks have no section headings, so say
  them: "So that's the problem. Now, our idea." / "Three things make this
  hard. First…"
- **Repeat the key claim** at least twice — once when introduced, once in
  the close. Redundancy is a bug in print and a feature in speech.
- **Define every acronym aloud the first time**, even ones the paper
  assumes. Then add a pronunciation note in brackets for anything
  ambiguous: `[say: "see-graph"]`.
- **Cut hedges the paper needed** ("under assumptions detailed in §4.2")
  to a spoken-size honesty marker ("with one caveat I'll flag on the
  results slide").
- Read every paragraph aloud once while drafting. If you stumble, the
  audience drowns.

## 3. The first 30 seconds

Budget ~65 words for the title slide. Never start with "Thanks, today I'll
talk about <reading the title>". Pick one hook:

- **Problem-first:** "Every map-matching system in production today throws
  away ninety percent of its GPS points. Here's why that's a mistake."
- **Surprising number:** lead with the paper's most counterintuitive
  measurement, then "this talk explains that number."
- **Concrete scene:** one sentence placing the audience inside the
  problem ("You're routing ten million delivery vans…").

Then one sentence of who-and-what: "I'm <name>, this is joint work with
<collaborators>, and I'm going to show you <one-line contribution>."

## 4. Transitions between slides

Transitions are where unscripted talks bleed time. Write all of them. The
catalogue:

- **Forward reference:** "…and that raises the obvious question — does it
  scale? [click] Here's the answer."
- **Contrast:** "That's what everyone else does. [click] We do the
  opposite."
- **Zoom:** "So that's the system from ten thousand feet. [click] Let's
  open the one box that matters."
- **Consequence:** "Because the sketch is mergeable, [click] the
  distributed version is almost free."
- **Checkpoint** (use at section boundaries, ~2 per talk): "Quick
  checkpoint: problem, idea — now the evidence. [click]"

Rule: the transition sentence belongs to the *outgoing* slide's word count
and ends with `[click]`. If two adjacent slides need no spoken connective,
they should probably be one slide — flag it to the user.

## 5. Talking through figures and tables

Never say "as you can see". Walk it:

1. **Orient (one sentence):** what the axes/columns are. "X is dataset
   size, log scale; Y is matching error — lower is better."
2. **Point (stage direction):** `[trace the red curve]` "The red curve is
   us."
3. **The one takeaway (one sentence):** "Flat. Error doesn't grow with
   scale — that's the whole result."

Budget ~45–60 words per figure. If a figure needs more than three
sentences, the figure is too dense for a talk — tell the user to simplify
the slide (route to `make-slides`/`polish-tables-figures`), don't paper
over it with narration.

## 6. Saying numbers aloud

- Write numbers as they are spoken, so the timer charges them honestly:
  "thirty-one point seven percent" (five words), not "31.7%" (one token).
- Round when precision isn't the point: "just under a third". Keep exact
  digits only for headline results, and say the comparison, not the
  table: "twelve times faster than the best prior system".
- Never read a units-dense expression verbatim; convert: "1.2e6 points/s"
  becomes "about a million points a second".
- Every spoken number must appear in the paper. If the user wants a
  rounded form, keep a bracketed note with the exact figure:
  "roughly a third [paper: 31.7%, Table 3]".

## 7. Closing and the takeaway

Budget ~65 words. The last slide stays up during Q&A, so the script's
job is one memorable sentence, said slowly:

- "If you remember one thing: <the contribution as one clause>."
- Then where to go: "Paper, code, and the demo are at <short URL on the
  slide>. Come find me at the poster tonight."
- Never end on "…so, yeah, that's it." Script the full stop: "Thank you —
  I'm happy to take questions."

## 8. Q&A handoff lines

Script the seam so the speaker doesn't improvise it at the most nervous
moment:

- On time: "Thank you — I'm happy to take questions. [stay at the podium,
  takeaway slide up]"
- Running long (chair signaling): "I'll stop here — the short version of
  the last two slides is <one clause>. Questions?"
- No questions coming: hand the chair a planted opener in the script's
  front matter, e.g. "If useful, a natural first question is how this
  differs from <closest rival>."

Deep Q&A preparation (anticipated hostile/curious questions, answer
drills) is the `rehearse-qa` skill's job — hand off there after the script
is timed.

## 9. Lightning talks (7 minutes or less)

The full-talk shape does not compress; change shape instead:

- Four beats: problem (with hook) → the one idea → the one result → the
  pointer. One slide each is ideal.
- One result, one figure, zero architecture diagrams. The goal is a visit
  to the poster or the paper, not understanding.
- No outline slide, no "joint work with" beyond a name on the slide, no
  Q&A handoff unless the session has one.
- Budget at the same wpm — a 5-minute slot is ~615 words at 130 wpm. Every
  sentence earns its place or dies.

## 10. Non-native speakers and accessibility

- Budget at 110–120 wpm, not 130 — and say so in the report, it is the
  difference between a comfortable talk and a sprint.
- Prefer short common verbs over Latinate ones ("use" not "utilize",
  "show" not "demonstrate") — easier to say under stress.
- Add bracketed pronunciation guides for proper nouns and acronyms once,
  at first use.
- Script breath points with `[pause]` at section boundaries.
- If the venue live-captions talks, a steady pace and full sentences also
  make the captions usable — one more reason never to plan on "speaking
  faster".
