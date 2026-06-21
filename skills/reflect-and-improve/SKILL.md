---
name: reflect-and-improve
description: >-
  The reflection agent. Use it right after another skill produces an artifact
  such as a rewrite from polish-prose, a rebuttal, an abstract, a preflight
  fix, or a tailored draft to critique that output against the stated goal, the
  paper's .paper-memory/profile.yml, the relevant rubric, and past
  .paper-memory/lessons.md, then decide whether it actually improved. Trigger
  words include reflect, self-critique, did this get better, did my edit help,
  regression check, review my own output, iterate, refine, second pass,
  sanity-check the rewrite, and "is the new version actually better". Runs a
  bounded self-refine / Reflexion loop, guards against regressions, and appends
  durable, deduplicated, dated lessons to .paper-memory/lessons.md via a stdlib
  script so the toolkit gets sharper each paper. Reflection adds cost; it only
  pays off when there is a measurable target.
---

# Reflect and Improve

A meta-skill that runs *after* another skill in this toolkit produces an
artifact. It asks one question honestly: **did the change actually make the
paper better, measured against the goal — or did it just make it different?**
It critiques the new artifact against (a) the goal, (b) the paper's
`.paper-memory/profile.yml`, (c) the rubric that fits the task, and (d) past
`.paper-memory/lessons.md`; iterates within a hard budget; refuses to accept a
change that lowers a measurable score; and records what it learned so the next
paper starts smarter.

This is a copilot, not a pilot. It proposes; the author decides and edits.

## When to use

- Just after `polish-prose`, `write-rebuttal`, `write-abstract`,
  `preflight-check`, `tailor-to-venue`, `draft-related-work`, or any skill that
  emits an artifact, and you want a guarded second pass — "is the new version
  actually better, or did I introduce a regression?"
- "Reflect on / critique / self-review this rewrite before I keep it."
- "Did my edit help?" / "did this get better?" / "should I revert?"
- To capture a durable lesson ("we keep over-hedging the abstract") so the
  whole toolkit stops repeating the mistake on this and future papers.

## When NOT to use (be honest about cost)

Reflection is an extra LLM pass plus author attention. It only pays off when
there is a **measurable or rubric-anchored target**. Skip it (or keep it to a
single quick pass) when:

- There is no goal to measure against — pure preference edits ("make it sound
  nicer" with no rubric) reduce to taste; one read is enough.
- The producing skill already emits a hard score that did not change (e.g. a
  preflight that was clean before and after). Re-running its checker IS the
  reflection; do that instead of a narrative critique.
- The artifact is tiny (a one-line fix). The loop's overhead exceeds its value.

Say this to the user when they ask to reflect on something unmeasurable, then
offer the single-pass version.

## Inputs

1. **The artifact** to critique: the new text/file (and, ideally, the version
   it replaced, so "better" can be a diff, not a vibe).
2. **The goal**: what the producing skill was asked to achieve, in one
   sentence ("cut the abstract to 200 words without dropping the contribution",
   "answer R2's soundness concern").
3. **`.paper-memory/profile.yml`** — author/paper positioning. If it does not
   exist, create it first with `paper-profile` (or hand-write the minimal
   fields below). Reflection without positioning gives generic advice.
4. **A measurable target**, where one exists:
   - a script score (preflight error count, `polish-prose` readability/hedge
     counts, abstract word count vs venue bound, citation-verify failures);
   - or a rubric in `references/` (or `simulate-reviewers/references/rubrics.md`)
     scored 1–5 before and after.
5. **`.paper-memory/lessons.md`** — read at start so the critique personalizes
   and does not repeat advice already logged.

## The `.paper-memory/` convention

A per-project directory in the **user's paper working directory** (never in
this repo). The skill creates it at use time. **Tell the user to add
`.paper-memory/` to their `.gitignore`** unless they want positioning and
lessons versioned with the paper. It is local; nothing is uploaded.

- `profile.yml` — vertical (systems/theory/applied/empirical/survey/position),
  contribution_type, target audience & venue tier, risk appetite, writing
  preferences (link to `match-style`), constraints. Minimal starter in
  [references/paper-memory-schema.md](references/paper-memory-schema.md).
- `lessons.md` — accumulated, deduplicated, dated lessons. Other skills
  (`preflight-check`, `polish-prose`, `verify-citations`, `simulate-reviewers`)
  APPEND here when they catch something and READ here at start. Format and
  hygiene rules in the schema reference; enforced by `scripts/reflect_log.py`.
- `decisions.md` — venue/track/positioning decisions with rationale (written by
  `select-venue` / `plan-submission`; read here for context).

## Process

The loop is **Reflexion / self-refine, bounded**: critique → revise → re-score
→ keep only if it measurably improved. Cap iterations; stop on no gain.

