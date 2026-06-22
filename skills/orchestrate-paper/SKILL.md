---
name: orchestrate-paper
description: Goal-driven conductor for the whole idea-to-published-paper lifecycle. Takes a research idea plus experiments and a target ("submit to NeurIPS 2026", or "help me pick a venue") and runs a goal->plan->execute->verify->reflect loop. It plans the stages, invokes the right lifecycle skills in order (literature-review, write-abstract, preflight-check, simulate-reviewers, and the rest), checkpoints with the author before each stage, and re-verifies the live CFP via parse-cfp rather than trusting a cached profile. Use when a researcher says "take my idea to a submitted paper", "run the whole pipeline", "orchestrate the paper for venue X", "what's the plan from here", or "what's done and what's next". Copilot, not autonomous author. It stops to ask at every stage gate, never fabricates results or citations, and never submits. Trigger words - orchestrate, pipeline, end to end, whole paper, idea to submission.
---

# Orchestrate Paper

The **conductor**. The author brings a technical idea, their experiments, and a
target — a venue, or "help me pick one." This skill sets the **goal**
("submission-ready for venue X by deadline D") and runs a
**goal → plan → execute → verify → reflect** loop across the whole lifecycle:
it plans which sub-skills run and in what order, invokes them, **checkpoints
with the author at every stage gate**, and uses external, measurable signals —
not its own say-so — to confirm each stage actually moved the paper forward
before going on.

It does not write the paper *for* the author and it never submits anything. It
**coordinates the specialists** (each of which is its own skill) and keeps a
durable, reviewable record in `paper-workspace/` so the author can pause,
inspect, reject, and resume at any point.

This skill follows a few non-negotiable working principles at every checkpoint:
name assumptions, show competing readings, surface tradeoffs, stop when
confused, verify live, and keep the author the author.

## When to use

- "Take my idea + results to a submission-ready paper for VENUE." / "Run the
  whole pipeline." / "Be my copilot from idea to submission."
- "What's the plan from here?" / "What's done, what's next, what's blocking me?"
- Mid-cycle coordination: "I just got reviews back — what now?" or "we were
  accepted; drive camera-ready + artifacts."
- The author has many skills available and wants one entry point that sequences
  them instead of running ~20 by hand.

## When NOT to use

- A single, well-scoped task ("polish this paragraph", "check my citations").
  Call that one skill directly — the orchestration overhead isn't worth it.
- The author wants the *text written for them* with no review. That is not what
  this is; it is a copilot, and the author authors.

## Inputs

1. **The idea + experiments** — what the paper claims and the evidence the
   author already has. The orchestrator never invents results to fill gaps; a
   missing experiment is surfaced as a blocker, not fabricated.
2. **The target** — a venue+track, or `help me pick` (routes through
   `select-venue` first). Either way, the live CFP is re-verified, never trusted
   from a cached profile.
3. **Whatever draft exists** — from a blank idea to a near-final `.tex`. The
   plan adapts to the current state (see the state script below).
4. **`.paper-memory/`** — positioning (`profile.yml`), accumulated
   `lessons.md`, and `decisions.md` following the
   [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)
   pattern. Read at start.

## The loop

For the full stage → skill → exit-criterion → checkpoint-question table, read
[`references/pipeline-map.md`](references/pipeline-map.md). The loop per stage:

