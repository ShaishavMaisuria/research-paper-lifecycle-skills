---
name: paper-profile
description: >-
  Interactively elicits and stores the author's paper positioning so every
  other skill in this repo behaves context-awarely. Use when a researcher says
  "set up my paper profile", "ask me about my paper", "what verticals",
  "configure for my paper", "remember my positioning/style", or is starting a
  new paper and wants the toolkit tuned before drafting. Asks with sensible
  options about vertical/emphasis, contribution type, audience and venue tier,
  risk appetite, and writing preferences, then writes
  .paper-memory/profile.yml in the paper working directory. Explains how
  downstream skills consume it for benchmark-paper weighting,
  simulate-reviewers persona calibration, polish-prose/match-style register,
  and tailor-to-venue framing. Bundles a stdlib script profile_io.py that
  reads/writes/validates the file and emits a blank template. Local-only, never
  uploaded; advisory copilot, never submits.
---

# Paper Profile

Elicits the author's **paper positioning** once, stores it in
`.paper-memory/profile.yml`, and lets every other skill read it so the whole
toolkit behaves context-awarely instead of asking the same questions over and
over. This is the "ask me about my paper" front door: a short, optioned
interview, then a small validated YAML file the rest of the repo consumes.

It is a **copilot**, not an oracle. The profile records *your stated intent*
(what kind of paper this is, who it's for, how bold you want to be). It does
not judge whether the science is good and it never predicts acceptance.

## When to use

- "Set up my paper profile" / "ask me about my paper" / "what verticals?"
- Starting a new paper and wanting the toolkit tuned before drafting.
- "Remember my writing style / positioning across skills."
- Any other skill notices `.paper-memory/profile.yml` is missing and you want
  to create it so that skill can personalize.
- Re-run any time the positioning changes (e.g. you drop down a venue tier, or
  pivot from systems to empirical framing).

## Inputs

- The user's **paper working directory** (where they want `.paper-memory/` to
  live). This is the user's paper repo, **not** this skills repo.
- The user's answers to the interview (you ask; they pick). Nothing else is
  required — there is no network call and no file the user must pre-create.
- Optional: an existing `.paper-memory/profile.yml` to update instead of
  starting fresh.

## Process

1. **Locate the paper directory and the memory dir.** Confirm with the user
   where their paper lives; the profile goes in `<paper-dir>/.paper-memory/`.
   If one already exists, load and show it (`profile_io.py show`) and offer to
   update rather than overwrite.

2. **Show the option menu, then interview.** Print the blank template so the
   user sees the choices, then ask through them. Get the exact vocabulary from
   the script so you never invent a value:
   `python3 scripts/profile_io.py schema`. Ask in this order, always offering
   the options and a one-line gloss of each (full descriptions live in
   [references/positioning-axes.md](references/positioning-axes.md)):

   - **vertical / emphasis** (required): `systems` | `theory` | `applied` |
     `empirical` | `survey` | `position`. "Is the heart of the paper a built
     artifact, a proof, a domain application, a measurement study, a synthesis,
     or an argument?"
   - **contribution_type** (required): `method` | `system` | `theory` |
     `dataset` | `empirical` | `application` | `survey` | `position`.
   - **audience**: `specialists` | `broad-field` | `practitioners` |
     `interdisciplinary`.
   - **venue_tier** (required): `top` | `specialized` | `regional` |
     `journal` | `workshop` | `preprint` | `undecided`; plus any concrete
     `target_venues` (e.g. `sigspatial-2026`).
   - **risk_appetite** (required): `safe` | `balanced` | `ambitious`. "Defend a
     tight incremental delta, or stake a big claim and accept polarized
     reviews?"
   - **writing_preferences**: `person` (we/I/impersonal/venue-default),
     `tone`, `notation` (heavy/light), `british_spelling`; plus
     `preferred_terms` and `avoid_terms`.
   - **context**: `prior_papers` (paths/ids, for `match-style`),
     `constraints` (hard deadline, must stay anonymized, no new experiments).

   Offer a sensible default for each and let the user accept it. Do not
   force every field — only the four required ones must be set.