1. **Establish the baseline — measure first.** Before critiquing, capture the
   *current* score of the artifact against its target. Pick the cheapest valid
   measure: re-run the producing skill's checker if it has one (preferred —
   deterministic), else score the relevant rubric 1–5. Record it:

   ```
   python3 scripts/reflect_log.py score --memory .paper-memory \
       --skill polish-prose --metric hedge-count --before 11
   ```

   If there is **no** measurable target, say so, do one qualitative pass, and
   stop — do not pretend a number exists.

2. **Read memory.** Surface recurring lessons so you neither repeat past advice
   nor re-introduce a known regression:

   ```
   python3 scripts/reflect_log.py recurring --memory .paper-memory
   ```

   Read `profile.yml`. A "tighten every sentence" critique is wrong for a
   position paper that values voice; a "add more hedging" critique is wrong for
   a high-risk-appetite systems paper. Tailor to the profile.

3. **Critique against the four anchors**, concretely and per-finding:
   - **Goal** — did it do the specific thing asked, fully and only that?
   - **Profile** — does it fit the vertical, audience, venue tier, voice?
   - **Rubric** — score the fitting dimensions (soundness, clarity,
     novelty-framing, responsiveness for rebuttals) 1–5 vs the prior version.
   - **Lessons** — does it repeat a logged mistake, or fix one?
   Write each as {what regressed/improved, evidence, minimal fix}.

4. **Decide — the regression guard is non-negotiable.** Compute the after
   score the same way as the baseline and compare:

   ```
   python3 scripts/reflect_log.py score --memory .paper-memory \
       --skill polish-prose --metric hedge-count --before 11 --after 6
   ```

   The script prints the delta and a verdict. **Never accept a change that
   lowers a measurable score** (more preflight errors, worse rubric mean, over
   the word bound, new citation failures) even if the prose "feels" better — a
   measurable regression beats a feeling. Outcomes: KEEP (measurably better) /
   REVERT (measurably worse — recommend the prior version) / TIE (no measurable
   change — defer to author taste, do not burn another iteration).

5. **Iterate within budget.** If KEEP but still short of target and under the
   iteration cap (default **3** total passes), produce a focused revision
   addressing the top finding only, then return to step 4. **Stop** when: the
   target is met, the cap is hit, or two consecutive passes show no measurable
   gain (diminishing returns — the honest signal to stop).

6. **Append durable lessons.** When the loop surfaces a pattern worth carrying
   forward, log it — deduplicated and dated:

   ```
   python3 scripts/reflect_log.py append --memory .paper-memory \
       --skill polish-prose --scope recurring \
       --issue "abstract over-hedges the contribution" \
       --rec "state the result as a claim once, then qualify in the body"
   ```

   `--scope this-paper` for paper-specific notes, `recurring` for cross-paper
   patterns (these are never pruned). The script dedupes on
   (skill, issue) and stamps the date.

7. **Hygiene.** Periodically prune stale `this-paper` lessons and enforce the
   cap (recurring lessons are always kept):

   ```
   python3 scripts/reflect_log.py prune --memory .paper-memory \
       --keep 50 --stale-days 365
   ```

   See [references/reflection-loop.md](references/reflection-loop.md) for the
   patterns this implements and their failure modes (reward hacking, sycophantic
   self-approval, oscillation), and
   [references/paper-memory-schema.md](references/paper-memory-schema.md) for
   the file formats.

## Output

- A critique: per-anchor findings (goal / profile / rubric / lessons), each
  with evidence and a minimal fix.
- A **KEEP / REVERT / TIE** verdict backed by a before→after number, not a
  vibe. On REVERT, recommend the prior version and explain which measure dropped.
- Zero or more lessons appended to `.paper-memory/lessons.md`.
- An honest statement of confidence and of what reflection could *not* measure.

## Adapt to your discipline

The loop and memory are field-agnostic; only the rubrics and metrics are
CS-flavored. Swap in your field's review form for the rubric, your venue's
length/format limits for the script metrics, and your citation style for the
verify hook. The `.paper-memory/` schema does not change.

## Guardrails

- **Never accept a measurable regression.** A lower score is a REVERT, however
  good the new version feels. This is the skill's whole point.
- **Reflection is not free.** State the cost; skip the loop when there is no
  measurable target and offer a single pass instead — do not manufacture a
  metric to justify iterating.
- **Bounded loop.** Hard iteration cap; stop on no measurable gain. Never spin.
- **No self-sycophancy.** Do not approve your own previous output by default;
  the baseline measure, not your prior reasoning, is the judge.
- Never fabricate scores, rubric numbers, or "improvements" — measure or say
  you could not. Route citation problems to `verify-citations`, desk-reject
  format problems to `preflight-check`.
- Never submit anything anywhere; never promise acceptance. `.paper-memory/`
  stays local — remind the user to `.gitignore` it.
