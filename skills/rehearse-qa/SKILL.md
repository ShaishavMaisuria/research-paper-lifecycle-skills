---
name: rehearse-qa
description: Simulated-audience Q&A rehearsal for conference talks, thesis defenses, job talks, and poster sessions. Use when a researcher says "rehearse Q&A", "practice questions", "mock Q&A", "grill me on my paper", "what will the audience ask", "hostile questions", "defense practice", "viva prep", "anticipate questions for my talk", or "questions I hope nobody asks". Sizes a drill to the real Q&A slot, fires hostile and curious questions one at a time in audience personas (hostile skeptic, methods stickler, statistician, adjacent-field expert, big-picture senior, confused newcomer, industry practitioner, self-promoter, rambler) calibrated to the venue family, mines the paper for dreaded weak-point questions, coaches concise answer-first responses, and grades transcripts deterministically for timing, hedging, filler, and buried answers. Coaches honest answers only — never spin — and never invents prior-work citations in drill questions.
---

# Rehearse Q&A

Drill the Q&A session before it happens. A simulated audience — hostile and
curious personas calibrated to the venue — asks questions one at a time,
grounded in the user's actual paper and slides; every answer gets coached
into a concise, honest, answer-first response; the questions the speaker
*hopes nobody asks* get prepared deliberately instead of dreaded vaguely.

## When to use

- "Grill me on my paper" / "rehearse the Q&A for my talk" / "mock Q&A"
- "What will the audience ask?" / "what's the worst question I could get?"
- "Practice my thesis defense / viva" / "prep me for job-talk questions"
- Poster-session prep (continuous Q&A, 2-minute and 5-minute pitches)
- After `write-talk-script` / `make-slides` — the talk is built, now the
  unscripted part gets rehearsed. After `simulate-reviewers` — its weakness
  list seeds the dreaded-question inventory.

## Inputs

1. The paper (and slides/script if they exist), in any readable form.
   Process them transiently — never copy paper text into this repo.
2. The setting and slot: conference talk / lightning / keynote / poster /
   defense / job talk, plus the Q&A length in minutes (ask if unknown).
3. Optional but better: a venue profile `venues/conferences/<venue>-<year>.yml`
   (schema in `venues/schema.yml`) so the audience matches the venue family.
   No profile? `parse-cfp` can create one, or run with the generic audience.

## Process

1. **Build the drill plan.** Run:

   ```
   python3 scripts/qa_drill.py --setting conference-talk --minutes 3 \
       --venue venues/conferences/<venue>-<year>.yml
   ```

   Deterministic and offline. Emits the slot math (how many questions the
   live slot actually fits, how many to drill), the persona lineup with
   per-persona quotas (venue-family calibrated when `--venue` is given),
   the round plan, answer-time targets, and a transcript skeleton for
   step 6. `--json` for machine output; `--help` for all settings. Exit
   codes: 0 ok, 2 bad arguments or missing/unparsable profile.

2. **Re-verify the slot — mandatory.** Venue profiles do NOT store talk
   slots, and Q&A lengths change per year, track, and session. Check the
   venue's live presenter instructions (start from the profile's `cfp_url`
   and `website`) for slot length, Q&A minutes, and format (chaired Q&A,
   no Q&A for lightning, poster logistics). Rehearsing to the wrong clock
   trains the wrong answers; state what was verified and when.

3. **Read the paper and build the dreaded-question inventory.** Mine
   limitations, claims, experimental scope, assumptions, cut material,
   rebuttal history, odd numbers, ethics/data provenance — full checklist
   and the per-question prep-card template in
   [references/dreaded-questions.md](references/dreaded-questions.md).
   Rank 8–15 questions by probability x damage and build an honest answer
   card for each. If a weakness is fixable before the talk, say so — fix
   beats rehearsal.

4. **Run the drill, one question at a time.** Follow the round plan
   (warm-up → hostile gauntlet → dreaded finale → rapid-fire → curveballs).
   Ask in persona, grounded in the actual paper/slides, then WAIT for the
   user's answer before continuing — never dump a question list. Persona
   voices, follow-up behavior, and venue/setting calibration are in
   [references/audience-personas.md](references/audience-personas.md).
   Prior-work rule: a drill question may only cite real papers verified via
   `find-papers` + `verify-citations`, otherwise it stays nameless
   ("suppose someone claims prior work did X"). Never invent a citation.

5. **Coach every answer.** After each user answer, break persona and give
   the five-part feedback (verdict / what worked / the one fix / a model
   answer built only from what the paper supports / re-drill if it failed)
   per [references/answer-coaching.md](references/answer-coaching.md).
   Coach the answer-first template: headline sentence, one piece of
   evidence, stop. Re-ask hard-failed questions later — an answer is
   drilled only when it lands twice.

6. **Grade the transcript deterministically.** Record the exchanges in the
   skeleton from step 1 (the user's answers as spoken/typed), then run:

   ```
   python3 scripts/grade_answers.py transcript.md --target 45 --max 75
   ```

   (Targets come from the drill plan.) Flags per answer: estimated speaking
   time vs target/cap, unanswered questions, hedge openers, filler density,
   and buried answers to yes/no questions. Exit codes: 0 ready, 1 re-drill
   needed, 2 bad input. `--json` for machine output.

7. **Deliver the readiness report.** Summarize: questions that land,
   questions needing another round (with the one fix each), the dreaded-
   question crib sheet (question → memorized headline → one number), and
   any "fix the slide instead" items routed back to `make-slides` /
   `write-talk-script`.

## Output

An interactive drill session plus, at the end (in chat; written to a file
only if the user asks): the graded transcript report from
`grade_answers.py`, the dreaded-question crib sheet for morning-of review,
and the re-drill list. No predictions — a drilled answer is preparation,
not a guarantee of what gets asked.

## Adapt to your discipline

Audience lineups are keyed on the venue `family:` field in
`scripts/qa_drill.py` (`FAMILY_LINEUPS`) — fork and add your community's
audience (e.g. a humanities seminar respondent, a clinical grand-rounds
panel) plus any new personas in `PERSONAS` and
[references/audience-personas.md](references/audience-personas.md). The
settings table (`SETTINGS`) takes new formats the same way.

## Guardrails

- **Honest answers only.** Never coach wording that hides, minimizes, or
  misrepresents a limitation or result; decline "help me avoid admitting X"
  framings and offer the concede-and-scope answer instead (it also performs
  better). Fixable weaknesses should be fixed, not rehearsed around.
- **Never fabricate citations** — in questions or model answers. Prior-work
  references in drills go through `find-papers` + `verify-citations` or
  stay nameless.
- Never put claims in the user's mouth the paper cannot support; model
  answers use only the paper's own evidence.
- Re-verify slot/session facts against the live venue pages (step 2 is not
  optional); profiles never carry talk-slot ground truth.
- Process the paper transiently; never store paper text in this repo.
- Never contact session chairs, committees, or any submission/conference
  system on the user's behalf.
- This is rehearsal, not prophecy: never claim the drilled questions are
  what will actually be asked, and never predict talk reception.
