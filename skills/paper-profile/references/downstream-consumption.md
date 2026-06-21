# How downstream skills consume profile.yml

The profile only matters if other skills actually read it. This file is the
contract: which field drives which behavior, and the exact rule every consuming
skill follows so the profile is helpful without ever becoming a hard
dependency.

## The graceful-degradation rule (every consumer)

A consuming skill MUST:

1. Look for `<paper-dir>/.paper-memory/profile.yml` at start.
2. If present and valid (`profile_io.py validate` passes), use it to skip
   questions and personalize.
3. If absent, invalid, or missing a field it wants, fall back to today's
   behavior — ask the user or use venue defaults. Never error out because the
   profile is missing.
4. Never overwrite `profile.yml`. Only `paper-profile` writes it. Other skills
   that learn something durable append to `lessons.md` / `decisions.md`
   instead (see paper-memory-convention.md).

This keeps the profile a *speedup and a calibration*, never a gate.

## Field-by-field consumption

### benchmark-paper — dimension weighting

Reads `vertical` and `contribution_type`. The scorecard has fixed dimensions
(section architecture, evaluation rigor, claim/citation density, …). The
profile re-weights them so a paper isn't penalized for not being a different
kind of paper:

- `vertical: theory` → down-weight the empirical-evaluation dimension, up-weight
  proof/clarity; a thin experiments section is expected, not a gap.
- `vertical: systems` → up-weight evaluation rigor and reproducibility
  artifacts; "no end-to-end evaluation" is a real gap.
- `vertical: survey` → coverage/taxonomy dimensions dominate; "no new method"
  is not a deduction.
- `contribution_type: dataset` → reproducibility/availability weighed heavily.

The report must still state what was measured and the exemplar range; the
profile changes weights, not the honesty of the numbers.

### simulate-reviewers — persona and harshness calibration

Reads `vertical`, `venue_tier`, `risk_appetite`.

- `venue_tier: top` + `risk_appetite: ambitious` → seat a hard skeptic persona
  who attacks the big claim; do not soften.
- `venue_tier: workshop` / `risk_appetite: safe` → a more lenient panel that
  judges incremental soundness, matching real workshop review.
- `vertical` selects which expertise the personas bring (a `systems` reviewer
  probes the evaluation; a `theory` reviewer probes the proofs).

Still advisory — the simulation never predicts the real outcome.

### polish-prose — register and removal list

Reads `writing_preferences` and `avoid_terms`.

- `person` / `tone` / `british_spelling` set the target register so the pass
  doesn't "correct" the author's deliberate voice.
- `notation` tunes how much the pass tightens math-heavy prose.
- `avoid_terms` is merged into the removal list (banned jargon, AI tells, a
  co-author's pet phrase).

### match-style — target voice seeding

Reads `writing_preferences`, `prior_papers`, `preferred_terms`.

- `prior_papers` is the author-voice corpus for the style signature.
- `preferred_terms` pins terminology so alignment is consistent.
- `writing_preferences` resolves conflicts (e.g. the venue prefers passive but
  the author set `first-person-we` → surface the trade-off rather than silently
  picking).

### tailor-to-venue / select-venue — framing and shortlist

Reads `venue_tier`, `target_venues`, `contribution_type`.

- `target_venues` seeds the shortlist / the venue to tailor toward.
- `contribution_type` + `venue_tier` frame the contribution for the right track
  (a `dataset` contribution maps to a benchmark/dataset track where one exists).

### write-abstract — what to lead with

Reads `vertical`, `key_claim`, `audience`.

- Leads the abstract with the claim the `audience` cares about, in the register
  the `vertical` rewards (systems: capability + numbers; theory: the result +
  its strength).

## Constraints are read by everyone

`constraints` (hard deadline, "stay anonymized," "no new experiments," page
budget) are advisory inputs to *all* skills so none of them suggest something
impossible — e.g. `simulate-reviewers` won't recommend "run another ablation"
when `constraints` says no new experiments are possible; it flags the risk
instead.

## Implementation note for skill authors

Load the profile with the bundled loader so parsing/validation is identical
everywhere:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("skills/paper-profile/scripts")))
import profile_io
prof = profile_io.load_profile(paper_dir / ".paper-memory" / "profile.yml")
if profile_io.validate(prof):   # non-empty list => problems => fall back
    prof = {}
```

Treat a missing or invalid profile as `{}` and branch on `.get(field)`. Never
crash on its absence.
