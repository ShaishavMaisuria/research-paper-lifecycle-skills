# The bounded reflection loop — patterns and failure modes

This skill implements a deliberately small, deliberately suspicious
self-critique loop. The patterns it borrows are well known; so are their ways
of going wrong. This file is the reasoning behind the `Process` steps in
`SKILL.md` and the rules baked into `scripts/reflect_log.py`.

## The patterns it implements

**Self-refine.** An agent critiques its own output and revises it, repeating
until a stopping condition. Cheap to run, but with no external signal it
optimizes for *looking* better to itself — see "sycophantic self-approval"
below. The fix is to ground every accept/reject in an *external* measure, not
the agent's own narration.

**Reflexion.** Turn a verbal critique into a written lesson that conditions
later attempts, so the system improves across episodes, not just within one.
`.paper-memory/lessons.md` is exactly this episodic memory; `reflect_log.py
append`/`recurring` are its read/write API. The cross-paper payoff is the whole
reason the directory persists.

Both only help **when there is a target to measure against**. Applied to pure
taste ("make it punchier") they add cost and produce confident, ungrounded
edits. The skill says so out loud and offers a single pass instead.

## Why it is bounded

Unbounded self-critique does not converge — it oscillates (edit A, "improve" to
B, "improve" B back toward A) or drifts away from the goal while each step feels
locally better. So:

- **Hard iteration cap** (default 3 total passes). Three passes captures almost
  all of the real gain; beyond that you are usually polishing noise.
- **Stop on no measurable gain.** Two consecutive passes with no score
  improvement is the honest signal that the loop has nothing left to give. A
  `TIE` from `reflect_log.py score` is that signal made explicit.
- **One finding per revision.** Fixing the single highest-impact issue per pass
  keeps the diff legible and the measurement attributable. Shotgun rewrites make
  it impossible to know *which* change moved the number.

## The regression guard (the core invariant)

> Never accept a change that lowers a measurable score.

A reflection step has three honest outcomes, and `reflect_log.py score` returns
them:

| Outcome | Condition | Action | Exit |
|---|---|---|---|
| KEEP | score improved in the metric's direction | adopt the new version | 0 |
| TIE | score unchanged | defer to author taste; do **not** iterate again to chase it | 0 |
| REVERT | score got worse | recommend the **prior** version; never keep | 1 |

The nonzero exit on REVERT lets a wrapper or the author *refuse* the change
mechanically. "The new prose feels better" does not override a measured
regression: more preflight errors, a worse rubric mean, busting the word bound,
new citation-verify failures. Feelings are a fine *tiebreaker* on a TIE; they
are not allowed to overturn a number.

Lower-is-better vs higher-is-better matters. `reflect_log.py` auto-detects
lower-is-better from metric names containing count/error/hedge/fail/over/etc.,
and you can force it with `--lower-is-better` / `--higher-is-better`. Get this
wrong and the guard inverts — always sanity-check the printed `direction`.

## Choosing the measure (cheapest valid wins)

Prefer a **deterministic script score** over a rubric, and a rubric over a vibe:

1. **Re-run the producing skill's checker.** Best signal, zero new judgment.
   - `preflight-check` → error/warning counts
   - `polish-prose` → readability / hedge / passive counts
   - `write-abstract` / `check_abstract.py` → words vs venue bound
   - `verify-citations` → number of unverified references
2. **Score a rubric 1–5 before and after** (this skill's tables, or
   `simulate-reviewers/references/rubrics.md`). Use the **mean** of the scored
   dimensions as the metric so one number drives the verdict. Be consistent:
   score both versions with the same anchors in the same session.
3. **No measure exists.** Say so. Do one qualitative pass against goal +
   profile and stop. Do **not** invent a number to justify another iteration —
   that is the reward-hacking failure mode below.

## Lightweight rubric for artifact reflection (1–5)

For prose/rebuttal/abstract artifacts where no script applies. Score the
dimensions that fit the artifact; take the mean.

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Goal fit | ignores or only partly does the asked thing; adds unasked changes | does the asked thing with minor drift | does exactly the asked thing, nothing extraneous |
| Clarity | reader must re-read to parse | mostly clear; a few dense spots | reads cleanly first time at the target audience's level |
| Faithfulness | overclaims / introduces unsupported assertions | claims supported but some hedging mismatch | claims match evidence; hedging calibrated to results |
| Profile fit | wrong register/vertical/venue tier | mostly on-profile | on-vertical, on-audience, on-voice per `profile.yml` |
| Responsiveness (rebuttals) | misses or dodges the reviewer's point | addresses it partially | answers the actual concern with a concrete commitment |

## Failure modes to watch for

- **Sycophantic self-approval.** The agent rates its own latest version higher
  because it wrote it. Defense: the *measure* is the judge, not the agent's
  reasoning; never default to KEEP without a number that moved.
- **Reward hacking the metric.** Optimizing the number while the artifact gets
  worse — e.g. deleting a needed caveat to cut "hedge-count", or trimming real
  content to hit a word bound. Defense: a second, opposing metric (cut hedges
  *and* keep the claim intact), and a human read on any large metric jump.
- **Oscillation / non-convergence.** Defense: the iteration cap and the
  stop-on-TIE rule.
- **Goal drift.** Each pass quietly broadens scope. Defense: re-read the
  one-sentence goal at the top of every pass; the "Goal fit" row punishes
  unasked changes.
- **Profile-blind critique.** Generic "tighten everything" advice that fights
  the paper's chosen voice (e.g. a position paper, a high-risk-appetite systems
  paper). Defense: read `profile.yml` first; tailor the critique.
- **Memory rot.** Stale `this-paper` lessons crowd out signal. Defense:
  `reflect_log.py prune` (recurring lessons are never pruned).
