---
name: write-talk-script
description: Writes a timed, word-budgeted speaker script for an exact conference-talk slot (e.g. a 12-minute talk plus 3-minute Q&A, or a 5-minute lightning talk). Use when a researcher mentions talk script, presentation script, speaker notes, conference talk, lightning talk, rehearsal, "what do I say on each slide", or "my talk is running long". Turns a slide deck or outline into spoken-register prose with a per-slide word budget at ~130 words/minute (calibratable), cumulative timing marks, written-out transitions, a marked cut list worth 10-15% of the talk for running long, and a Q&A handoff. Bundled stdlib-only Python scripts compute the budget (word_budget.py) and re-time any draft (script_timer.py with per-slide timing, cut savings, and an over/under verdict). Venue-aware but treats presenter instructions and the acceptance email as ground truth for slot length; never invents results — every claim spoken must come from the paper.
---

# Write Talk Script

Produce a speaker script that fits an exact talk slot: every slide gets a
word budget at the speaker's real pace, a cumulative timing mark, a
written-out transition, and a marked cut list so running long on stage has a
pre-planned answer. Slides tell the audience what to look at; this script is
what the speaker actually says. It is the post-acceptance companion to
`make-slides`.

## When to use

- "Write the script for my 12-minute SIGSPATIAL talk" / "15-minute slot
  including 3 minutes of Q&A — what do I say?"
- "Turn my deck into speaker notes I can rehearse from"
- "My talk is running long — what do I cut?"
- "I have a 5-minute lightning talk / spotlight"
- After `make-slides`, before the first timed rehearsal.

## Inputs

1. The exact slot: total minutes, and whether Q&A is inside the slot or
   handled separately. **Ground truth is the presenter instructions and the
   acceptance email**, not memory and not venue profiles.
2. The deck or an outline (slide titles in order). No deck yet? Run
   `make-slides` first.
3. The paper (camera-ready preferred) — the only legitimate source for every
   number and claim spoken.
4. Optional: `venues/conferences/<venue>-<year>.yml` for venue context, and
   the speaker's measured pace in words per minute.

## Process

1. **Pin down the slot facts.** Ask for: total minutes, Q&A inside or
   outside, session language, and whether the chair uses timecards. If a
   venue profile exists, use it for context only and re-verify against the
   live `cfp_url` / venue website — profiles do not encode talk slots, and
   slots change year to year. Typical shapes (verify, never assume):
   full papers 12–20 min including Q&A; CHI historically ~10 min + 5 Q&A;
   lightning/spotlight 1–7 min. Details in
   [references/timing-and-cuts.md](references/timing-and-cuts.md).

2. **Calibrate the pace.** Default to 130 wpm — a deliberate conference
   pace. If the speaker can do the 1-minute read-aloud calibration
   (timing-and-cuts.md §2), use their measured number; suggest 110–120 wpm
   for non-native speakers or dense technical material. Never exceed 150.

3. **Build the outline file.** One line per slide (a `- ` bullet or `## `
   heading), in deck order. Pin slides that need fixed time with a trailing
   `| <minutes>` (e.g. `- Key idea | 2`). Title and takeaway slides
   typically pin at 0.5.

4. **Compute the word budget.** Run:

   ```
   python3 scripts/word_budget.py --minutes 15 --qa 3 --outline outline.md \
       [--wpm 120] [--venue-profile venues/conferences/<venue>.yml]
   ```

   Also save the machine-readable form for step 6:
   `python3 scripts/word_budget.py ... --json > budget.json`.
   The script reserves a safety buffer (default 0.5 min) so the talk lands
   early, never at the bell. No outline yet? `--slides N` splits evenly.

5. **Draft the script slide by slide,** inside each slide's word budget, in
   spoken register — short sentences, contractions, signposts, numbers
   written the way they are said. Follow
   [references/script-craft.md](references/script-craft.md) for the file
   format (one `## ` heading per slide, `[bracketed]` stage directions and
   timing marks, written-out transitions as the last sentence of each
   slide), opening and closing patterns, and figure walkthroughs. Every
   factual claim must trace to the paper — quote the paper's numbers, then
   render them speakable.

6. **Time the draft.** Run:

   ```
   python3 scripts/script_timer.py talk-script.md --budget budget.json
   ```

   (or `--minutes 15 --qa 3` without a budget file). Fix `OVER` slides by
   cutting words, not by planning to speak faster; re-run until the verdict
   is `WITHIN BUDGET`. Exit codes: 0 within budget, 1 over, 2 bad input.

7. **Build the cut list.** Mark 2–3 cuttable passages totaling 10–15% of
   the talk with `<!-- CUT: label -->` … `<!-- END CUT -->` (each marker on
   its own line, no nesting, no crossing slide boundaries). What to cut
   first and what must never be cut: timing-and-cuts.md §6. Re-run
   `script_timer.py` — it reports each cut's seconds saved and whether
   applying all cuts rescues an overrun.

8. **Finalize the rehearsal package.** Insert the budget's timing mark at
   the top of each slide section (e.g. `[4:30]`), add the Q&A handoff line,
   and append the rehearsal protocol and the on-stage running-long protocol
   (timing-and-cuts.md §8–9). Tell the user the timing holds only after at
   least one full out-loud rehearsal with a timer.

## Output

- `talk-script.md` — one `## ` section per slide: timing mark, word count,
  spoken prose with stage directions, transition sentence, cut blocks; ends
  with the Q&A handoff and a rehearsal checklist.
- `budget.json` — the per-slide budget, reusable on every re-timing pass.
- A timing report (from `script_timer.py`) showing the talk fits, with the
  cut list and seconds saved per cut.

## Adapt to your discipline

The defaults target CS conference talks (12–20 min, slide-driven, English).
For other fields, adjust the section shares in your outline (e.g. methods-
heavy medical talks), the pace (`--wpm`), and the venue norms in
timing-and-cuts.md — the scripts are field-agnostic.

## Guardrails

- Never invent results, numbers, quotes, or citations for the script —
  every claim spoken must come from the user's paper. New references go
  through `verify-citations` first.
- Timing is an estimate, not a guarantee: never tell the user the talk
  "fits" without a real timed rehearsal; word-rate math ignores nerves,
  laser-pointer detours, and clicker failures (that is what the buffer and
  cut list are for).
- Venue profiles never override presenter instructions or the acceptance
  email for slot length; re-verify against the live `cfp_url` before
  scripting.
- Preserve the speaker's voice and precise technical claims — spoken
  register is a rewrite for the ear, not a simplification of the science,
  and not a read-aloud of paper paragraphs.
- Never upload the script or slides to any speaker portal, or submit
  anything on the user's behalf.