1. **GOAL.** State the goal in one sentence and the current target
   (venue+track+deadline). If the target is unset, run `select-venue`, record
   the choice in `.paper-memory/decisions.md`, and confirm with the author
   before treating it as fixed (principle #1, #6).

2. **PLAN.** Produce a reviewable, up-front plan — *which* sub-skills will run,
   in *what* order, and why — from the pipeline map, adapted to the draft's
   current state. Plan-then-execute beats reactive step-by-step here: the author
   gets a roadmap to approve. Show it; do not start executing a multi-stage plan
   silently.

3. **EXECUTE.** Run the stage's sub-skill(s). Each writes its artifact to the
   right `paper-workspace/<stage>/` folder and appends to `INDEX.md`. The
   orchestrator does not re-implement a specialist; it invokes it.

4. **VERIFY — on external signals, never self-judgment.** Confirm the stage met
   its exit criterion using a *measurable* check, because a model's
   self-reflection validates its own hallucinations (see
   [`references/verification-signals.md`](references/verification-signals.md)).
   Signals are concrete: `latexmk`/compile exit code, page count vs the live
   venue limit, anonymization linter, a BibTeX entry resolving to a real DOI via
   `verify-citations`, a claim tracing to a real result via `verify-claims`, the
   reported numbers reproducing from the artifact via `verify-results`, a
   checklist-presence grep, a script's pass/fail. If no external oracle exists
   for a step (a judgment call), say so and escalate to the author rather than
   letting the model grade itself.

5. **REFLECT — did it measurably improve?** Run `reflect-and-improve` against
   the stage goal and the before/after measurable target. Accept the stage only
   if the signal improved (or held while another did). **Never** accept a change
   that lowers a measurable score. Respect stop conditions (below) so the loop
   can't spin.

6. **CHECKPOINT.** Present at the stage gate: what was done, the tradeoffs, the
   competing interpretations where they exist, and the one checkpoint question
   from the pipeline map. **Wait for author sign-off** before the next stage.
   This is the durable pause point — state is on disk, so the author can leave
   and resume.

Run the state script at any time to see where things stand:

```
python3 scripts/pipeline_state.py status --workspace paper-workspace
```

It reads `paper-workspace/INDEX.md` (and an optional `pipeline-state.json`) and
prints **what's done / what's next / blocked-on** plus the current goal and the
pending checkpoint. Other subcommands: `init`, `set-goal`, `next`, `advance`,
`block`, `checkpoint`, and `signoff` (the author clears a raised checkpoint so
the loop can advance). Run `python3 scripts/pipeline_state.py --help`.

## Worked example (one loop, end to end)

Author: *"Take my idea + results to a submission-ready paper for NeurIPS 2026."*

```
# GOAL — record the target and open the durable log
python3 scripts/pipeline_state.py init --workspace paper-workspace
python3 scripts/pipeline_state.py set-goal --workspace paper-workspace \
    --goal "submission-ready for NeurIPS 2026 main track" \
    --venue "NeurIPS 2026" --track main --deadline "2026-05-15 AoE"
```

**Lock requirements first (hard stop).** Before planning, run `parse-cfp` on the
live CFP — never the cached `venues/conferences/neurips-2026.yml`. Suppose it
returns a 9-page limit and double-blind review, each carrying a source URL + the
date fetched. Raise the checkpoint and wait:

```
python3 scripts/pipeline_state.py checkpoint --workspace paper-workspace \
    --stage parse-cfp \
    --question "9pp, double-blind, NeurIPS checklist required, AoE deadline — confirm before we build on these?"
```

The author confirms. Now **PLAN**: show the stage list from the pipeline map
adapted to the draft's state (a half-written `.tex`, no related work yet), get
approval, then **EXECUTE** one stage — say `preflight-check`. **VERIFY on an
external signal**, not the model's say-so: `check_sections.py` exits 0 and the
PDF is 9 pages against the 9-page live limit. **REFLECT**: the desk-reject count
went 2 → 0, an improvement, so accept. Record it and raise the next checkpoint:

```
python3 scripts/pipeline_state.py advance --workspace paper-workspace \
    --stage preflight-check --signal "check_sections.py exit 0; 9pp <= 9 live limit; anonymizer clean"
python3 scripts/pipeline_state.py status --workspace paper-workspace   # done / next / blocked
```

If a later stage exposes a gap — e.g. `simulate-reviewers` predicts R2 will ask
for an ablation the author doesn't have — that is a **blocker, not something to
fabricate**: `block --stage simulate-reviewers --on "missing ablation R2 will ask for"`,
surface it, and let the author decide. Submission is never the orchestrator's
action: it hands over a ready package and stops.

## Stop conditions (so the loop can't spin forever)

Configurable, but always present — the loop must terminate:

- **Stage exit met** — the measurable criterion in the pipeline map passes.
- **Diminishing returns** — a reflect pass improves the metric by less than a
  small delta (e.g. prose-lint delta < N); stop polishing.
- **Hard iteration cap** — at most ~3 refine passes per stage, then escalate.
- **Budget cap** — stop and report when a token/time budget is hit.
- **Escalate to author** — when an unverified assumption gates the next step,
  the request has more than one reading, or the model is genuinely confused
  (principles #1, #2, #4). Escalation is a first-class outcome, not a failure.

## Live verification is mandatory

Venue rules change every cycle and the model's memory of them is stale by
construction. Before any
stage relies on a deadline, page limit, blinding level, template, checklist, or
artifact-badge rule, re-fetch it from the live CFP via `parse-cfp` and prefer
that over any `venues/conferences/*.yml` cached profile. Every venue fact the
orchestrator carries into a checkpoint must keep its source URL and the date it
was fetched, so the author can click through and confirm. Overconfidence is
**highest right after** a fetch, so re-check the fetched fact against the
primary source before acting on it. Never hardcode a venue rule into this skill.

## Output

- A running plan + per-stage artifacts under `paper-workspace/`, each logged in
  `INDEX.md` — the durable, reviewable record.
- A live **what's-done / what's-next / blocked-on** view from
  `pipeline_state.py`.
- A short narrative at each checkpoint: done, tradeoffs, the decision the author
  needs to make. Never a draft presented as finished-and-submitted.

## Adapt to your discipline

The pipeline map includes common conference and journal rails. Fork it: reorder
stages for a journal (revise-and-resubmit instead of rebuttal), swap citation
norms, and adjust which checklists, ethics statements, data policies, or
artifact tracks apply in your field. Keep the stage gates; change what runs
inside them.

## Guardrails

- **Copilot, never pilot.** It plans and coordinates; it never fabricates
  results or citations, never claims acceptance or predicts a decision, and
  **never submits** to any system on the author's behalf.
- **Verify on external signals, not self-reflection.** The completion signal is
  always a compile/lint/DOI-resolve/checklist/human-sign-off — never the model
  grading its own output (see `references/verification-signals.md`).
- **Stop at every stage gate.** Author sign-off is required between stages; high-
  stakes transitions (treating a CFP card as ground truth, sending a rebuttal,
  camera-ready) are hard stops.
- **Durable checkpoints.** Persist each stage artifact + `INDEX.md` before
  advancing, so a pause/restart never re-runs prior skills (avoiding duplicate
  API calls against the key-free search stack).
- **Don't double-deadline.** Track the artifact-evaluation / camera-ready track
  as a *separate* post-acceptance deadline, not folded into the paper deadline.
- One file under 500 lines; `references/` one level deep; scripts stdlib-only
  with `--help` and clean nonzero exits.

## Memory

Uses the shared `.paper-memory/` convention described by
[`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md).

- **At start:** read `profile.yml` (positioning), `lessons.md` (recurring
  habits to watch for across stages), and `decisions.md` (prior venue/track
  choices) so the plan is personalized and consistent with earlier decisions.
- **At end of each stage:** append a dated entry via
  `reflect-and-improve/scripts/reflect_log.py` —
  `date · orchestrate-paper · stage advanced / blocked, on what signal` — and
  log any venue/track decision to `decisions.md`.
- Create `.paper-memory/` on demand; offer to add it to `.gitignore`; local
  only, never uploaded.