3. **Write and validate.** Persist the answers with one call. The script
   validates against the closed vocabulary and stamps the date; it refuses to
   write an out-of-vocabulary value (so a typo can't silently corrupt the
   file that every other skill trusts):

   ```
   python3 scripts/profile_io.py write <paper-dir>/.paper-memory/profile.yml \
       --field vertical=systems --field contribution_type=system \
       --field venue_tier=top --field risk_appetite=ambitious \
       --field audience=broad-field \
       --field wp.person=first-person-we --field wp.tone=assertive \
       --field target_venues="sigspatial-2026, vldb-2027" \
       --field constraints="hard deadline 2026-08-01, no new experiments"
   ```

   Use `--from <existing>` to update in place, repeated `--field` to set each
   answer, comma-separated values for list fields, and `wp.<key>=...` for the
   nested writing preferences. Re-validate any hand-edited file with
   `python3 scripts/profile_io.py validate <path>`.

4. **Set up .gitignore (ask first).** `.paper-memory/` is **local** — it holds
   the author's private positioning and accumulated lessons. Recommend adding
   `.paper-memory/` to the paper repo's `.gitignore` unless the user
   deliberately wants to version it (e.g. to share positioning with
   co-authors). State the choice; let the user decide.

5. **Explain how downstream skills consume it.** Tell the user concretely what
   changes now that the profile exists (see the table below and
   [references/downstream-consumption.md](references/downstream-consumption.md)).
   The point of the interview is that they won't be re-asked.

6. **Mention the rest of `.paper-memory/`.** This skill owns `profile.yml`.
   The same directory also accumulates `lessons.md` (deduped, dated lessons
   other skills append when they catch something, and read at start to avoid
   repeating advice) and `decisions.md` (venue/track/positioning decisions
   with rationale). See
   [the shared `.paper-memory/` convention](references/paper-memory-convention.md)
   for the file formats and memory-hygiene rules. This skill does not
   write those two files; it just establishes the directory and explains them.

## How downstream skills consume the profile

| Skill | Reads | Effect |
|---|---|---|
| `benchmark-paper` | `vertical`, `contribution_type` | Re-weights scorecard dimensions (a `theory` paper isn't penalized for a thin evaluation; a `system` paper is). |
| `simulate-reviewers` | `vertical`, `venue_tier`, `risk_appetite` | Calibrates reviewer personas + harshness; an `ambitious` claim at a `top` venue gets a skeptic, not a rubber stamp. |
| `polish-prose` | `writing_preferences`, `avoid_terms` | Tunes the de-AI-ify / register pass to the author's person, tone, spelling, and banned terms. |
| `match-style` | `writing_preferences`, `prior_papers`, `preferred_terms` | Seeds the target voice and terminology so alignment matches the author. |
| `tailor-to-venue` / `select-venue` | `venue_tier`, `target_venues`, `contribution_type` | Frames the contribution and shortlist toward the stated targets. |
| `write-abstract` | `vertical`, `key_claim`, `audience` | Leads with the claim the right reader cares about. |

These skills should **degrade gracefully**: if `profile.yml` is absent they
ask the user (or use venue defaults) as they do today. The profile removes the
re-asking; it is never a hard dependency.

## Output

- `<paper-dir>/.paper-memory/profile.yml` — a small validated YAML file
  (schema v1). Required: `vertical`, `contribution_type`, `venue_tier`,
  `risk_appetite`. Optional everything else.
- A short plain-English recap of the positioning and the concrete behavior
  changes in the skills the user is likely to run next.

## Adapt to your discipline

The positioning axes are CS-flavored (systems/theory/empirical, conference
tiers, double-blind constraints). For other fields, edit the vocabularies at
the top of `scripts/profile_io.py` (e.g. add `clinical-trial` or
`humanities-essay` verticals, swap venue tiers for journal quartiles) — the
validator and emitter are data-driven, so new disciplines need new tokens, not
new code. Bump `SCHEMA_VERSION` if you change required fields.

## Guardrails

- **Never invent a vocabulary value.** Pull the allowed values from
  `profile_io.py schema`; the writer rejects anything else so the file every
  other skill trusts can't be silently corrupted.
- **Never decide for the user.** Offer options and a default; the author picks
  their own positioning and risk appetite. Don't infer "ambitious" because the
  topic sounds exciting.
- **Local and private.** `.paper-memory/` is never uploaded anywhere; always
  offer the `.gitignore` line and respect the user's versioning choice.
- **This skill is configuration, not authorship.** It records intent. It does
  not write paper content, predict acceptance, or submit anything.
- Keep this file under 500 lines; `references/` go one level deep only.
