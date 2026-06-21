# Timing and cuts — making the talk fit the slot

Pace math, buffers, timing marks, cut-list design, and rehearsal. The
companion file [script-craft.md](script-craft.md) covers the prose itself.

## Contents

1. [Pace math: why 130 wpm](#1-pace-math-why-130-wpm)
2. [Calibrating to the actual speaker](#2-calibrating-to-the-actual-speaker)
3. [Buffers: land early, never at the bell](#3-buffers-land-early-never-at-the-bell)
4. [Timing marks and checkpoints](#4-timing-marks-and-checkpoints)
5. [Slot norms and session-chair timecards](#5-slot-norms-and-session-chair-timecards)
6. [Designing the cut list](#6-designing-the-cut-list)
7. [Executing cuts live](#7-executing-cuts-live)
8. [The running-long protocol](#8-the-running-long-protocol)
9. [Rehearsal protocol](#9-rehearsal-protocol)
10. [Q&A timing](#10-qa-timing)

## 1. Pace math: why 130 wpm

Conversational English runs ~150–170 wpm; a good conference talk runs
slower — the audience is parsing dense material, often not in their first
language, in a room with imperfect acoustics. **130 wpm is the default
budget rate**: deliberate but not droning. The working range:

| wpm | when |
|-----|------|
| 100–115 | non-native speaker, heavy math, live captioning |
| 120–135 | the default band for technical talks |
| 140–150 | practiced native speaker, light material — the ceiling |
| >150 | never budget here; this is panic pace |

The arithmetic the scripts implement: `words = minutes × wpm`. A
12-minute speaking slot at 130 wpm is ~1,560 words — minus the buffer
(§3), ~1,495 scriptable words. That is the entire talk: about 2.5 pages
of double-spaced text for 12 minutes. Most first drafts are 30–50% over.

## 2. Calibrating to the actual speaker

The 1-minute test (do this before trusting any budget):

1. Take a ~200-word paragraph of the *speaker's own draft* (not news
   text — technical prose reads slower).
2. The speaker reads it aloud, standing, at presentation volume, once as
   a warm-up and once timed for exactly 60 seconds.
3. Count words covered in the timed pass. That is their wpm; pass it as
   `--wpm` to both scripts.
4. Subtract ~10 wpm from the measured rate for the real room (adrenaline
   speeds people up, but pauses, clicks, and looking at the audience slow
   the *word* rate down — the discount nets it out conservatively).

Re-budget if the measured rate differs from the assumed one by more than
10 wpm: at 12 minutes, a 15-wpm error is ~180 words ≈ 80 seconds.

## 3. Buffers: land early, never at the bell

`word_budget.py` reserves an unscripted buffer (default 0.5 min for
slots with more than 8 speaking minutes, 0.25 min below that). Reasons it
exists, none optional:

- laptop/clicker/adapter fumbling at the start (often 20–30 s of the slot),
- laughter, a mid-talk question, a stumble and recovery,
- the chair starting the clock at the introduction, not at slide 1.

Target: the scripted talk ends 30–60 seconds before the speaking time
does. Finishing a minute early reads as composed; finishing at the bell
means Q&A is being eaten; running over steals time from the next speaker
and is the single most-remembered failure mode at conferences.

## 4. Timing marks and checkpoints

The budget assigns each slide a start mark (`starts at 4:30`). In the
final script:

- Put the mark in the slide's stage direction line:
  `[4:30 — budget 260 words]`.
- Promote 2–3 of them to **checkpoints** the speaker actually uses
  mid-talk (start of the method, start of the results, the takeaway
  slide). At each checkpoint the speaker glances at the timer: ahead of
  the mark → carry on; more than ~30 s behind → execute the next cut
  (§7). Checking every slide is a tic; checking three times is control.
- The final checkpoint is the **Q&A handoff mark** (speaking time = slot
  − Q&A): the last scripted line must be said by then.

## 5. Slot norms and session-chair timecards

Typical CS-venue shapes — **starting points only, never assume**:

- Full-paper talks: 12–20 minutes *including* Q&A at most venues.
- CHI historically ~10 min + 5 min Q&A; ML venues use short orals
  (5–12 min) plus posters; lightning/spotlight slots run 1–7 min.
- Poster sessions expect a 2-minute and a 5-minute pitch — same scripting
  method, lightning shape.

**Ground truth is the presenter instructions and the acceptance email**,
which arrive after notification and change year to year. Venue profiles
under `venues/conferences/` do not encode slot lengths; if one is loaded
for context, re-verify anything timing-critical against its live
`cfp_url`/website before scripting. Many venues (ACM and IEEE both)
require an author to register and present — a no-show can pull the paper
from the proceedings, so confirm who is speaking, too.

Session chairs typically flash timecards at 5, 2, and 1 minute(s)
remaining or use a countdown timer; ask the venue which, and write the
cards into the protocol card (§8).

## 6. Designing the cut list

Mark 10–15% of the talk as droppable *while drafting*, not in a panic on
stage. Order of sacrifice:

1. **The second example** — one well-told example always beats two rushed.
2. **Mechanism detail** beyond what's needed to believe the results
   (inner-loop math, hyperparameters, the third architecture box).
3. **Related-work depth** — keep the one-sentence positioning, cut the
   tour.
4. **Extra results** — keep the headline figure; ablations and secondary
   tables go to backup slides.
5. **The outline slide narration** (and usually the outline slide).

Never cut: the problem statement, the key idea, the headline result, the
takeaway, or any limitation/honesty caveat — cutting caveats to save time
misrepresents the work.

Mechanics: wrap each candidate in `<!-- CUT: label -->` …
`<!-- END CUT -->` and re-run `script_timer.py`; it prices every cut in
seconds and reports whether applying all of them rescues an over-budget
talk. A good cut list is 2–3 blocks of 30–60 seconds each, spread across
the middle of the talk (cuts near the end can't save you — by then the
time is already spent).

## 7. Executing cuts live

A cut only works on stage if the seam is pre-sewn:

- Each cut block needs a **skip line** — the sentence *after* the block
  must read correctly whether or not the block was spoken. Test by
  reading the slide aloud with the block deleted.
- If a cut spans a whole slide, the stage direction is
  `[if cutting: double-click past slide 9]` and the incoming transition
  must not reference the skipped content.
- Mark the trigger in the script: `[2-min card → take CUT:
  second-example]`. Decisions made in advance don't cost stage presence.

## 8. The running-long protocol

Append this card to the script (filled in with the talk's own labels):

```
RUNNING-LONG PROTOCOL
- Checkpoint behind by <30 s  → tighten delivery, skip nothing.
- Behind by 30–90 s          → take the next CUT block, silently.
- 2-minute card               → jump to the results slide; say the
                                bridge line: "Let me jump to what
                                matters — the results."
- 1-minute card               → takeaway slide; deliver the one
                                memorable sentence and the thank-you.
NEVER: speak faster, skip the takeaway, or apologize for time.
```

Apologizing and accelerating are the two instincts to script out: both
spend time to broadcast distress. Jumping cleanly reads as confidence.

## 9. Rehearsal protocol

Three passes minimum; the timing is not real until pass 3:

1. **Desk pass** — read aloud seated, editing as you go; fix every
   stumble by rewriting the sentence (a stumble in rehearsal is a
   guaranteed stumble on stage). Re-run `script_timer.py` after edits.
2. **Standing pass** — full delivery, real clicker if possible, timer
   running; note the actual time at each checkpoint next to the budgeted
   mark.
3. **Recorded pass** — phone camera, then watch it. Check: total time
   (must land in the buffer zone), filler-word clusters, any slide where
   the spoken words just re-read the slide text.

If pass 3 lands >30 s over despite matching word count, the speaker's
real pace is below the budgeted wpm — re-budget with the measured rate
(§2) rather than trimming sentence by sentence.

## 10. Q&A timing

- Q&A length comes from the same presenter instructions; "12-minute
  talk + 3-minute Q&A" usually means a 15-minute slot the chair manages.
- Script the handoff line (script-craft.md §8) and keep the takeaway
  slide up — it is the only slide most questioners will reference.
- Budget answers at ~30 seconds: answer, one supporting fact, stop. Three
  questions fit in 3 minutes; rambling answers are running-over with
  extra steps.
- Backup slides live *after* the takeaway and cost zero talk time; the
  script's front matter should index them ("ablations: backup 2;
  proof sketch: backup 4") so the speaker can jump on demand.
- Full question anticipation and answer drills: hand off to the
  `rehearse-qa` skill once the script is frozen.
